"""Quick standalone debug script to test claude_agent_sdk with Bedrock.

Usage:
    python debug_sdk.py           — test 1: basic SDK, no tools (original test)
    python debug_sdk.py mcp       — test 2: MCP server with mcp__alha__ prefixed allowed_tools
    python debug_sdk.py mcp-simple — test 3: MCP server with simple (non-prefixed) allowed_tools
    python debug_sdk.py mcp-none  — test 4: MCP server with NO allowed_tools restriction
"""
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
# Mock Rekognition so classify_disease tool doesn't need real ARNs
os.environ.setdefault("REKOGNITION_MOCK", "true")

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import StreamEvent


def on_stderr(line: str) -> None:
    print(f"[CLAUDE STDERR] {line}", file=sys.stderr, flush=True)


async def run_test(label: str, prompt, allowed_tools: list, mcp_servers: dict, max_turns: int = 1, system_prompt: str = "You are a helpful assistant."):
    model = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    print(f"\n{'='*60}", flush=True)
    print(f"TEST: {label}", flush=True)
    print(f"Model: {model}", flush=True)
    print(f"Tools: {allowed_tools or 'none'}", flush=True)
    print(f"MCP servers: {list(mcp_servers.keys()) or 'none'}", flush=True)
    print(f"{'='*60}", flush=True)

    sdk_env = {**os.environ, "CLAUDE_CODE_ACCEPT_TOS": "1", "ANTHROPIC_CUSTOM_HEADERS": ""}
    sdk_env.pop("CLAUDECODE", None)

    tool_calls_seen = []
    try:
        async for event in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=allowed_tools,
                mcp_servers=mcp_servers,
                max_turns=max_turns,
                include_partial_messages=True,
                model=model,
                env=sdk_env,
                stderr=on_stderr,
            ),
        ):
            if isinstance(event, StreamEvent):
                raw = event.event
                evt_type = raw.get("type", "?")
                # Log all non-delta event types for debugging
                if evt_type == "content_block_delta":
                    delta = raw.get("delta", {})
                    if delta.get("type") == "text_delta":
                        print(delta.get("text", ""), end="", flush=True)
                    elif delta.get("type") == "input_json_delta":
                        pass  # tool input streaming, skip
                elif evt_type == "content_block_start":
                    cb = raw.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        tool_name = cb.get("name", "?")
                        tool_calls_seen.append(tool_name)
                        print(f"\n  [TOOL_USE] {tool_name} (id={cb.get('id','')})", flush=True)
                    elif cb.get("type") == "text":
                        pass  # text block start
                elif evt_type == "content_block_stop":
                    pass
                elif evt_type in ("message_start", "message_stop", "message_delta"):
                    if evt_type == "message_start":
                        msg = raw.get("message", {})
                        print(f"  [MSG_START] role={msg.get('role')} model={msg.get('model')}", flush=True)
                    elif evt_type == "message_delta":
                        delta = raw.get("delta", {})
                        print(f"  [MSG_DELTA] stop_reason={delta.get('stop_reason')}", flush=True)
                else:
                    # Log unknown event types
                    print(f"  [EVENT] {evt_type}: {str(raw)[:200]}", flush=True)

        print(f"\n  Tools called: {tool_calls_seen or 'NONE'}", flush=True)
        print(f"[PASS] {label}", flush=True)
        return True
    except Exception as e:
        # Unwrap ExceptionGroup to show root cause
        root = e
        if hasattr(e, "exceptions") and e.exceptions:
            root = e.exceptions[0]
        print(f"\n[FAIL] {label}", file=sys.stderr, flush=True)
        print(f"  outer: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        print(f"  root:  {type(root).__name__}: {root}", file=sys.stderr, flush=True)
        return False


async def run_raw_subprocess_test():
    """Run claude CLI directly to see its stderr/stdout when --mcp-config is used."""
    import json as _json
    import subprocess as _sp
    import shutil

    claude_bin = shutil.which("claude")
    if not claude_bin:
        # SDK bundles its own CLI
        from pathlib import Path
        bundled = Path(__file__).parent / ".venv/Lib/site-packages/claude_agent_sdk/_bundled/claude.exe"
        if not bundled.exists():
            bundled = Path(__file__).parent / ".venv/Lib/site-packages/claude_agent_sdk/_bundled/claude"
        claude_bin = str(bundled) if bundled.exists() else None
    if not claude_bin:
        print("[SKIP] claude binary not found", flush=True)
        return
    print(f"Using claude binary: {claude_bin}", flush=True)

    mcp_config = _json.dumps({"mcpServers": {"alha": {"type": "sdk", "name": "alha"}}})
    cmd_with_mcp = [
        claude_bin, "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--mcp-config", mcp_config,
        "--include-partial-messages",
        "--max-turns", "1",
        "--verbose",
    ]
    cmd_without_mcp = [
        claude_bin, "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--include-partial-messages",
        "--max-turns", "1",
        "--verbose",
    ]

    env = {**os.environ, "CLAUDE_CODE_ACCEPT_TOS": "1", "ANTHROPIC_CUSTOM_HEADERS": ""}
    env.pop("CLAUDECODE", None)

    for label, cmd in [("WITHOUT mcp-config", cmd_without_mcp), ("WITH mcp-config", cmd_with_mcp)]:
        print(f"\n{'='*60}", flush=True)
        print(f"RAW SUBPROCESS: {label}", flush=True)
        print(f"CMD: {' '.join(cmd[:6])}...", flush=True)
        print(f"{'='*60}", flush=True)
        try:
            proc = _sp.run(cmd, capture_output=True, text=True, timeout=15, env=env,
                           input='')  # empty stdin → immediate EOF
            print(f"  exit code: {proc.returncode}", flush=True)
            print(f"  stdout ({len(proc.stdout)} chars): {proc.stdout[:500]}", flush=True)
            print(f"  stderr ({len(proc.stderr)} chars): {proc.stderr[:500]}", flush=True)
        except _sp.TimeoutExpired:
            print("  [TIMEOUT after 15s — subprocess was alive]", flush=True)
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}", flush=True)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "basic"

    # Enable SDK debug logging for all modes
    import logging
    logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s",
                        stream=sys.stderr)

    # Skip version check to avoid potential subprocess interference
    os.environ["CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK"] = "1"

    # Monkey-patch SDK to trace the exact failure point
    from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
    _orig_connect = SubprocessCLITransport.connect
    _orig_write = SubprocessCLITransport.write
    _orig_end_input = SubprocessCLITransport.end_input

    async def traced_connect(self):
        print(f"[TRACE] connect() called, _ready={self._ready}", file=sys.stderr, flush=True)
        await _orig_connect(self)
        print(f"[TRACE] connect() done, _ready={self._ready}, process={self._process is not None}", file=sys.stderr, flush=True)
        # Log the full command that was built
        cmd = self._build_command()
        print(f"[TRACE] FULL subprocess cmd:", file=sys.stderr, flush=True)
        for i, arg in enumerate(cmd):
            print(f"  [{i}] {arg[:300]}", file=sys.stderr, flush=True)

    async def traced_write(self, data):
        snippet = data[:120].replace('\n', ' ')
        print(f"[TRACE] write() called, _ready={self._ready}, data={snippet}...", file=sys.stderr, flush=True)
        await _orig_write(self, data)
        print(f"[TRACE] write() done", file=sys.stderr, flush=True)

    async def traced_end_input(self):
        print(f"[TRACE] end_input() called, _ready={self._ready}", file=sys.stderr, flush=True)
        await _orig_end_input(self)
        print(f"[TRACE] end_input() done, _ready={self._ready}", file=sys.stderr, flush=True)

    SubprocessCLITransport.connect = traced_connect
    SubprocessCLITransport.write = traced_write
    SubprocessCLITransport.end_input = traced_end_input

    from claude_agent_sdk._internal.query import Query
    _orig_start = Query.start
    _orig_initialize = Query.initialize

    async def traced_start(self):
        print(f"[TRACE] query.start() called", file=sys.stderr, flush=True)
        await _orig_start(self)
        print(f"[TRACE] query.start() done, _tg={self._tg is not None}", file=sys.stderr, flush=True)

    async def traced_initialize(self):
        print(f"[TRACE] query.initialize() called", file=sys.stderr, flush=True)
        result = await _orig_initialize(self)
        print(f"[TRACE] query.initialize() done", file=sys.stderr, flush=True)
        return result

    Query.start = traced_start
    Query.initialize = traced_initialize

    if mode == "raw":
        # Test 0: raw subprocess to capture stderr from claude CLI
        await run_raw_subprocess_test()

    elif mode.startswith("mcp"):
        # MCP server tests — test tool naming conventions
        print("Loading ALHA MCP tools...", flush=True)
        from claude_agent_sdk import create_sdk_mcp_server
        from tools.classify_disease import classify_disease
        from tools.query_knowledge_base import query_knowledge_base
        from tools.request_image import request_image
        from tools.symptom_interview import symptom_interview

        mcp_server = create_sdk_mcp_server(
            name="alha",
            version="1.0.0",
            tools=[symptom_interview, request_image, classify_disease, query_knowledge_base],
        )

        # Load the real system prompt for more realistic testing
        sys_prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
        try:
            with open(sys_prompt_path, encoding="utf-8") as f:
                alha_system_prompt = f.read()
            print(f"Loaded system prompt ({len(alha_system_prompt)} chars)", flush=True)
        except FileNotFoundError:
            alha_system_prompt = "You are a veterinary AI assistant. Use the provided tools to help farmers."
            print("System prompt file not found, using fallback", flush=True)

        # Choose allowed_tools based on sub-mode
        if mode == "mcp":
            # Prefixed names — the way Claude Code references MCP tools internally
            allowed_tools = [
                "mcp__alha__symptom_interview",
                "mcp__alha__request_image",
                "mcp__alha__classify_disease",
                "mcp__alha__query_knowledge_base",
            ]
            test_label = "MCP with mcp__alha__ prefixed allowed_tools"
        elif mode == "mcp-simple":
            # Simple names — matches SDK example docs
            allowed_tools = ["symptom_interview", "request_image", "classify_disease", "query_knowledge_base"]
            test_label = "MCP with simple (non-prefixed) allowed_tools"
        elif mode == "mcp-none":
            # No allowed_tools — let Claude use any available tool
            allowed_tools = []
            test_label = "MCP with NO allowed_tools restriction"
        else:
            allowed_tools = []
            test_label = f"MCP unknown mode: {mode}"

        user_msg = "[session_id: debug-session-001]\n[language: en]\nFarmer: My cow has lumpy skin and fever. What should I do?"

        async def prompt_iter():
            yield {
                "type": "user",
                "session_id": "",
                "message": {"role": "user", "content": user_msg},
                "parent_tool_use_id": None,
            }

        await run_test(
            label=test_label,
            prompt=prompt_iter(),
            allowed_tools=allowed_tools,
            mcp_servers={"alha": mcp_server},
            max_turns=10,
            system_prompt=alha_system_prompt,
        )
    else:
        # Test 1: basic SDK, no tools (original smoke test)
        await run_test(
            label="Basic SDK — no tools",
            prompt="Say hello in one sentence.",
            allowed_tools=[],
            mcp_servers={},
            max_turns=1,
        )


if __name__ == "__main__":
    asyncio.run(main())
