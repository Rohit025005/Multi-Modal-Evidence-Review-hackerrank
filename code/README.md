# Damage Claim Verification System

A multimodal damage-claim verification system that processes insurance claims using Gemini Vision for perception and deterministic rules for decisions.

## Architecture

<p align="center">
  <img src="../architecture.png" alt="Architecture Diagram" width="1100">
</p>

The system processes damage claims in batches, analyzes claim images using Gemini Vision, enriches results with user history, and uses a deterministic decision engine to generate claim verification outputs.

- **Gemini 2.5 Flash** handles perception only: extracts claim fields from conversation and analyzes each image visually.
- **Deterministic rules** handle all decisions: evidence validation, claim status, severity, risk flags, justification.

This separation ensures Gemini never directly decides claim outcomes.

## Files

| File | Purpose |
|---|---|
| `main.py` | Entry point. Batch or debug mode. Resumable pipeline. |
| `perception.py` | Unified Gemini perception: one call per claim for all images + conversation. |
| `claim_extractor.py` | Fallback claim extraction (separate from images). |
| `image_analyzer.py` | Fallback per-image analysis. |
| `decision_engine.py` | Deterministic rules: claim status, severity, risk flags, justification. |
| `evidence_validator.py` | Checks if images meet minimum evidence requirements. |
| `history_scorer.py` | Looks up user history and generates risk flags. |
| `gemini_client.py` | Gemini API wrapper with content-based caching and retry logic. |
| `mappings.py` | Centralized domain mappings: issue type canonicalization, part normalization, severity priors, risk flag normalization. |
| `evaluation/main.py` | Per-field accuracy evaluation against expected outputs. |

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```


## Usage

```bash
# Batch mode (all claims)
python main.py --input dataset/claims.csv --output output.csv

# Debug mode (single claim)
python main.py --debug user_001 --input dataset/sample_claims.csv

# Evaluation
python evaluation/main.py output_sample.csv dataset/sample_claims.csv
```

## Key Design Decisions

1. **Unified perception**: One Gemini call per claim (conversation + all images) instead of separate extraction + per-image analysis.
2. **Severity priors**: Uses issue-type-based priors (e.g., scratch->low, dent->medium, broken_part->high) instead of relying on Gemini's severity estimates.
3. **Row-position resumability**: Tracks output row count (not user_id) to handle duplicate user_ids correctly.
4. **Content-based caching**: Gemini responses cached by content hash with prompt versioning to avoid redundant API calls.

## Requirements

- Python 3.10+
- `google-generativeai` package
- `python-dotenv`
- `Pillow` (for image handling)
- `.env` file with `GEMINI_API_KEY` set
