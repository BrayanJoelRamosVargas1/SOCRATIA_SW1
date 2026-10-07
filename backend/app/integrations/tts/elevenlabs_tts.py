import base64
import json
import logging
import time
from collections.abc import AsyncIterator

import websockets
from websockets.exceptions import WebSocketException

from app.integrations.tts.base import TTSProvider, TTSProviderError, TTSRequest

logger = logging.getLogger(__name__)

ELEVENLABS_WS_URL = (
    "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_flash_v2_5"
)


class ElevenLabsTTSProvider(TTSProvider):
    name = "elevenlabs"

    def __init__(
        self,
        *,
        api_key: str | None,
        default_voice_id: str | None,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.default_voice_id = default_voice_id
        self.timeout_seconds = timeout_seconds

    async def synthesize(self, request: TTSRequest) -> AsyncIterator[bytes]:
        if not self.api_key:
            raise TTSProviderError("ElevenLabs TTS is not configured", provider=self.name)

        voice_id = request.voice_id or self.default_voice_id
        if not voice_id:
            raise TTSProviderError("ElevenLabs voice ID is not configured", provider=self.name)

        url = ELEVENLABS_WS_URL.format(voice_id=voice_id)

        try:
            # We use a context manager for the websocket connection
            async with websockets.connect(url, ping_interval=None) as ws:
                # 1. Send initialization with API key and settings
                init_msg = {
                    "text": " ",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                    "xi_api_key": self.api_key,
                }
                await ws.send(json.dumps(init_msg))

                # 2. Send the full text
                text_msg = {
                    "text": request.text,
                    "try_trigger_generation": True,
                }
                await ws.send(json.dumps(text_msg))

                # 3. Close the input stream
                eos_msg = {"text": ""}
                await ws.send(json.dumps(eos_msg))

                first_chunk = True
                start_time = time.monotonic()

                # 4. Receive audio chunks
                while True:
                    try:
                        response = await ws.recv()
                        data = json.loads(response)

                        if data.get("error"):
                            logger.error("ElevenLabs WS returned error: %s", data["error"])
                            raise TTSProviderError(
                                f"ElevenLabs error: {data['error']}", provider=self.name
                            )

                        if data.get("audio"):
                            if first_chunk:
                                ttfa = int((time.monotonic() - start_time) * 1000)
                                logger.info("TTS_TTFA provider=%s ms=%d", self.name, ttfa)
                                first_chunk = False

                            chunk = base64.b64decode(data["audio"])
                            if chunk:
                                yield chunk

                        if data.get("isFinal"):
                            break
                    except websockets.exceptions.ConnectionClosed:
                        break

        except WebSocketException as exc:
            raise TTSProviderError(
                f"ElevenLabs WebSocket error: {str(exc)}", provider=self.name
            ) from exc
        except Exception as exc:
            raise TTSProviderError(
                f"ElevenLabs unexpected error: {str(exc)}", provider=self.name
            ) from exc
