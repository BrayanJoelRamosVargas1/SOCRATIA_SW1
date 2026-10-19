import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.stt.base import STTProviderError, STTRequest
from app.integrations.stt.gemini_stt import GeminiSTTProvider


def provider(result=None, timeout=1):
    instance = GeminiSTTProvider(api_key=None, model='gemini-3.5-transcribe', timeout_seconds=timeout, max_attempts=1)
    create = AsyncMock(return_value=result or SimpleNamespace(output_text='  Una respuesta.  '))
    instance.client = SimpleNamespace(aio=SimpleNamespace(interactions=SimpleNamespace(create=create)))
    return instance, create


@pytest.mark.asyncio
async def test_current_interactions_contract_and_no_stored_audio():
    instance, create = provider()
    result = await instance.transcribe(STTRequest(audio_bytes=b'fixture audio', mime_type='audio/wav;codec=pcm'))
    assert result.text == 'Una respuesta.'
    request = create.call_args.kwargs
    assert request['input'][0]['mime_type'] == 'audio/wav'
    assert base64.b64decode(request['input'][0]['data']) == b'fixture audio'
    assert request['generation_config']['transcription_config']['mode'] == {'type':'verbatim'}
    assert request['store'] is False
    assert request['timeout'] == 1


@pytest.mark.asyncio
async def test_installed_sdk_text_outputs_are_supported():
    instance, _ = provider(SimpleNamespace(outputs=[SimpleNamespace(type='text',text='Una '),SimpleNamespace(type='text',text='respuesta.')]))
    assert (await instance.transcribe(STTRequest(b'audio','audio/wav'))).text == 'Una respuesta.'


@pytest.mark.asyncio
async def test_request_deadline_and_empty_result():
    instance, create = provider(timeout=.01)
    async def slow(**kwargs):
        await asyncio.sleep(1)
    create.side_effect = slow
    with pytest.raises(STTProviderError) as error:
        await instance.transcribe(STTRequest(b'audio','audio/wav'))
    assert error.value.retryable
    instance, _ = provider(SimpleNamespace(output_text='   '))
    with pytest.raises(STTProviderError):
        await instance.transcribe(STTRequest(b'audio','audio/wav'))


@pytest.mark.asyncio
async def test_interactions_status_errors_are_retryable_without_exposing_body():
    class UnavailableError(Exception):
        status_code = 503
    instance, create = provider()
    create.side_effect = UnavailableError('private request details')
    with pytest.raises(STTProviderError) as error:
        await instance.transcribe(STTRequest(b'audio','audio/wav'))
    assert error.value.retryable
    assert 'private' not in str(error.value)
