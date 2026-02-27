"""Tool: query_knowledge_base — retrieve treatment protocols from Bedrock KB."""
import json
from datetime import datetime

import boto3
import structlog
from botocore.exceptions import ClientError
from claude_agent_sdk import tool

from config import config

log = structlog.get_logger()

# Module-level client — created once, reused per call
_bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime", region_name=config.aws_region
)


@tool(
    "query_knowledge_base",
    "Query the veterinary knowledge base for treatment protocols. "
    "Returns up to 5 relevant ICAR/NDDB document excerpts with citations. "
    "Always call after disease is classified before giving treatment guidance.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active session ID"},
            "disease_name": {
                "type": "string",
                "description": "Diagnosed disease name (e.g. lumpy_skin_disease)",
            },
            "animal_type": {
                "type": "string",
                "description": "Animal species (cattle, poultry, buffalo)",
            },
            "language": {
                "type": "string",
                "description": "Response language code: hi or en",
            },
        },
        "required": ["session_id", "disease_name", "animal_type", "language"],
    },
)
async def query_knowledge_base(args: dict) -> dict:
    """Retrieve treatment protocols from Bedrock Knowledge Base."""
    session_id = args.get("session_id", "")
    disease_name = args.get("disease_name", "")
    animal_type = args.get("animal_type", "cattle")
    language = args.get("language", "hi")

    start_time = datetime.utcnow()

    if not config.bedrock_kb_id:
        # KB not configured — return graceful empty result
        result = {
            "treatment_summary": "",
            "citations": [],
            "found": False,
            "note": "Knowledge base not configured",
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    try:
        query_text = f"{disease_name} {animal_type} treatment protocol"
        response = _bedrock_agent_runtime.retrieve(
            knowledgeBaseId=config.bedrock_kb_id,
            retrievalQuery={"text": query_text},
        )

        retrieval_results = response.get("retrievalResults", [])
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        if not retrieval_results:
            result = {
                "treatment_summary": "",
                "citations": [],
                "found": False,
            }
            log.info(
                "tool_executed",
                tool_name="query_knowledge_base",
                session_id=session_id,
                disease_name=disease_name,
                citations_count=0,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        # Extract up to 5 results
        citations = []
        summary_parts = []
        for item in retrieval_results[:5]:
            text = item.get("content", {}).get("text", "")
            uri = item.get("location", {}).get("s3Location", {}).get("uri", "")
            if text:
                summary_parts.append(text)
                citations.append({"source": uri, "text": text[:300]})

        treatment_summary = "\n\n".join(summary_parts)
        result = {
            "treatment_summary": treatment_summary,
            "citations": citations,
            "found": True,
        }

        log.info(
            "tool_executed",
            tool_name="query_knowledge_base",
            session_id=session_id,
            disease_name=disease_name,
            citations_count=len(citations),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    except ClientError as exc:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        log.error(
            "bedrock_kb_error",
            session_id=session_id,
            error=str(exc),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        result = {
            "error": True,
            "code": "KB_ERROR",
            "message": "Knowledge base unavailable",
            "message_hi": "ज्ञान आधार अनुपलब्ध",
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
