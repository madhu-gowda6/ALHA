# Data Models

## DynamoDB Tables

### `alha-consultations`

Primary key: `session_id` (String, Hash)
GSI: `gsi-farmer-phone` — partition key: `farmer_phone`

| Attribute | Type | Description |
|-----------|------|-------------|
| `session_id` | String (PK) | UUID v4 — consultation session identifier |
| `farmer_phone` | String | E.164 phone number (unredacted for GSI query) |
| `animal_type` | String | `cattle` \| `poultry` \| `buffalo` |
| `disease_name` | String | Snake-case disease label (e.g. `lumpy_skin_disease`) |
| `confidence_score` | Number | 0–100 float |
| `severity` | String | `CRITICAL` \| `HIGH` \| `MEDIUM` \| `LOW` \| `NONE` |
| `vet_assigned` | String | Vet display name or `"none"` |
| `vet_phone` | String | Redacted format: `+91XXXXX1234` |
| `treatment_summary` | String | KB treatment text (max 2000 chars) |
| `kb_citations` | String | JSON-serialized array of citation strings |
| `timestamp` | String | ISO 8601 UTC (e.g. `2026-03-05T10:30:00Z`) |

---

### `alha-vets`

Primary key: `vet_id` (String, Hash)

| Attribute | Type | Description |
|-----------|------|-------------|
| `vet_id` | String (PK) | UUID |
| `name` | String | Vet display name |
| `phone` | String | E.164 phone number |
| `speciality` | String | `cattle` \| `poultry` \| `buffalo` |
| `lat` | Number | Latitude (decimal degrees) |
| `lon` | Number | Longitude (decimal degrees) |
| `district` | String | District name |
| `state` | String | State name |

---

### `alha-farmers`

Primary key: `phone_number` (String, Hash)

| Attribute | Type | Description |
|-----------|------|-------------|
| `phone_number` | String (PK) | E.164 phone number |
| *(additional attributes TBD)* | | |

---

### `alha-disease-models`

Primary key: `animal_type` (String, Hash)

| Attribute | Type | Description |
|-----------|------|-------------|
| `animal_type` | String (PK) | `cattle` \| `poultry` |
| `model_arn` | String | AWS Rekognition Custom Labels project version ARN |

---

## Python (Pydantic) Models — `alha-agent`

### `Consultation` (`models/consultation.py`)
```python
class Consultation(BaseModel):
    session_id: str
    farmer_phone: str
    animal_type: str
    disease_name: Optional[str] = None
    confidence_score: Optional[float] = None
    severity: Optional[str] = None
    vet_assigned: Optional[str] = None
    vet_phone: Optional[str] = None
    treatment_summary: Optional[str] = None
    timestamp: Optional[str] = None
    kb_citations: list[str] = []
```

### `Vet` (`models/vet.py`)
```python
class Vet(BaseModel):
    vet_id: str
    name: str
    phone: str
    speciality: str
    lat: float
    lon: float
    district: str
    state: str
```

### WebSocket Message Types (`models/ws_messages.py`)

**Inbound:**
- `ChatMessage` — `type="chat"`, `session_id`, `message`, `language: "hi"|"en"`

**Outbound:**
- `TokenMessage` — `type="token"`, `text`
- `ResponseCompleteMessage` — `type="response_complete"`
- `ErrorMessage` — `type="error"`, `message`, `message_hi`
- `ImageRequestMessage` — `type="image_request"`, `upload_url`, `prompt`, `prompt_hi`
- `GPSRequestMessage` — `type="gps_request"`, `prompt`, `prompt_hi`
- `ToolCallMessage` — `type="tool_call"`, `tool_name`, `tool_input`

### `LoginRequest` (`app.py`)
```python
class LoginRequest(BaseModel):
    username: str
    password: str
```

---

## Dart Models — `alha` Flutter PWA

### `Message` (`lib/models/message.dart`)
```dart
enum MessageType { text, image, error, system, typing, diagnosis, severity, vetFound }

class Message {
  final String id;               // millisecondsSinceEpoch string
  final String content;          // display text
  final bool isUser;             // true = farmer bubble, false = agent bubble
  final DateTime timestamp;
  final MessageType type;        // controls which widget renders it
  final String? language;        // "hi" or "en"
  final String? messageHi;       // Hindi version for error messages
  final String? imageUrl;
  final DiagnosisData? diagnosisData;  // populated for MessageType.diagnosis
  final String? severityLevel;         // populated for MessageType.severity
  final VetData? vetData;              // populated for MessageType.vetFound
}
```

### `DiagnosisData`
```dart
class DiagnosisData {
  final String? disease;      // snake_case disease name
  final double confidence;    // 0–100
  final BboxData? bbox;       // normalized bounding box
  final String s3Key;         // for ImageBubble rendering
}

class BboxData {
  final double left, top, width, height;  // normalized 0–1
}
```

### `VetData`
```dart
class VetData {
  final String name;
  final String speciality;
  final double distanceKm;
  final String phone;
}
```

### `Consultation` (`lib/models/consultation.dart`)
Maps to the history API response:
```dart
class Consultation {
  final String consultationId;
  final String animalType;
  final String? diseaseName;
  final double? confidenceScore;
  final String? severity;
  final String? vetAssigned;
  final String? treatmentSummary;
  final String? kbCitations;   // JSON-encoded citation array
  final String timestamp;      // ISO 8601
}
```

---

## In-Memory Session State — `alha-agent`

The agent maintains the following per-session dictionaries in process memory (non-persistent across restarts):

| Variable | Type | Description |
|----------|------|-------------|
| `_session_histories` | `dict[str, list[dict]]` | Conversation history (max 40 entries) |
| `_session_languages` | `dict[str, str]` | Language detected on first chat message |
| `_session_farmer_phones` | `dict[str, str]` | Farmer phone from JWT on connection |
| `_session_locks` | `dict[str, asyncio.Lock]` | Per-session serialization lock |
| `_pending_action_sessions` | `dict[str, Optional[str]]` | Tracks expected inbound WS message type |
| `_active_ws_map` | `dict[str, WebSocket]` | Live WS connection (used by MCP tools) |

History format: `[{"role": "user"|"assistant", "content": str}, ...]`

---

## Disease Classification Severity Table

| Disease | Severity |
|---------|----------|
| `lumpy_skin_disease` | CRITICAL |
| `newcastle_disease` | CRITICAL |
| `anthrax` | CRITICAL |
| `foot_and_mouth_disease` | HIGH |
| `foot_and_mouth` | HIGH |
| `brucellosis` | HIGH |
| `blackleg` | HIGH |
| Any other known disease | MEDIUM |
| Routine/preventive query | LOW |
| No disease identified | NONE |

### Disease → Hindi Name Mapping

| Disease Code | Hindi Name |
|-------------|-----------|
| `lumpy_skin_disease` | लम्पी स्किन रोग |
| `newcastle_disease` | रानीखेत रोग |
| `foot_and_mouth_disease` | खुरपका-मुंहपका रोग |
| `blackleg` | काला पांव |
| `anthrax` | एंथ्रेक्स (तिल्ली ज्वर) |
| `brucellosis` | ब्रुसेलोसिस |
