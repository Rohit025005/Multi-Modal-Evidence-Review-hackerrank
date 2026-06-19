# Operational Analysis

## Model Calls

### Sample processing (20 claims)
- **Initial run**: 20 Gemini API calls (1 per claim, unified perception)
- **Subsequent runs**: 0 calls (all cached)
- **Cache hit rate**: 100% after initial run

### Test processing (44 claims)
- **Total API calls**: ~44 Gemini API calls (1 per claim)
- **Cache overlap**: ~20 claims share cache with sample set
- **Net new calls**: ~24 unique API calls for test set

**Total for both**: ~44 unique API calls

## Token Usage (Estimated)

| Metric | Per Claim | Total (44 claims) |
|---|---|---|
| Input tokens (prompt + images) | ~2,000-4,000 | ~100,000-180,000 |
| Output tokens (JSON response) | ~1,000-2,000 | ~44,000-88,000 |
| **Total** | ~3,000-6,000 | ~150,000-270,000 |

Images dominate token usage. Multi-image claims (2-3 images) consume proportionally more input tokens.

## Images Processed

- **Sample**: 20-25 images across 20 claims
- **Test**: 50-70 images across 44 claims
- **Total**: ~70-95 images

## Cost Estimation

Using Gemini 2.5 Flash pricing (free tier):
- **Input**: $0.15 / 1M tokens
- **Output**: $0.60 / 1M tokens

| Component | Tokens | Cost |
|---|---|---|
| Input (sample) | ~45,000 | $0.007 |
| Output (sample) | ~25,000 | $0.015 |
| Input (test) | ~120,000 | $0.018 |
| Output (test) | ~65,000 | $0.039 |
| **Total** | ~255,000 | **~$0.08** |

At free-tier rates, cost is negligible. At pay-as-you-go, processing the full test set costs under $0.10.

## Latency / Runtime

| Phase | Time |
|---|---|
| Gemini perception (per claim) | 3-8 seconds |
| Deterministic decisions | <10ms |
| **Total per claim** | **3-8 seconds** |
| **Full test set (44 claims)** | **~3-6 minutes** |

## TPM/RPM Considerations

- **Rate limit**: Gemini free tier allows ~15 RPM / 1M TPM
- **Strategy**: One call per claim avoids per-image rate limits
- **Retry**: Exponential backoff with 45s base delay on 429 errors
- **Resumability**: Pipeline tracks output row count; interrupted runs resume from last saved row

## Caching Strategy

- **Content-based hashing**: Response cached by SHA-256 hash of (prompt + image paths + content)
- **Prompt versioning**: `PROMPT_VERSION` constant in `gemini_client.py`; bump to invalidate all caches
- **Cache location**: `.gemini_cache/` at repo root (not committed to git)
- **Persistence**: Cache survives across runs, branches, and code changes

## Batching / Throttling

- Claims processed sequentially to stay within RPM limits
- No explicit batching (Gemini handles multi-image input natively)
- API calls are idempotent; cache prevents duplicate work
