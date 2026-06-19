"""
Gemini API Client with content-based caching and prompt versioning.

Handles all communication with Google Gemini API.
Caches responses by content hash (not path) to survive file moves.
Prompt versioning via PROMPT_VERSION constant — bump to invalidate old caches.
"""

import os
import json
import hashlib
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

CODE_DIR = Path(__file__).parent
CACHE_DIR = CODE_DIR.parent / ".gemini_cache"

MAX_RETRIES = 5
BASE_DELAY = 45

PROMPT_VERSION = "v1"


def _retry_with_backoff(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """Call func with retry on 429 RESOURCE_EXHAUSTED errors."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            is_rate_limit = "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
            if not is_rate_limit:
                raise
            if attempt < max_retries - 1:
                delay = BASE_DELAY + random.uniform(0, 10)
                print(f"  [rate limit] Attempt {attempt + 1}/{max_retries}: waiting {delay:.0f}s...")
                time.sleep(delay)
            else:
                raise


class GeminiClient:
    """Wrapper around Gemini API with disk caching."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Set it in .env file or as an environment variable."
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        self.prompt_version = PROMPT_VERSION

        self._version_dir = CACHE_DIR / PROMPT_VERSION
        self._version_dir.mkdir(parents=True, exist_ok=True)

    def _image_content_hash(self, image_path: str) -> str:
        """Hash the file bytes of an image for content-based caching."""
        h = hashlib.sha256()
        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def _cache_key_legacy(self, prompt: str, image_paths: list = None) -> str:
        """Legacy cache key (path-based) for backward compatibility."""
        content = prompt
        if image_paths:
            content += "|" + ";".join(sorted(image_paths))
        return hashlib.sha256(content.encode()).hexdigest()

    def _cache_key_unified(
        self, prompt: str, image_paths: List[str], conversation: str = ""
    ) -> str:
        """Content-based cache key for unified perception calls.

        Key = prompt_version + hash(prompt) + hash(conversation) + sorted image content hashes.
        Stable across file moves, prompt rewording invalidated by PROMPT_VERSION bump.
        """
        parts = [self.prompt_version]
        parts.append(hashlib.sha256(prompt.encode()).hexdigest()[:16])
        if conversation:
            parts.append(hashlib.sha256(conversation.encode()).hexdigest()[:16])
        for img_path in sorted(image_paths):
            if os.path.exists(img_path):
                parts.append(self._image_content_hash(img_path))
            else:
                parts.append(hashlib.sha256(img_path.encode()).hexdigest()[:8])
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Look up cached response in versioned directory."""
        cache_file = self._version_dir / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _set_cached(self, key: str, response: Dict):
        """Save response to versioned cache directory."""
        cache_file = self._version_dir / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)

    def generate_text(self, prompt: str, use_cache: bool = True) -> Dict[str, Any]:
        """Send text-only prompt to Gemini and return parsed JSON response."""
        if use_cache:
            cache_key = self._cache_key_legacy(prompt)
            cached = self._get_cached(cache_key)
            if cached:
                print(f"  [cache hit] prompt hash: {cache_key[:12]}...")
                return cached

        response = _retry_with_backoff(
            self.model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=2048,
            ),
        )

        raw_text = response.text.strip()

        parsed = self._parse_json_response(raw_text)

        if use_cache:
            self._set_cached(cache_key, parsed)

        return parsed

    def generate_with_image(
        self, prompt: str, image_path: str, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Send text + single image prompt to Gemini and return parsed JSON response."""
        if use_cache:
            cache_key = self._cache_key_legacy(prompt, [image_path])
            cached = self._get_cached(cache_key)
            if cached:
                print(f"  [cache hit] image: {image_path} hash: {cache_key[:12]}...")
                return cached

        import PIL.Image

        img = PIL.Image.open(image_path)

        response = _retry_with_backoff(
            self.model.generate_content,
            [prompt, img],
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=2048,
            ),
        )

        raw_text = response.text.strip()
        parsed = self._parse_json_response(raw_text)

        if use_cache:
            self._set_cached(cache_key, parsed)

        return parsed

    def generate_with_images(
        self,
        prompt: str,
        image_paths: List[str],
        conversation: str = "",
        use_cache: bool = True,
        max_output_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send text + multiple images to Gemini and return parsed JSON.

        This is the primary method for the unified perception pipeline.
        One Gemini call per claim: conversation + all images in a single request.

        Args:
            prompt: The unified perception prompt.
            image_paths: List of resolved (absolute or working-dir-relative) image paths.
            conversation: Original conversation text, used for cache key stability.
            use_cache: Whether to check/populate disk cache.
            max_output_tokens: Max output tokens (default 4096 for combined response).

        Returns:
            Parsed JSON dict from Gemini, or fallback dict on failure.
        """
        if use_cache:
            cache_key = self._cache_key_unified(prompt, image_paths, conversation)
            cached = self._get_cached(cache_key)
            if cached:
                img_names = [os.path.basename(p) for p in image_paths]
                print(f"  [cache hit] unified call: {', '.join(img_names)}")
                return cached

        import PIL.Image

        content_parts = [prompt]
        for img_path in image_paths:
            try:
                img = PIL.Image.open(img_path)
                content_parts.append(img)
            except Exception as e:
                print(f"  [warning] Could not load image {img_path}: {e}")
                continue

        if len(content_parts) == 1:
            return {"parse_error": True, "raw_response": "No images could be loaded"}

        response = _retry_with_backoff(
            self.model.generate_content,
            content_parts,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=max_output_tokens,
            ),
        )

        raw_text = response.text.strip()
        parsed = self._parse_json_response(raw_text)

        if use_cache and "parse_error" not in parsed:
            self._set_cached(cache_key, parsed)

        return parsed

    def _parse_json_response(self, raw_text: str) -> Dict[str, Any]:
        """Parse JSON from Gemini response, handling markdown fences."""
        text = raw_text

        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_response": raw_text, "parse_error": True}
