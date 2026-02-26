"""Tool: symptom_interview — structured symptom collection from farmer."""
# from claude_agent_sdk import tool  # enabled in Epic 2


# @tool(
#     "symptom_interview",
#     "Collect structured symptom information from the farmer via conversation",
#     {
#         "type": "object",
#         "properties": {
#             "session_id": {"type": "string"},
#             "farmer_response": {"type": "string"},
#         },
#         "required": ["session_id", "farmer_response"],
#     },
# )
async def symptom_interview(session_id: str, farmer_response: str) -> dict:
    """Collect and structure symptom data from farmer input."""
    pass
