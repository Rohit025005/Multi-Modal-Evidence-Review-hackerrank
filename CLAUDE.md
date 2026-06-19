@AGENTS.md

Here is a clean spec you can give to an agent like OpenCode.

---

## What we are building

We are building a **multimodal damage-claim verification system**.  
For every claim row, the system reads:

- the **short claim conversation**,
- the **submitted local images**,
- the **user’s past history**,
- and the **evidence requirements table**,

then decides whether the claim is:

- `supported`
- `contradicted`
- `not_enough_information`

The system must also output supporting metadata like:

- whether the evidence standard is met,
- the visible issue type,
- the relevant object part,
- supporting image IDs,
- risk flags,
- whether the image is valid,
- severity,
- and a short justification grounded in the images.

This is **not** a pure LLM text task.  
It is a **rule-guided multimodal verification pipeline**.

---

## What we have understood from the repo and sample data

The repo already contains everything needed:

- `dataset/claims.csv`
- `dataset/sample_claims.csv`
- `dataset/user_history.csv`
- `dataset/evidence_requirements.csv`
- `dataset/images/`
- `code/main.py`
- `code/evaluation/main.py`
- `problem_statement.md`

From the CSVs, we learned:

### `claims.csv`
Each row has:
- `user_id`
- `image_paths`
- `user_claim`
- `claim_object`

### `sample_claims.csv`
This is the gold reference for expected behavior.  
It shows the exact output style and how the labels should behave.

From the sample rows, we learned:

- the claim conversation is the real source of the alleged damage,
- the image is the primary truth source,
- user history adds risk context only,
- evidence can be sufficient, insufficient, or conflicting,
- a claim can be contradicted even when the image is valid,
- a claim can be not enough information if the claimed part is not visible,
- supporting images must be selected explicitly,
- quality problems like blur and wrong angle must be flagged.

### `user_history.csv`
This is only for risk context:
- past claim count
- accepted claims
- manual reviews
- fraud flags

It can add `user_history_risk`, but it must **never override clear visual evidence**.

### `evidence_requirements.csv`
This gives object-level evidence rules.  
It tells us what is needed for:
- car damage,
- laptop damage,
- package damage,
- general multi-image review,
- part visibility,
- angle/context visibility.

So the decision engine should not be hardcoded to specific cases.  
It should apply these general rules dynamically.

---

## Core reasoning logic

For each claim, the system should do this:

1. **Extract the actual claim**
   - object type
   - claimed issue type
   - claimed part
   - implied severity or certainty words
   - any uncertainty in the conversation

2. **Inspect each image independently**
   - what object is visible
   - what part is visible
   - what damage is visible
   - whether the image is blurry, low-light, wrong angle, or irrelevant
   - whether the image looks like it belongs to the claim

3. **Check evidence sufficiency**
   - is the claimed part visible?
   - is the damage visible?
   - is the angle enough to inspect the claim?
   - if multiple images exist, does at least one give useful evidence?

4. **Decide claim status**
   - `supported`: visible evidence matches the claim
   - `contradicted`: enough evidence exists, but it does not match the claim
   - `not_enough_information`: the claim cannot be verified from the images

5. **Add risk flags**
   - `blurry_image`
   - `wrong_angle`
   - `damage_not_visible`
   - `claim_mismatch`
   - `non_original_image`
   - `user_history_risk`
   - `manual_review_required`

6. **Estimate severity**
   - `low`
   - `medium`
   - `high`
   - `unknown`

Severity should come from the image, not from the user narrative alone.

---

## Important constraints

- No case-specific hardcoding.
- No file-specific answers.
- The system must work on unseen test cases.
- Images are the primary truth source.
- User history is only a risk signal.
- The output schema must exactly match `problem_statement.md`.
- The solution must read local CSVs and local images.
- The solution must produce `output.csv`.
- The evaluation workflow must be included.
- Everything should be reproducible and deterministic as much as possible.

---

## Best implementation style

The cleanest design is a small pipeline:

**CSV loader → claim extractor → image analyzer → evidence validator → history scorer → decision engine → CSV writer**

That means:

- `main.py` orchestrates the run,
- claim extraction is isolated,
- image analysis is isolated,
- decision rules are isolated,
- evaluation is isolated.

This is better than one giant prompt or one giant script.

---

## What the final system should output

For every claim row, fill the required columns such as:

- evidence standard met
- evidence standard reason
- risk flags
- issue type
- object part
- claim status
- claim status justification
- supporting image IDs
- valid image
- severity

The final justification should be short and based on what is actually visible in the images.

---

## The practical strategy

Use a **hybrid system**:

- structured parsing for the conversation,
- vision model or image reasoning for image inspection,
- rule-based logic for the final verdict,
- deterministic post-processing for output formatting.

This keeps it cheap, explainable, and stable on free or limited models.

---

## The main idea in one line

We are building a **multimodal evidence judge** for damage claims, where the claim text defines what to check, the images define what is true, and history only adds suspicion.

Yes. One more important thing from `AGENTS.md` that OpenCode must follow is the **mandatory transcript logging system**. 

Add this section to the project description:

---

# Conversation Transcript / Logging Requirements

This repository contains a global `AGENTS.md` contract. The implementation must respect it.

## Logging Rules

* On startup, read `AGENTS.md` completely.
* Check whether onboarding has already been recorded.
* Maintain a persistent log file:

**Windows**

```text
%USERPROFILE%\hackerrank_orchestrate\log.txt
```

**Linux/macOS**

```text
$HOME/hackerrank_orchestrate/log.txt
```

The log file:

* must be created if missing,
* is append-only,
* must never be committed,
* is shared across sub-agents and worktrees,
* must never contain secrets.

---

## Onboarding Requirement

If no agreement exists for this repo root:

1. Show greeting.
2. Show current time.
3. Show remaining challenge time.
4. Recite rules from `AGENTS.md`.
5. Wait for:

```text
I agree
```

6. Record:

```text
AGREEMENT RECORDED: <repo_root>
```

Only then continue.

---

## Session Logging

Every user interaction should append:

```text
timestamp
short title
user prompt
response summary
actions performed
context
```

The log should be concise and append-only.

---

# Why this matters

This transcript system is part of the repository contract. It is not optional. The hackathon submission specifically asks for:

```text
Chat transcript: log.txt
```

Therefore logging is a first-class requirement, not an extra feature. The system should generate `log.txt` automatically while the agent works. 

---

# Final Mental Model

We are building **three systems simultaneously**:

### 1. Claim Verification Engine

```text
Conversation
+ Images
+ User History
+ Evidence Rules
↓
Structured Claim Decision
```

### 2. Evaluation System

```text
sample_claims.csv
↓
Run predictions
↓
Compare outputs
↓
Report metrics
```

### 3. Agent Operating System

```text
Onboarding
+ Transcript Logging
+ Session Tracking
+ Reproducibility
+ Environment Variables
```

---

# Principles OpenCode should follow

1. Simplicity over complexity.
2. No case-specific hardcoding.
3. Deterministic where possible.
4. Images are the source of truth.
5. User history only adds risk context.
6. Separate perception from reasoning.
7. Prefer structured outputs over free text.
8. Every component should be independently testable.
9. Every run should be reproducible.
10. Automatically maintain `log.txt` according to `AGENTS.md`. 
