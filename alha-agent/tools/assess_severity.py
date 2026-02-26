"""Tool: assess_severity — determine case severity from symptoms and diagnosis."""
import structlog

log = structlog.get_logger()

SEVERITY_LEVELS = ("mild", "moderate", "severe", "emergency")


async def assess_severity(
    session_id: str, disease_name: str, symptoms: list[str], animal_type: str
) -> dict:
    """
    Assess severity of a diagnosed condition.

    Returns:
        dict with severity (mild/moderate/severe/emergency), rationale,
        rationale_hi, escalate_to_vet (bool).
    """
    pass
