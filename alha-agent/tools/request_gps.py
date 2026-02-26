"""Tool: request_gps — ask farmer to share GPS coordinates."""
import structlog

log = structlog.get_logger()


async def request_gps(session_id: str) -> dict:
    """
    Send a GPS coordinate request to the farmer's Flutter client.

    Returns:
        dict with latitude, longitude once farmer responds.
    """
    pass
