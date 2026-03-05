# Flutter UI Components

## Application Entry Points

### `main.dart`
Entry point wraps the app in `ProviderScope` (Riverpod root). Defines two key wrappers:

- **`_OfflineGuard`** — Listens to `window.onOffline`/`window.onOnline` browser events. Shows a bilingual offline screen with a wifi-off icon when disconnected.
- **`_StartupRouter`** — On init, reads the stored JWT from `SharedPreferences`, validates expiry, and routes to `ChatScreen` (if valid) or `LoginScreen`.

---

## Screens

### `LoginScreen` (`screens/login_screen.dart`)
Simple credential form — username + password fields routed to `POST /api/auth/login`. On success, persists token + generates session UUID. Widget keys `Key('username_field')`, `Key('password_field')`, `Key('login_button')` for test targeting.

**Design:** Off-white `#F9F6F0` background, forest-green `#2E7D32` logo icon and button.

---

### `ChatScreen` (`screens/chat_screen.dart`)
The primary consultation interface. Uses `ConsumerStatefulWidget` to read `sessionProvider` and `chatProvider`.

**Responsibilities:**
- Connects `WebSocketService` on init; wires `chatProvider.setWsSendFn()`.
- Manages 4 `StreamSubscription`s for overlay triggers: `symptomInterviewTrigger`, `cameraOverlayTrigger`, `gpsRequestTrigger`, `vetPreferenceTrigger`.
- Renders message list via `ListView.builder` — dispatches to type-specific widgets.
- Handles voice input via `SpeechService`.
- Handles "new session" flow: cancels subscriptions, generates new UUID, resets providers, reconnects.

**Inline UI cards (shown between message list and input bar):**
- **GPS Request Card** — blue card with "Share Location" button; uses a button tap (user gesture) to trigger Chrome geolocation permission dialog.
- **Vet Preference Card** — green card with Yes / No buttons for HIGH/MEDIUM severity.
- **New Session Banner** — green card after `session_complete`.

**AppBar actions:** Profile, New Consultation, History, Language Toggle.

**`_ConnectionDot`** — Animated pulsing dot in AppBar indicating WebSocket state (green=connected, red=disconnected, pulsing=reconnecting).

---

### `HistoryScreen` (`screens/history_screen.dart`)
Fetches past consultations from `GET /api/history`. Displays as `ListView` with animal emoji icon, disease name, timestamp, and `SeverityBadge`. Pull-to-refresh supported. Tapping opens `_ConsultationDetail` showing full treatment summary and KB citations.

---

### `ProfileScreen` (`screens/profile_screen.dart`)
Decodes JWT claims client-side (base64url) to display username and phone number. Logout button clears `SharedPreferences` + `sessionProvider` and returns to `LoginScreen`.

---

## Providers (Riverpod)

### `sessionProvider` — `SessionNotifier` (`providers/session_provider.dart`)

Manages global auth + session state:

```
SessionState {
  sessionId: String?      // UUID v4
  authToken: String?      // Cognito JWT
  language: String        // "hi" (default) | "en"
  connectionState: WsConnectionState
}
```

**Methods:** `setAuth()`, `setLanguage()`, `setConnectionState()`, `setSessionId()`, `clearAuth()`, `detectLanguage(text)` (Devanagari Unicode range detection).

---

### `chatProvider` — `ChatNotifier` (`providers/chat_provider.dart`)

Central message bus. Processes all inbound WebSocket messages and manages streaming state.

```
ChatState {
  messages: List<Message>     // all rendered messages
  isStreaming: bool           // true while agent is responding
  currentStreamingText: str   // accumulates tokens into last bubble
  sessionComplete: bool       // true after session_complete WS event
}
```

**WS message handlers:**
| Message Type | Handler |
|-------------|---------|
| `token` | Appends to last assistant bubble or creates new one |
| `response_complete` | Clears streaming state |
| `error` | Adds error bubble, stops streaming |
| `frontend_action` | Routes to overlay stream controllers |
| `diagnosis` | Adds `MessageType.diagnosis` bubble |
| `severity` | Adds `MessageType.severity` bubble, tracks `_lastSeverity` |
| `vet_found` | Adds `MessageType.vetFound` bubble; triggers vet preference stream if HIGH/MEDIUM |
| `notification_sent` | Adds system message |
| `session_complete` | Adds system message, sets `sessionComplete = true` |

**Overlay guards:** Boolean flags (`_symptomInterviewPending`, `_cameraOverlayPending`, `_gpsRequestPending`, `_vetPreferencePending`) prevent duplicate overlay triggers from rapid WS messages.

---

### `cameraProvider` — `CameraNotifier` (`providers/camera_provider.dart`)

Manages image upload state. Key feature: `imageBytesMap: Map<String, Uint8List>` stores uploaded image bytes keyed by S3 key, so `ImageBubble` renders the correct image even after multiple uploads in the same session.

---

## Services

### `WebSocketService` (`services/websocket_service.dart`)

Manages persistent WebSocket connection to agent with automatic exponential-backoff reconnection (1s → 2s → 4s ... cap 30s).

**States:** `disconnected → connecting → connected → reconnecting`

**Methods:** `connect(url, token)`, `send(json)`, `disconnect()`, `dispose()`

**Streams:** `messages` (parsed JSON), `connectionStateStream` (state changes)

---

### `AuthService` (`services/auth_service.dart`)

Handles JWT storage (`SharedPreferences`) and client-side token validation:
- `login(username, password)` — POST to `/api/auth/login`
- `isLoggedIn()` — decodes JWT locally, checks `exp` claim
- `getTokenClaims()` — base64url decode payload without verification
- `getSessionId()` / `setSessionId()` — persists UUID

---

### `SpeechService` (`services/speech_service.dart`)

Wraps `speech_to_text` package. Supports bilingual recognition: `en_US` or `hi_IN` locale. Listens up to 30 seconds with 5-second pause timeout. Returns `finalResult` only (no partials).

---

### `LocationService` (`services/location_service.dart`)

Platform-conditional export:
- **Web** (`location_service_web.dart`): Uses `dart:html` `window.navigator.geolocation` API.
- **Non-web** (`location_service_stub.dart`): No-op stub for VM unit tests.

Returns `LocationResult { success, lat?, lon?, errorMessage? }`.

---

### `UploadService` (`services/upload_service.dart`)

Two-step image upload:
1. `getPresignedUrl(sessionId, authToken)` — POST `/api/upload-url` (15s timeout)
2. `uploadImage(uploadUrl, bytes)` — HTTP PUT to S3 presigned URL (30s timeout)

Throws `UploadException { message, messageHi }` on any failure.

---

## Widgets

### `TextBubble` (`widgets/text_bubble.dart`)
Renders chat messages (user/assistant/system/error). Uses `flutter_markdown` for agent responses to render formatted text including `**bold**`, lists, and the mandatory medical disclaimer.

### `ImageBubble` (`widgets/image_bubble.dart`)
Renders disease diagnosis results: shows the uploaded image with `BoundingBoxOverlay` if a `bbox` is present, disease name, confidence %, and a disclaimer.

### `BoundingBoxOverlay` (`widgets/bounding_box_overlay.dart`)
Draws a colored rectangle on top of the diagnosis image using normalized bbox coordinates.

### `SeverityBadge` (`widgets/severity_badge.dart`)
Color-coded chip: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green, NONE=grey.

### `VetCard` (`widgets/vet_card.dart`)
Shows vet name, speciality, distance, and a tappable phone number (via `platform/phone_launcher_web.dart` which calls `window.open('tel:...')`).

### `SymptomInterviewOverlay` (`widgets/symptom_interview_overlay.dart`)
Modal bottom sheet with structured Q&A form. Non-dismissible. Collects answers and calls `onComplete(answers)` which sends `symptom_answers` WS message.

### `CameraOverlay` (`widgets/camera_overlay.dart`)
Modal bottom sheet with Camera / Gallery buttons. Uses `ImagePicker` → `UploadService` pipeline. Shows upload progress spinner. Language-aware button labels.

### `InputBar` (`widgets/input_bar.dart`)
Text input + send + voice buttons. Disabled while `isStreaming`. Exposes `GlobalKey<InputBarState>` so `ChatScreen` can inject voice transcripts via `setVoiceText()`.

### `LanguageToggle` (`widgets/language_toggle.dart`)
AppBar segmented toggle: `EN` / `हि`. Sets `sessionProvider.language`.

### `TypingIndicator` (`widgets/typing_indicator.dart`)
Animated dots shown as last list item when `isStreaming=true` and no text has arrived yet.

### `VoiceButton` (`widgets/voice_button.dart`)
Microphone button with animated active state. Reused in `InputBar`.

---

## Platform Adapters

### `phone_launcher` (`platform/`)

Platform-conditional export:
- **Web** (`phone_launcher_web.dart`): `window.open('tel:{phone}')` via `dart:html`
- **Non-web** (`phone_launcher_stub.dart`): No-op stub

---

## Theme (`config/theme.dart`)

| Token | Value | Usage |
|-------|-------|-------|
| `primaryGreen` | `#2E7D32` | AppBar, buttons, primary actions |
| `lightGreen` | `#4CAF50` | Accents |
| `earthBrown` | `#6D4C41` | Secondary text |
| `creamBackground` | `#F9F6F0` | Scaffold background |

Material 3 with `ColorScheme.fromSeed`. Text theme: Inter for most text, Noto Sans Devanagari for `bodyLarge`/`bodyMedium` to ensure proper Hindi rendering.

---

## Navigation Structure

```
AlhaApp
├── _OfflineGuard (browser online/offline listener)
│   └── _StartupRouter (JWT check)
│       ├── LoginScreen → ChatScreen (on success)
│       └── ChatScreen (if already authenticated)
│           ├── ProfileScreen (pushed, side nav)
│           ├── HistoryScreen (pushed, side nav)
│           │   └── _ConsultationDetail (pushed on list tap)
│           └── [Modal Bottom Sheets]
│               ├── SymptomInterviewOverlay (non-dismissible)
│               └── CameraOverlay (non-dismissible)
```
