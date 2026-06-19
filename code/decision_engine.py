"""
Deterministic Decision Engine.

Combines Gemini observations with rules to produce final claim decisions.
All fields that Gemini does NOT produce are computed here.
"""

from typing import Dict, Any, List, Tuple

from mappings import severity_prior, max_severity, normalize_risk_flags


def decide_claim_status(
    extracted_claim: Dict[str, Any],
    image_observations: List[Dict[str, Any]],
    evidence_met: bool,
) -> Tuple[str, str]:
    """Decide supported / contradicted / not_enough_information.

    Rules derived from sample_claims.csv patterns.
    """
    if not evidence_met:
        return "not_enough_information", "Evidence requirements not met"

    claim_object = extracted_claim.get("claim_object", "unknown")
    claimed_part = extracted_claim.get("claimed_object_part", "unknown")
    claimed_issue = extracted_claim.get("claimed_issue_type", "none")
    is_exaggeration = extracted_claim.get("is_severity_exaggeration_risk", False)

    relevant_obs = [
        obs for obs in image_observations
        if obs.get("visible_object") == claim_object
    ]

    if not relevant_obs:
        any_relevant = [
            obs for obs in image_observations
            if obs.get("image_quality", {}).get("is_relevant_to_claim", True)
        ]
        if any_relevant:
            return (
                "not_enough_information",
                "The submitted images do not show the claimed object type",
            )
        return (
            "not_enough_information",
            "No images provide relevant evidence for this claim",
        )

    wrong_object = any(
        obs.get("visible_object") != claim_object
        for obs in image_observations
        if obs.get("visible_object") not in ("unrecognizable", "other_object")
    )
    if wrong_object:
        return "contradicted", "The images do not show the claimed object type"

    all_visible_parts = set()
    for obs in relevant_obs:
        all_visible_parts.update(obs.get("visible_parts", []))

    any_damage_on_claimed_part = False
    damage_on_different_part = False
    no_visible_damage = True
    for obs in relevant_obs:
        for damage in obs.get("visible_damage", []):
            if damage.get("issue_type") != "none":
                no_visible_damage = False
                if damage.get("part") == claimed_part:
                    any_damage_on_claimed_part = True
                else:
                    damage_on_different_part = True

    if any_damage_on_claimed_part:
        return "supported", "Damage is visible on the claimed part"

    if claimed_part not in all_visible_parts and not any_damage_on_claimed_part:
        return "not_enough_information", (
            f"The claimed {claimed_part} is not visible in the submitted images"
        )

    if no_visible_damage:
        return "not_enough_information", (
            "The claimed area is visible but shows no physical damage"
        )

    if damage_on_different_part:
        for obs in relevant_obs:
            for damage in obs.get("visible_damage", []):
                if damage.get("issue_type") != "none" and damage.get("part") != claimed_part:
                    return "contradicted", (
                        f"The images show {damage['issue_type']} on the "
                        f"{damage['part']}, but the claim is about "
                        f"{claimed_part}"
                    )

    return "not_enough_information", (
        "Could not verify the claim from the submitted images"
    )


def collect_risk_flags(
    image_observations: List[Dict[str, Any]],
    extracted_claim: Dict[str, Any],
    history_flags: List[str],
) -> List[str]:
    """Collect all risk flags from observations, claim, and history."""
    raw_flags = []

    for obs in image_observations:
        q = obs.get("image_quality", {})
        if q.get("is_blurry"):
            raw_flags.append("blurry_image")
        if q.get("is_low_light"):
            raw_flags.append("low_light_or_glare")
        if q.get("is_wrong_angle"):
            raw_flags.append("wrong_angle")
        if q.get("is_cropped_or_obstructed"):
            raw_flags.append("cropped_or_obstructed")
        if not q.get("is_relevant_to_claim", True):
            raw_flags.append("wrong_object")

    conversation_notes = extracted_claim.get("conversation_notes", "")
    if "ignore" in conversation_notes.lower():
        raw_flags.append("text_instruction_present")

    for hf in history_flags:
        if hf:
            raw_flags.append(hf)

    return normalize_risk_flags(raw_flags)


def determine_severity(
    image_observations: List[Dict[str, Any]],
    claimed_severity: str = "unknown",
    claim_status: str = "unknown",
    claimed_issue_type: str = "unknown",
) -> str:
    """Determine final severity from image observations.

    For supported claims: use severity_prior of the claimed issue type.
    For contradicted/NEI: use max of severity priors of observed damage.
    """
    if claim_status == "supported" and claimed_issue_type != "unknown":
        return severity_prior(claimed_issue_type)

    combined = "none"
    for obs in image_observations:
        for damage in obs.get("visible_damage", []):
            issue_type = damage.get("issue_type", "none")
            if issue_type == "none":
                continue
            sev = severity_prior(issue_type)
            combined = max_severity(combined, sev)
    return combined


def determine_supporting_images(
    image_observations: List[Dict[str, Any]],
    extracted_claim: Dict[str, Any],
    claim_status: str,
    resolved_issue_type: str = None,
    resolved_object_part: str = None,
) -> str:
    """Determine which image IDs support the decision.

    For supported: match against claimed issue/part.
    For contradicted: match against resolved (observed) issue/part.
    For not_enough_information: return "none".
    """
    if claim_status == "not_enough_information":
        return "none"

    if claim_status == "contradicted" and resolved_issue_type and resolved_object_part:
        match_issue = resolved_issue_type
        match_part = resolved_object_part
    else:
        match_issue = extracted_claim.get("claimed_issue_type", "none")
        match_part = extracted_claim.get("claimed_object_part", "unknown")

    supporting = []
    for obs in image_observations:
        for damage in obs.get("visible_damage", []):
            if (
                damage.get("issue_type") == match_issue
                and damage.get("part") == match_part
            ):
                image_id = obs.get("image_id", "")
                if image_id and image_id not in supporting:
                    supporting.append(image_id)
                break

    if not supporting and claim_status == "supported":
        for obs in image_observations:
            if obs.get("image_quality", {}).get("is_relevant_to_claim", True):
                image_id = obs.get("image_id", "")
                if image_id:
                    supporting.append(image_id)
                    break

    return ";".join(supporting) if supporting else "none"


def determine_valid_image(image_observations: List[Dict[str, Any]]) -> bool:
    """Determine if the image set is usable for automated review."""
    return any(
        obs.get("image_quality", {}).get("is_relevant_to_claim", True)
        and obs.get("image_quality", {}).get("confidence", "low") in ("high", "medium")
        for obs in image_observations
    )


def build_justification(
    claim_status: str,
    extracted_claim: Dict[str, Any],
    image_observations: List[Dict[str, Any]],
) -> str:
    """Build final justification string."""
    if claim_status == "supported":
        for obs in image_observations:
            for damage in obs.get("visible_damage", []):
                if (
                    damage.get("issue_type") == extracted_claim.get("claimed_issue_type")
                    and damage.get("part") == extracted_claim.get("claimed_object_part")
                ):
                    return damage.get("description", obs.get("observation_summary", "Visible evidence supports the claim"))
        return "The visible evidence supports the claim"

    elif claim_status == "contradicted":
        for obs in image_observations:
            summary = obs.get("observation_summary", "")
            if summary:
                return summary
        return "The visible evidence contradicts the claim"

    else:
        for obs in image_observations:
            if not obs.get("image_quality", {}).get("is_relevant_to_claim", True):
                return "The submitted images do not provide evidence for the claimed damage"
        return "The submitted images do not contain enough information to verify the claim"


def resolve_output_fields(
    claim_status: str,
    extracted_claim: Dict[str, Any],
    image_observations: List[Dict[str, Any]],
    severity: str,
) -> Tuple[str, str, str]:
    """Return (issue_type, object_part, severity) adjusted for claim_status.

    - supported: use claimed fields (claim matches observation)
    - contradicted: use observed damage fields (claim is wrong)
    - not_enough_information: issue_type="unknown", keep claimed part, severity="unknown"
    """
    if claim_status == "supported":
        return (
            extracted_claim.get("claimed_issue_type", "none"),
            extracted_claim.get("claimed_object_part", "unknown"),
            severity,
        )

    if claim_status == "not_enough_information":
        return (
            "unknown",
            extracted_claim.get("claimed_object_part", "unknown"),
            "unknown",
        )

    # contradicted — find the observed damage that contradicts the claim
    claimed_part = extracted_claim.get("claimed_object_part", "unknown")

    # First: damage on a DIFFERENT part than claimed
    for obs in image_observations:
        for damage in obs.get("visible_damage", []):
            if damage.get("issue_type") != "none" and damage.get("part") != claimed_part:
                return (
                    damage.get("issue_type", "unknown"),
                    damage.get("part", "unknown"),
                    severity,
                )

    # Fallback: damage on the SAME part but different type
    for obs in image_observations:
        for damage in obs.get("visible_damage", []):
            if damage.get("issue_type") != "none":
                return (
                    damage.get("issue_type", "unknown"),
                    damage.get("part", "unknown"),
                    severity,
                )

    # No damage observed at all
    return ("unknown", "unknown", severity)
