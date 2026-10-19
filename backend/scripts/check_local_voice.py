import asyncio
import time
from app.integrations.tts.dependencies import get_tts_provider
from app.integrations.tts.base import TTSRequest


async def main():
    provider = get_tts_provider()
    for run in range(2):
        started = time.monotonic()
        audio = b"".join([chunk async for chunk in provider.synthesize(TTSRequest(text="Explique cómo validó los resultados de su investigación.", speaker_index=0))])
        assert audio[:4] == b"RIFF"
        print({"provider":provider.name,"mime":provider.mime_type,"bytes":len(audio),"seconds":round(time.monotonic()-started,3),"cached":bool(run)})


if __name__ == '__main__':
    asyncio.run(main())
