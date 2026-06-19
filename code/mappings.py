"""
Centralized normalization mappings and calibration heuristics.

All domain-level label mappings, synonyms, and severity priors live here.
These are ontology mappings and calibration heuristics, NOT dataset memorization.

Rules:
- Applicable to unseen claims
- Independent of specific dataset rows
- Configurable and documented
- No case-specific hardcoding (no user IDs, file names, image paths, sample rows)
"""

from typing import List

# =============================================================================
# ISSUE TYPE CANONICALIZATION
# =============================================================================
# Maps Gemini's free-form labels to the benchmark's allowed issue_type values.
# Key: normalized Gemini label (lowercase, underscored)
# Value: benchmark issue_type

ISSUE_TYPE_CANONICAL = {
    # dent variants
    "dent": "dent",
    "dented": "dent",
    "denting": "dent",
    "deformation": "dent",
    "deformed": "dent",
    "crumple": "dent",
    "crumpled": "dent",
    "bent": "dent",
    "indentation": "dent",

    # scratch variants
    "scratch": "scratch",
    "scratched": "scratch",
    "scrape": "scratch",
    "scraped": "scratch",
    "scuff": "scratch",
    "scuffed": "scratch",
    "abrasion": "scratch",
    "mark": "scratch",
    "marking": "scratch",

    # crack variants
    "crack": "crack",
    "cracked": "crack",
    "cracking": "crack",
    "fracture": "crack",
    "fractured": "crack",
    "split": "crack",
    "splitting": "crack",

    # glass_shatter variants (canonicalize to crack per benchmark)
    "glass_shatter": "crack",
    "shattered_glass": "crack",
    "fractured_glass": "crack",
    "glass_crack": "crack",
    "shatter": "crack",
    "shattered": "crack",

    # broken_part variants
    "broken_part": "broken_part",
    "broken": "broken_part",
    "breakage": "broken_part",
    "snapped": "broken_part",
    "snapped_off": "broken_part",
    "detached": "broken_part",
    "dislodged": "broken_part",
    "displaced": "broken_part",

    # missing_part variants
    "missing_part": "missing_part",
    "missing": "missing_part",
    "absent": "missing_part",
    "gone": "missing_part",
    "torn_off": "missing_part",

    # torn_packaging variants
    "torn_packaging": "torn_packaging",
    "torn": "torn_packaging",
    "tear": "torn_packaging",
    "ripped": "torn_packaging",
    "ripped_open": "torn_packaging",
    "open_flap": "torn_packaging",

    # crushed_packaging variants
    "crushed_packaging": "crushed_packaging",
    "crushed": "crushed_packaging",
    "crumpled_packaging": "crushed_packaging",
    "dented_packaging": "crushed_packaging",
    "dent": "dent",  # careful: dent on package = crushed_packaging, but dent on car = dent

    # water_damage variants
    "water_damage": "water_damage",
    "water": "water_damage",
    "water_stain": "water_damage",
    "watermark": "water_damage",
    "wet": "water_damage",
    "moisture": "water_damage",

    # stain variants
    "stain": "stain",
    "stained": "stain",
    "discoloration": "stain",
    "discolored": "stain",
    "mark": "stain",  # careful: mark on package could be stain

    # none
    "none": "none",
    "no_damage": "none",
    "no_issue": "none",
    "intact": "none",
    "undamaged": "none",
}

# =============================================================================
# OBJECT PART NORMALIZATION
# =============================================================================
# Maps Gemini's free-form part labels to the benchmark's allowed object_part values.

PART_CANONICAL = {
    # Car parts
    "front_bumper": "front_bumper",
    "rear_bumper": "rear_bumper",
    "bumper": "rear_bumper",  # default bumper to rear if ambiguous
    "front_bumper_cover": "front_bumper",
    "rear_bumper_cover": "rear_bumper",
    "door": "door",
    "driver_door": "door",
    "passenger_door": "door",
    "rear_door": "door",
    "hood": "hood",
    "bonnet": "hood",
    "windshield": "windshield",
    "front_glass": "windshield",
    "windscreen": "windshield",
    "side_mirror": "side_mirror",
    "mirror": "side_mirror",
    "wing_mirror": "side_mirror",
    "headlight": "headlight",
    "head_lamp": "headlight",
    "front_light": "headlight",
    "taillight": "taillight",
    "tail_lamp": "taillight",
    "rear_light": "taillight",
    "fender": "fender",
    "wing": "fender",
    "quarter_panel": "quarter_panel",
    "quarter": "quarter_panel",
    "body": "body",
    "chassis": "body",
    "frame": "body",
    "trunk": "body",

    # Laptop parts
    "screen": "screen",
    "display": "screen",
    "lcd": "screen",
    "panel": "screen",
    "keyboard": "keyboard",
    "keys": "keyboard",
    "trackpad": "trackpad",
    "touchpad": "trackpad",
    "hinge": "hinge",
    "hinges": "hinge",
    "lid": "lid",
    "cover": "lid",
    "corner": "corner",
    "edge": "corner",
    "port": "port",
    "ports": "port",
    "connector": "port",
    "base": "base",
    "bottom": "base",
    "chassis": "body",
    "casing": "body",

    # Package parts
    "box": "box",
    "package_box": "box",
    "shipping_box": "box",
    "package_corner": "package_corner",
    "corner": "package_corner",
    "package_side": "package_side",
    "side": "package_side",
    "seal": "seal",
    "tape": "seal",
    "seal_area": "seal",
    "label": "label",
    "tag": "label",
    "contents": "contents",
    "item": "item",
    "product": "item",
}

# =============================================================================
# SEVERITY PRIORS
# =============================================================================
# Default severity by issue type when Gemini's severity is inconsistent or missing.
# Used as calibration heuristics, not hard rules.

SEVERITY_PRIORS = {
    "dent": "medium",
    "scratch": "low",
    "crack": "medium",
    "broken_part": "high",
    "missing_part": "high",
    "glass_shatter": "high",
    "torn_packaging": "medium",
    "crushed_packaging": "medium",
    "water_damage": "medium",
    "stain": "low",
    "none": "none",
    "unknown": "unknown",
}

# =============================================================================
# SEVERITY ORDERING
# =============================================================================
# For severity comparison and max/min logic.

SEVERITY_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "unknown": -1,
}


def canonicalize_issue_type(raw_label: str) -> str:
    """Map a Gemini-generated issue type label to the benchmark's allowed value.

    Args:
        raw_label: The raw label from Gemini (e.g., "shattered_glass", "dented")

    Returns:
        Benchmark issue_type (e.g., "crack", "dent")
    """
    normalized = raw_label.strip().lower().replace(" ", "_").replace("-", "_")
    return ISSUE_TYPE_CANONICAL.get(normalized, normalized)


def canonicalize_part(raw_label: str) -> str:
    """Map a Gemini-generated part label to the benchmark's allowed value.

    Args:
        raw_label: The raw label from Gemini (e.g., "bonnet", "touchpad")

    Returns:
        Benchmark object_part (e.g., "hood", "trackpad")
    """
    normalized = raw_label.strip().lower().replace(" ", "_").replace("-", "_")
    return PART_CANONICAL.get(normalized, normalized)


def severity_prior(issue_type: str) -> str:
    """Get the default severity for an issue type.

    Args:
        issue_type: The canonical issue type

    Returns:
        Default severity level
    """
    return SEVERITY_PRIORS.get(issue_type, "unknown")


def max_severity(sev_a: str, sev_b: str) -> str:
    """Return the higher of two severity levels.

    Args:
        sev_a: First severity level
        sev_b: Second severity level

    Returns:
        The higher severity level
    """
    a = SEVERITY_ORDER.get(sev_a, -1)
    b = SEVERITY_ORDER.get(sev_b, -1)
    if a >= b:
        return sev_a
    return sev_b


# =============================================================================
# RISK FLAG NORMALIZATION
# =============================================================================
# Only these risk flags are allowed in the output.
# Maps Gemini's free-form quality/risk labels to benchmark-allowed risk_flags.

VALID_RISK_FLAGS = {
    "none",
    "blurry_image",
    "cropped_or_obstructed",
    "low_light_or_glare",
    "wrong_angle",
    "wrong_object",
    "wrong_object_part",
    "damage_not_visible",
    "claim_mismatch",
    "possible_manipulation",
    "non_original_image",
    "text_instruction_present",
    "user_history_risk",
    "manual_review_required",
}

# Maps Gemini/observation labels to benchmark-allowed risk_flags
RISK_FLAG_CANONICAL = {
    # Image quality flags
    "blurry": "blurry_image",
    "blurred": "blurry_image",
    "out_of_focus": "blurry_image",
    "low_light": "low_light_or_glare",
    "glare": "low_light_or_glare",
    "overexposed": "low_light_or_glare",
    "underexposed": "low_light_or_glare",
    "dark": "low_light_or_glare",
    "bright": "low_light_or_glare",
    "wrong_angle": "wrong_angle",
    "bad_angle": "wrong_angle",
    "poor_angle": "wrong_angle",
    "side_angle": "wrong_angle",
    "cropped": "cropped_or_obstructed",
    "obstructed": "cropped_or_obstructed",
    "cut_off": "cropped_or_obstructed",
    "partial_view": "cropped_or_obstructed",

    # Object/relevance flags
    "wrong_object": "wrong_object",
    "not_relevant": "wrong_object",
    "irrelevant": "wrong_object",
    "wrong_object_part": "wrong_object_part",
    "wrong_part": "wrong_object_part",

    # Damage visibility flags
    "damage_not_visible": "damage_not_visible",
    "no_damage_visible": "damage_not_visible",
    "unclear_damage": "damage_not_visible",

    # Claim mismatch flags
    "claim_mismatch": "claim_mismatch",
    "mismatch": "claim_mismatch",
    "contradicts_claim": "claim_mismatch",

    # Manipulation flags
    "possible_manipulation": "possible_manipulation",
    "manipulation": "possible_manipulation",
    "suspicious": "possible_manipulation",
    "non_original_image": "non_original_image",
    "non_original": "non_original_image",
    "stock_photo": "non_original_image",
    "internet_image": "non_original_image",

    # Text flags
    "text_instruction": "text_instruction_present",
    "text_present": "text_instruction_present",
    "written_instruction": "text_instruction_present",

    # History flags (passed through from history_scorer)
    "user_history_risk": "user_history_risk",
    "manual_review_required": "manual_review_required",
}


def normalize_risk_flags(raw_flags: List[str]) -> List[str]:
    """Normalize a list of raw risk flags to benchmark-allowed values.

    Args:
        raw_flags: List of raw risk flag strings from observations/claims

    Returns:
        Deduplicated list of valid risk_flags
    """
    normalized = []
    seen = set()
    for flag in raw_flags:
        canonical = RISK_FLAG_CANONICAL.get(flag.strip().lower(), flag.strip().lower())
        if canonical in VALID_RISK_FLAGS and canonical != "none" and canonical not in seen:
            normalized.append(canonical)
            seen.add(canonical)
    return normalized
