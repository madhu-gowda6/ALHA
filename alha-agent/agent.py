"""
ALHA Agent — Claude Agent SDK configuration and MCP server.
Implemented fully in Epic 2. This file is the scaffold stub.
"""
import os

import structlog

log = structlog.get_logger()

# Bedrock backend activated via CLAUDE_CODE_USE_BEDROCK=1 env var (set in ECS task def)
# SDK import deferred until Epic 2 full implementation
# from claude_agent_sdk import tool, create_sdk_mcp_server

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")


def load_system_prompt() -> str:
    with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


# Placeholder: MCP server will be created in Epic 2
# mcp_server = create_sdk_mcp_server(tools=[...])
