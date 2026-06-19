"""
Image Analyzer using Gemini Vision (FALLBACK).

DEPRECATED for main pipeline use. The primary path is perception.py which
combines claim extraction + image analysis in a single Gemini call.

This module is retained as a fallback for:
  - perception.py fallback path when unified Gemini call fails
  - Testing and development
  - Manual one-off image analysis

Do NOT call this directly from main.py in the production pipeline.
"""

from typing import Dict, Any, List

IMAGE_OBSERVATION_PROMPT = """You are an image analyst for a damage claim verification system.

Analyze this image and describe what you see.

CLAIM CONTEXT:
- Object type: {claim_object}
- User claims: {claim_description}
- Claimed part: {claimed_object_part}
- Claimed issue: {claimed_issue_type}

Analyze the image and return strict JSON with these fields:

1. visible_object: What object is in the image?
   - "car" if a car or vehicle is visible
   - "laptop" if a laptop or notebook computer is visible
   - "package" if a box, parcel, or package is visible
   - "other_object" if something else is visible
   - "unrecognizable" if the image is too blurry or dark to tell

2. visible_parts: List of parts visible in the image.
   For cars: front_bumper, rear_bumper, door, hood, windshield, side_mirror,
     headlight, taillight, fender, quarter_panel, body
   For laptops: screen, keyboard, trackpad, hinge, lid, corner, port, base, body
   For packages: box, package_corner, package_side, seal, label, contents, item

3. visible_damage: List of damage observations. Each item has:
   - issue_type: "dent", "scratch", "crack", "broken_part", "glass_shatter",
     "missing_part", "torn_packaging", "crushed_packaging", "water_damage",
     "stain", or "none"
   - part: which part shows this damage
   - description: short description of what you see (1 sentence)
   - estimated_severity: "low", "medium", or "high"
   If no damage is visible, return an empty list.

4. image_quality:
   - is_blurry: true if the image is blurry or low resolution
   - is_low_light: true if the image is too dark or has glare/reflection
   - is_wrong_angle: true if the image shows the wrong angle to evaluate
     the claimed damage (e.g., claiming headlight damage but image shows door)
   - is_cropped_or_obstructed: true if the relevant area is cropped out or blocked
   - is_relevant_to_claim: true if this image could help evaluate the claim
   - confidence: "high" if you are confident in your observations,
     "medium" if somewhat confident, "low" if uncertain

5. observation_summary: 1-2 sentence summary of what this image shows.
   Be specific about what object, parts, and damage are visible.

Return ONLY valid JSON. No markdown, no explanation, no extra text."""


def analyze_image(
    gemini_client,
    image_path: str,
    claim_object: str,
    claim_description: str,
    claimed_object_part: str,
    claimed_issue_type: str,
) -> Dict[str, Any]:
    """Analyze one image using Gemini Vision.

    Args:
        gemini_client: Initialized GeminiClient instance.
        image_path: Path to the image file.
        claim_object: The claimed object type.
        claim_description: Plain-English claim description.
        claimed_object_part: The claimed part.
        claimed_issue_type: The claimed issue type.

    Returns:
        Dict with image observation fields.
    """
    prompt = IMAGE_OBSERVATION_PROMPT.format(
        claim_object=claim_object,
        claim_description=claim_description,
        claimed_object_part=claimed_object_part,
        claimed_issue_type=claimed_issue_type,
    )

    result = gemini_client.generate_with_image(prompt, image_path, use_cache=True)

    if "parse_error" in result:
        return _fallback_observe(image_path)

    result = _validate_observation(result)

    return result


def _validate_observation(obs: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize observation fields."""
    if "visible_object" not in obs:
        obs["visible_object"] = "unrecognizable"

    if "visible_parts" not in obs or not isinstance(obs["visible_parts"], list):
        obs["visible_parts"] = []

    if "visible_damage" not in obs or not isinstance(obs["visible_damage"], list):
        obs["visible_damage"] = []

    for damage in obs["visible_damage"]:
        if "issue_type" not in damage:
            damage["issue_type"] = "none"
        if "part" not in damage:
            damage["part"] = "unknown"
        if "description" not in damage:
            damage["description"] = ""
        if "estimated_severity" not in damage:
            damage["estimated_severity"] = "medium"

    if "image_quality" not in obs:
        obs["image_quality"] = {
            "is_blurry": False,
            "is_low_light": False,
            "is_wrong_angle": False,
            "is_cropped_or_obstructed": False,
            "is_relevant_to_claim": True,
            "confidence": "medium",
        }
    else:
        q = obs["image_quality"]
        for key in [
            "is_blurry", "is_low_light", "is_wrong_angle",
            "is_cropped_or_obstructed", "is_relevant_to_claim",
        ]:
            if key not in q:
                q[key] = False if key != "is_relevant_to_claim" else True
        if "confidence" not in q:
            q["confidence"] = "medium"

    if "observation_summary" not in obs:
        obs["observation_summary"] = ""

    return obs


def _fallback_observe(image_path: str) -> Dict[str, Any]:
    """Minimal fallback if Gemini fails."""
    import os
    filename = os.path.basename(image_path).lower()

    return {
        "visible_object": "unrecognizable",
        "visible_parts": [],
        "visible_damage": [],
        "image_quality": {
            "is_blurry": True,
            "is_low_light": False,
            "is_wrong_angle": False,
            "is_cropped_or_obstructed": False,
            "is_relevant_to_claim": False,
            "confidence": "low",
        },
        "observation_summary": f"Could not analyze image {filename}",
    }
