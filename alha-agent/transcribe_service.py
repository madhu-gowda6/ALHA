import asyncio
import base64
from typing import Callable, Optional

import structlog
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

log = structlog.get_logger()

# Per-connection state: session_id → asyncio.Queue of base64-encoded PCM chunks.
# sentinel None means the stream is done.
_audio_queues: dict[str, asyncio.Queue] = {}


class _Handler(TranscriptResultStreamHandler):
    """Receives Transcribe results and forwards them to the WebSocket."""

    def __init__(
        self,
        output_stream,
        session_id: str,
        send_fn: Callable,  # async callable: send_fn(dict) → None
    ):
        super().__init__(output_stream)
        self._session_id = session_id
        self._send_fn = send_fn
        self._partial_text = ""

    async def handle_transcript_event(self, event: TranscriptEvent):
        results = event.transcript.results
        for result in results:
            if not result.alternatives:
                continue
            text = result.alternatives[0].transcript.strip()
            if not text:
                continue
            is_final = not result.is_partial
            # Only send if text changed or is final
            if is_final or text != self._partial_text:
                self._partial_text = text
                try:
                    await self._send_fn({
                        "type": "transcript",
                        "session_id": self._session_id,
                        "text": text,
                        "is_final": is_final,
                    })
                except Exception as exc:
                    log.warning(
                        "transcribe_send_failed",
                        session_id=self._session_id,
                        error=str(exc),
                    )


async def _audio_generator(session_id: str):
    """Yield PCM audio bytes from the queue until the sentinel None is received."""
    queue = _audio_queues.get(session_id)
    if queue is None:
        return
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield chunk


async def run_transcription(
    session_id: str,
    language_code: str,  # "hi-IN" or "en-US"
    region: str,
    send_fn: Callable,  # async fn(dict)
) -> None:
    """Open a Transcribe streaming session and pipe audio from the queue.

    This coroutine runs until the audio queue is exhausted (None sentinel
    received from voice_stop), then sends a final is_final=True transcript
    if one hasn't already been sent.
    """
    log.info(
        "transcribe_session_start",
        session_id=session_id,
        language_code=language_code,
    )
    try:
        client = TranscribeStreamingClient(region=region)
        stream = await client.start_stream_transcription(
            language_code=language_code,
            media_sample_rate_hz=16000,
            media_encoding="pcm",
        )

        handler = _Handler(stream.output_stream, session_id, send_fn)

        async def write_audio():
            async for pcm_bytes in _audio_generator(session_id):
                await stream.input_stream.send_audio_event(audio_chunk=pcm_bytes)
            await stream.input_stream.end_stream()

        await asyncio.gather(write_audio(), handler.handle_events())

        log.info("transcribe_session_done", session_id=session_id)

    except Exception as exc:
        log.error(
            "transcribe_session_error",
            session_id=session_id,
            error=str(exc),
        )
    finally:
        _audio_queues.pop(session_id, None)


def start_session(session_id: str) -> None:
    """Create an audio queue for a new voice session."""
    _audio_queues[session_id] = asyncio.Queue()


def push_audio(session_id: str, b64_chunk: str) -> None:
    """Decode a base64 PCM chunk and push it to the audio queue."""
    queue = _audio_queues.get(session_id)
    if queue is None:
        return
    try:
        pcm = base64.b64decode(b64_chunk)
        queue.put_nowait(pcm)
    except Exception as exc:
        log.warning("transcribe_push_audio_error", session_id=session_id, error=str(exc))


def stop_session(session_id: str) -> None:
    """Signal end-of-stream by pushing the sentinel None."""
    queue = _audio_queues.get(session_id)
    if queue is not None:
        queue.put_nowait(None)
