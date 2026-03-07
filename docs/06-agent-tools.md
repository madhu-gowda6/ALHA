# Agent MCP Tools

The `alha-agent` exposes 9 tools via an in-process MCP server (`create_sdk_mcp_server`). Claude drives the agentic loop and calls these tools in sequence according to the consultation protocol.

All tools are registered under the `alha` MCP namespace: `mcp__alha__<tool_name>`.

---

## Tool: `symptom_interview`

**File:** `tools/symptom_interview.py`

Displays a structured symptom interview overlay in the Flutter UI. Claude generates 1–3 targeted follow-up questions and their Hindi translations before calling this tool.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `questions` | string[] | Yes | Up to 3 questions in English |
| `questions_hi` | string[] | Yes | Same questions in Hindi |

**Side Effect:** Sends `frontend_action: symptom_interview` via WebSocket to Flutter.

**Agent next step:** Wait silently for `symptom_answers` WebSocket message.

---

## Tool: `request_image`

**File:** `tools/request_image.py`

Triggers the camera/gallery overlay in Flutter. Called when visual diagnosis is required.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `prompt_text` | string | Yes | English prompt |
| `prompt_text_hi` | string | Yes | Hindi prompt |

**Side Effect:** Sends `frontend_action: request_image` via WebSocket.

**Agent next step:** Wait for `image_data` WebSocket message.

---

## Tool: `classify_disease`

**File:** `tools/classify_disease.py`

Classifies livestock disease from an uploaded S3 image. Uses a three-branch strategy:

1. **Claude-only mode** (`REKOGNITION_CLAUDE=true`): Claude vision only via Bedrock.
2. **Normal mode**: Rekognition Custom Labels → Claude double-check. If they disagree, Claude wins.
3. **Rekognition error fallback**: Falls through to Claude vision.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `s3_image_key` | string | Yes | Must start with `uploads/`, no `..` |
| `animal_type` | string | Yes | `cattle` \| `poultry` \| `buffalo` |

**Output:**
```json
{
  "disease": "lumpy_skin_disease",
  "confidence": 87.5,
  "bbox": { "left": 0.2, "top": 0.3, "width": 0.4, "height": 0.3 },
  "source": "rekognition"
}
```

**Soft failure** (image unclear):
```json
{ "disease": null, "confidence": 0.0, "bbox": null, "soft_failure": true, "message": "...", "message_hi": "..." }
```

**Side Effect:** Sends `diagnosis` WebSocket message to Flutter.

---

## Tool: `query_knowledge_base`

**File:** `tools/query_knowledge_base.py`

Retrieves treatment protocols from Amazon Bedrock Knowledge Base (ICAR/NDDB veterinary documents). Returns up to 5 relevant excerpts with S3 URI citations.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `disease_name` | string | Yes | e.g. `lumpy_skin_disease` |
| `animal_type` | string | Yes | Animal species |
| `language` | string | Yes | `hi` or `en` |

**Query format:** `"{disease_name} {animal_type} treatment protocol"`

**Output:**
```json
{
  "treatment_summary": "Full text of up to 5 KB results...",
  "citations": [{ "source": "s3://...", "text": "First 300 chars..." }],
  "found": true
}
```

Gracefully returns `found: false` when KB is not configured (`BEDROCK_KB_ID` empty).

---

## Tool: `assess_severity`

**File:** `tools/assess_severity.py`

Computes severity level from disease name + symptom context using a heuristic table. Broadcasts a severity badge to the Flutter UI.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `disease_name` | string | Yes | Snake-case disease label |
| `animal_type` | string | Yes | Animal species |
| `symptom_context` | string | Yes | Brief symptom summary |

**Output:**
```json
{ "severity": "CRITICAL", "session_id": "...", "disease_name": "lumpy_skin_disease" }
```

**Side Effect:** Sends `severity` WebSocket message to Flutter.

**Severity routing (drives next tool calls):**
- `CRITICAL` → `request_gps` immediately, skip vet preference card
- `HIGH` / `MEDIUM` → `request_gps`, show vet preference card after `vet_found`
- `LOW` / `NONE` → KB guidance only, `save_consultation`

---

## Tool: `request_gps`

**File:** `tools/request_gps.py`

Prompts the farmer to share their browser geolocation. Flutter shows an inline card — the actual GPS permission dialog opens from a user button tap (Chrome security requirement).

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `prompt_text` | string | Yes | English prompt |
| `prompt_text_hi` | string | Yes | Hindi prompt |

**Side Effect:** Sends `frontend_action: request_gps` via WebSocket.

**Agent next step:** Wait for `gps_data` WebSocket message.

---

## Tool: `find_nearest_vet`

**File:** `tools/find_nearest_vet.py`

Scans the `alha-vets` DynamoDB table (paginated), filters by `speciality` matching `animal_type`, then uses the Haversine formula to rank vets by distance. Returns the closest match.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `lat` | number | Yes | Farmer latitude |
| `lon` | number | Yes | Farmer longitude |
| `animal_type` | string | Yes | Filter by vet speciality |

**Output:**
```json
{
  "vet_id": "uuid",
  "name": "Dr. Ramesh Kumar",
  "speciality": "cattle",
  "distance_km": 4.7,
  "phone": "+919876543210",
  "lat": 28.63,
  "lon": 77.21,
  "session_id": "..."
}
```

**Side Effect:** Sends `vet_found` WebSocket message to Flutter.

**Haversine implementation:** `utils/haversine.py::haversine_km()` using Earth radius 6371 km.

---

## Tool: `send_notification`

**File:** `tools/send_notification.py`

Publishes dual transactional SMS via AWS SNS: one to the farmer (confirmation + vet name), one to the vet (farmer GPS location + case details as Google Maps link).

Soft-fails on `ClientError` (e.g. SNS Sandbox restrictions in development).

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Active session ID |
| `farmer_phone` | string | Yes | Farmer E.164 phone |
| `vet_phone` | string | Yes | Vet E.164 phone |
| `vet_name` | string | Yes | Vet display name |
| `disease_name` | string | Yes | Diagnosed disease |
| `severity` | string | Yes | Severity level |
| `lat` | number | Yes | Farmer latitude |
| `lon` | number | Yes | Farmer longitude |
| `confidence` | number | Yes | Confidence score 0–100 |
| `animal_type` | string | No | Animal species for vet SMS |

**SMS content:**
- Farmer: `"ALHA Alert: {disease} ({confidence}% confidence, {severity}). Nearest vet: {vet_name} is on their way. / ...Hindi..."`
- Vet: `"ALHA Emergency: Farmer has reported {disease} ({severity}) in their {animal_type}... Location: https://maps.google.com/?q={lat},{lon}"`

**Side Effect:** Sends `notification_sent` WebSocket message to Flutter.

---

## Tool: `save_consultation`

**File:** `tools/save_consultation.py`

Persists the completed consultation record to the `alha-consultations` DynamoDB table. Uses flat DynamoDB item format (no nested types). Always called at the end of every consultation, regardless of severity.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Consultation session ID (becomes PK) |
| `farmer_phone` | string | Yes | Stored unredacted for GSI |
| `animal_type` | string | Yes | Animal species |
| `disease_name` | string | Yes | Snake-case disease label |
| `confidence_score` | number | Yes | 0–100 |
| `severity` | string | Yes | Severity level |
| `vet_assigned` | string | Yes | Vet name or `"none"` |
| `vet_phone` | string | Yes | Redacted via `redact_phone()` before storage |
| `treatment_summary` | string | Yes | KB guidance (max 2000 chars) |
| `kb_citations` | string[] | Yes | Citation list → stored as JSON string |

**Side Effect:** Sends `session_complete` WebSocket message to Flutter.

---

## Consultation Tool-Calling Sequences

```
CRITICAL severity:
  symptom_interview → [symptom_answers] → request_image → [image_data]
  → classify_disease → query_knowledge_base → assess_severity
  → request_gps → [gps_data] → find_nearest_vet
  → send_notification → save_consultation

HIGH/MEDIUM (farmer accepts vet):
  ...assess_severity → request_gps → [gps_data] → find_nearest_vet
  → [vet_preference: yes] → send_notification → save_consultation

HIGH/MEDIUM (farmer declines vet):
  ...find_nearest_vet → [vet_preference: no] → save_consultation

LOW/NONE:
  symptom_interview → [symptom_answers] → query_knowledge_base
  → assess_severity → save_consultation
```

---

## Security: PII Handling

- **Farmer phone** stored unredacted in `farmer_phone` DynamoDB attribute (required for GSI query matching JWT claim).
- **Vet phone** stored redacted: `+91XXXXX{last4}` via `hooks/pii_filter_hook.py::redact_phone()`.
- **CloudWatch logs**: `PIIFilterHook` redacts phone numbers in `save_consultation` tool output before logging.
- **S3 image keys**: Validated with `startswith("uploads/")` + no `..` to prevent cross-session access.
- **Message length**: Chat messages capped at 2000 chars; symptom answers: question 500, answer 1000.
- **History cap**: Max 40 conversation entries per session to prevent unbounded memory growth.
