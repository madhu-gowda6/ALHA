"""Quick standalone debug script to test claude_agent_sdk with Bedrock."""
import asyncio
import os
import sys

# Must remove CLAUDECODE from os.environ BEFORE the SDK reads it.
# The SDK always does {**os.environ, **user_env, ...} so popping from sdk_env
# is not enough — os.environ is the base layer.
os.environ.pop("CLAUDECODE", None)

# Minimal env for Bedrock
os.environ.setdefault("CLAUDE_CODE_USE_BEDROCK", "1")
os.environ.setdefault("CLAUDE_CODE_ACCEPT_TOS", "1")
os.environ.setdefault("CLAUDE_CODE_SKIP_SETUP", "1")
os.environ.setdefault("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
# Dummy values so config.py doesn't crash on missing required vars
os.environ.setdefault("CONSULTATIONS_TABLE", "alha-consultations")
os.environ.setdefault("VETS_TABLE", "alha-vets")
os.environ.setdefault("S3_IMAGE_BUCKET", "alha-images")

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import StreamEvent


def on_stderr(line: str) -> None:
    print(f"[CLAUDE STDERR] {line}", file=sys.stderr, flush=True)


async def main():
    model = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    print(f"Testing with model: {model}", flush=True)

    try:
        sdk_env = {**os.environ, "CLAUDE_CODE_ACCEPT_TOS": "1"}
        sdk_env.pop("CLAUDECODE", None)  # prevent nested-session block
        async for event in query(
            prompt="Say hello in one sentence.",
            options=ClaudeAgentOptions(
                system_prompt="You are a helpful assistant.",
                allowed_tools=[],
                max_turns=1,
                include_partial_messages=True,
                model=model,
                env=sdk_env,
                stderr=on_stderr,
            ),
        ):
            if isinstance(event, StreamEvent):
                raw = event.event
                if raw.get("type") == "content_block_delta":
                    delta = raw.get("delta", {})
                    if delta.get("type") == "text_delta":
                        print(delta.get("text", ""), end="", flush=True)
        print("\n[DONE]", flush=True)
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
