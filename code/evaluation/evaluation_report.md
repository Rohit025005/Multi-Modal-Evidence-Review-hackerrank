# Evaluation Report

## Strategy Comparison

### Strategy A: Unified Gemini Perception (PRIMARY)
- **Model**: Gemini 2.5 Flash (temperature=0.0)
- **Calls**: 1 Gemini call per claim (conversation + all images together)
- **Pipeline**: unified_perceive() → deterministic decision engine
- **Key property**: Perception only; all decisions made by deterministic rules

### Strategy B: Per-Image + Per-Conversation (FALLBACK)
- **Model**: Gemini 2.5 Flash (temperature=0.0)
- **Calls**: 1 call for claim extraction + N calls for N images = (N+1) per claim
- **Pipeline**: claim_extractor.py → image_analyzer.py per image → decision engine
- **Key property**: Same deterministic engine, but extraction and analysis are separate

### Comparison Table

| Metric | Strategy A (Unified) | Strategy B (Per-Image) |
|---|---|---|
| API calls per claim | 1 | N + 1 (N = images) |
| API calls for 44 claims | ~44 | ~100-130 |
| Latency per claim | 3-8s | 8-20s |
| Cache granularity | Per-claim | Per-image + per-conversation |
| Image context | All images seen together | Each image seen in isolation |
| Perception quality | Higher (full context) | Lower (no cross-image context) |

**Chosen**: Strategy A (Unified) — fewer API calls, lower latency, better cross-image reasoning.

---

## Accuracy on sample_claims.csv (20 claims)

Results from the primary pipeline (Strategy A):

| Field | Correct / Total | Accuracy |
|---|---|---|
| claim_status | 14/20 | 70.0% |
| issue_type | 15/20 | 75.0% |
| object_part | 15/20 | 75.0% |
| severity | 12/20 | 60.0% |
| evidence_standard_met | 17/20 | 85.0% |
| **Overall** | **73/100** | **73.0%** |

### Improvement from v1 (67.0% → 73.0%)

| Field | v1 | v2 | Delta |
|---|---|---|---|
| claim_status | 60.0% | 70.0% | +10% |
| issue_type | 65.0% | 75.0% | +10% |
| object_part | 70.0% | 75.0% | +5% |
| severity | 55.0% | 60.0% | +5% |
| evidence_standard_met | 85.0% | 85.0% | 0% |

The improvement came from fixing duplicate dictionary keys in `mappings.py` (`"mark"` conflicting between `scratch` and `stain`; `"corner"` conflicting between laptop `corner` and `package_corner`), which allowed Gemini's output to normalize to the correct labels.

### Known Failure Patterns

1. **Contradiction detection misses** (user_005, user_008, user_020, user_030, user_033, user_034): The deterministic engine finds damage on the claimed part and returns `supported`, but the expected answer expects `contradicted` because the *type* or *extent* of damage doesn't match the claim. This requires tighter contradiction logic that checks issue_type matching, not just part matching.

2. **Part identification errors** (user_008, user_020, user_030, user_031, user_033): Gemini misidentifies which part is visible in the images (e.g., `box` vs `package_side`, `front_bumper` vs `hood`). Improving the prompt with clearer part definitions would help.

3. **Severity mismatches** (user_005, user_007, user_008, user_010, user_012, user_020, user_033, user_034): Severity priors are context-free. A `broken_part` on a side_mirror maps to `high`, while expected is `medium`. Context-aware severity (part + issue_type) would improve accuracy.

4. **Issue type confusion** (user_005, user_008, user_011, user_020, user_034): Gemini misclassifies the damage type (e.g., `water_damage` vs `stain`, `dent` vs `scratch`). Better few-shot examples in the prompt would help.

5. **Evidence standard errors** (user_006, user_032, user_033): The EvidenceValidator checks only "does any image show the claimed object." Expected outputs require "does the image show the specific claimed part."

### Planned Improvements

- Add damage-type contradiction detection in `decide_claim_status()` — check if observed issue_type matches claimed issue_type
- Refine evidence validator to check specific part visibility, not just object type
- Improve Gemini prompt with better part definitions and few-shot examples
- Add context-aware severity based on both issue_type and object_part

---

## Operational Analysis

### Model Calls
- **Sample (20 claims)**: 20 Gemini API calls (1 per claim, unified perception)
- **Test (44 claims)**: 44 Gemini API calls
- **Total**: ~64 unique API calls
- **Cache hit rate**: 100% on subsequent runs

### Token Usage (Estimated)

| Metric | Per Claim | Total (44 claims) |
|---|---|---|
| Input tokens (prompt + images) | ~2,000-4,000 | ~100,000-180,000 |
| Output tokens (JSON response) | ~1,000-2,000 | ~44,000-88,000 |
| **Total** | ~3,000-6,000 | ~150,000-270,000 |

Images dominate token usage.

### Cost Estimation (Gemini 2.5 Flash)

| Component | Tokens | Cost |
|---|---|---|
| Input (sample) | ~45,000 | $0.007 |
| Output (sample) | ~25,000 | $0.015 |
| Input (test) | ~120,000 | $0.018 |
| Output (test) | ~65,000 | $0.039 |
| **Total** | ~255,000 | **~$0.08** |

### Latency / Runtime

| Phase | Time |
|---|---|
| Gemini perception (per claim) | 3-8 seconds |
| Deterministic decisions | <10ms |
| **Total per claim** | **3-8 seconds** |
| **Full test set (44 claims)** | **~3-6 minutes** |

### Rate Limiting

- **Free tier**: ~5-15 RPM / 1M TPM
- **Strategy**: Sequential processing, one call per claim
- **Retry**: Exponential backoff with 45s base delay + random jitter on 429 errors
- **Resumability**: Row-position tracking; interrupted runs resume from last saved row

### Caching

- **Method**: Content-based SHA-256 hash of (PROMPT_VERSION + prompt + conversation + image bytes)
- **Versioning**: `PROMPT_VERSION = "v1"` in `gemini_client.py`; bump to invalidate all caches
- **Storage**: `.gemini_cache/` at repo root (git-ignored)
- **Persistence**: Survives across runs, branches, and code changes

---

## Final Strategy

**Strategy A (Unified Gemini Perception) + Deterministic Decision Engine.**

The system uses a single Gemini 2.5 Flash call per claim to extract claim fields and per-image observations, then applies deterministic rules for evidence validation, claim status, severity, risk flags, and justification. This separation ensures decisions are grounded in visual evidence rather than LLM intuition.
