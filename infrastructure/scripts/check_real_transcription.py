"""One bounded provider check using only the existing synthetic Spanish sample."""
import argparse
import asyncio
import json
from pathlib import Path
import re
import sys
import unicodedata
import wave

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo/'backend'))
parser = argparse.ArgumentParser()
parser.add_argument('--provider', choices=['groq','gemini'], default='groq')
parser.add_argument('--browser-audio', action='store_true', help='Use the pre-encoded synthetic WebM fixture')
args = parser.parse_args()
source = repo/'artifacts/jury-remote/expression-voice-backup/kokoro-alex.wav'
assert source.is_file(), 'Use the original generated example; do not record the user.'
with wave.open(str(source)) as audio:
    duration = audio.getnframes()/audio.getframerate()
assert duration < 15 and source.stat().st_size < 1_000_000
if args.browser_audio:
    source = repo/'artifacts/defense-validation/synthetic-browser-response.webm'
    assert source.is_file() and source.stat().st_size < 1_000_000

from app.core.config import get_settings
from app.integrations.stt.base import STTRequest
from app.integrations.stt.groq_stt import GroqSTTProvider
from app.integrations.stt.gemini_stt import GeminiSTTProvider

def words(text):
    return re.findall(r'[a-z]+', ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c)))

async def main():
    settings = get_settings()
    if args.provider == 'groq':
        provider = GroqSTTProvider(api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
            model=settings.groq_stt_model, timeout_seconds=25, max_attempts=1)
    else:
        provider = GeminiSTTProvider(api_key=settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None,
            model=settings.gemini_stt_model, timeout_seconds=25, max_attempts=1)
    output = repo/'artifacts/defense-validation'
    output.mkdir(parents=True,exist_ok=True)
    mime = 'audio/webm;codecs=opus' if args.browser_audio else 'audio/wav'
    report = {'provider':args.provider,'audio_seconds':round(duration,3),'input':'synthetic Spanish sample','mime_type':mime,'attempts':1}
    try:
        result = await asyncio.wait_for(provider.transcribe(STTRequest(audio_bytes=source.read_bytes(),mime_type=mime)),timeout=30)
        expected = set(words('Explique qué problema resuelve su investigación. Cómo validó los resultados y cuáles son las principales limitaciones de su propuesta'))
        coverage = len(expected.intersection(words(result.text)))/len(expected)
        report.update({'text':result.text,'latency_ms':result.latency_ms,'reference_word_coverage':round(coverage,3),'passed':coverage>=.85})
    except Exception as error:
        # Provider exceptions can include transport details. Preserve only type;
        # credentials, headers and request URLs never enter the report.
        report.update({'passed':False,'error_type':type(error).__name__,
            'cause_type':type(error.__cause__).__name__ if error.__cause__ else None,
            'http_status':getattr(error.__cause__,'code',None),
            'retryable':getattr(error,'retryable',False)})
    suffix = '-webm' if args.browser_audio else ''
    (output/f'real-stt-{args.provider}{suffix}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['passed'] else 1

sys.exit(asyncio.run(main()))
