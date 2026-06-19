# Damage Claim Verification System

A multimodal damage-claim verification system that processes insurance claims using Gemini Vision for perception and deterministic rules for decisions.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    DAMAGE CLAIM VERIFICATION SYSTEM              │
└──────────────────────────────────────────────────────────────────┘

  INPUTS                         PIPELINE                         OUTPUT
  ───────                        ────────                         ──────

┌──────────────┐
│ claims.csv   │──►┌───────────────────────────────────────────────┐
│              │   │              BATCH RUNNER                     │
│ user_id      │   │  (main.py - resumable by row position)        │
│ image_paths  │   └──────────────────────┬────────────────────────┘
│ user_claim   │                          │ for each claim
│ claim_object │                          ▼
└──────────────┘               ┌──────────────────┐
┌──────────────┐               │ GEMINI PERCEPTION │  1 API call per claim
│ images/      │──►            │  (perception.py)  │  (conversation + all
│              │   ┌──────────►│                   │   images combined)
│ img_1.jpg    │   │          │  - claim fields    │
│ img_2.jpg    │───┘          │  - per-image obs   │
│ ...          │              └────────┬───────────┘
└──────────────┘                       │
┌──────────────┐                       │ extracted_claim
│ user_history │                       │ image_observations
│              │──►  ┌────────┐        │
│ history.csv  │     │history │◄───────┤
└──────────────┘     │scorer  │        │
                     └───┬────┘        │
                         │             ▼
                         │    ┌─────────────────────────────────────┐
                         │    │    DETERMINISTIC DECISION ENGINE    │
                         │    │         (decision_engine.py)        │
                         │    │                                     │
                         │    │  ┌──────────────────────────────┐   │
                         ├────┼─►│ 1. Evidence Validator        │   │
                         │    │  │    - object shown?           │  │
                         │    │  │    - requirements met?        │  │
                         │    │  └──────────┬───────────────────┘   │
                         │    │             │                       │
                         │    │  ┌──────────▼───────────────────┐   │
                         │    │  │ 2. Claim Status Decision     │   │
                         │    │  │    - damage on claimed part? │   │
                         │    │  │    - supported/contradicted/ │   │
                         │    │  │      not_enough_information  │   │
                         │    │  └──────────┬───────────────────┘   │
                         │    │             │                       │
                         │    │  ┌──────────▼───────────────────┐   │
                         │    │  │ 3. Severity (prior-based)    │   │
                         │    │  │    - scratch -> low          │  │
                         │    │  │    - dent -> medium          │  │
                         │    │  │    - broken_part -> high     │  │
                         │    │  └──────────┬───────────────────┘  │
                         │    │             │                      │
                         │    │  ┌──────────▼───────────────────┐  │
                         │    │  │ 4. Risk Flags                │  │
                         │    │  │    - image quality           │  │
                         │    │  │    - history flags           │  │
                         │    │  │    - claim mismatch          │  │
                         │    │  └──────────┬───────────────────┘  │
                         │    │             │                      │
                         │    │  ┌──────────▼───────────────────┐  │
                         │    │  │ 5. Justification             │  │
                         │    │  │    - image-grounded text     │  │
                         │    │  └──────────┬───────────────────┘  │
                         │    └─────────────┼──────────────────────┘
                         │                  ▼
                         │    ┌──────────────────────┐
                         └───►│   OUTPUT FIELDS      │
                              │                      │
                              │  issue_type           │
                              │  object_part          │
                              │  claim_status         │  --> output.csv
                              │  severity             │
                              │  supporting_image_ids │
                              │  risk_flags           │
                              │  justification        │
                              └──────────────────────┘
```

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
