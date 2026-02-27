FROM python:3.12-slim

WORKDIR /app

# Install Node.js (required for claude CLI) and curl
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install claude CLI (Claude Code — required by claude_agent_sdk subprocess)
RUN npm install -g @anthropic-ai/claude-code --prefer-offline || \
    npm install -g @anthropic-ai/claude-code

# Accept Claude Code TOS and configure Bedrock defaults
# CLAUDE_CODE_SKIP_SETUP=1      — skips interactive onboarding/browser auth
# CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 — disables telemetry/update checks
ENV CLAUDE_CODE_ACCEPT_TOS=1 \
    CLAUDE_CODE_SKIP_SETUP=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6 \
    CLAUDE_CODE_USE_BEDROCK=1 \
    AWS_REGION=us-east-1

# Pre-initialise the claude config directory so first-run doesn't try to write
# interactively. Also verify the binary is on PATH.
RUN mkdir -p /root/.claude && claude --version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
