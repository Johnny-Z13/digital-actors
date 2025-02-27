import pickle
import hashlib
import os
import time
import asyncio
import websockets
import json
from rich.console import Console
from ttsprovider import TTSProvider  

class CachedVoiceClient:
    def __init__(self, voice_id, model_id, optimize_streaming_latency, tts_provider="elevenlabs"):
        self.voice_id = voice_id
        self.model_id = model_id
        self.optimize_streaming_latency = optimize_streaming_latency
        self.tts_provider = TTSProvider(provider=tts_provider, voice_id=voice_id, model_id=model_id, optimize_streaming_latency=optimize_streaming_latency)

    def is_cached(self, tts_text):
        entry_hash = self._generate_hash(tts_text)
        return os.path.exists(f"./voicecache/{entry_hash}.pkl")

    async def get_voice_line(self, tts_text):
        entry_hash = self._generate_hash(tts_text)

        if self.is_cached(tts_text):
            async for resp in self._load_from_cache(entry_hash):
                yield resp
        else:
            responses = []
            print(f"Fetching TTS from {self.tts_provider.provider}...")

            async for resp in self.tts_provider.generate_tts(tts_text):
                yield resp
                responses.append(resp)

            self._save_to_cache(entry_hash, responses)

    def _generate_hash(self, text):
        return hashlib.md5(str((self.voice_id, self.model_id, self.optimize_streaming_latency, text)).encode(), usedforsecurity=False).hexdigest()

    async def _load_from_cache(self, entry_hash):
        try:
            with open(f"./voicecache/{entry_hash}.pkl", "rb") as f:
                responses = pickle.load(f)
            print("Loaded TTS from cache")
            for resp in responses:
                yield resp
        except Exception as e:
            print(f"Cache load error: {e}")

    def _save_to_cache(self, entry_hash, responses):
        try:
            with open(f"./voicecache/{entry_hash}.pkl", "wb") as f:
                pickle.dump(responses, f, protocol=5)
        except Exception as e:
            print(f"Cache save error: {e}")

async def main():
    import io
    import json
    import base64
    import subprocess
    from pydub import AudioSegment
    # Ensure CachedVoiceClient is initialized with the correct provider
    voice_client = CachedVoiceClient(None, None, None, tts_provider="kokoro")
    print("Model loaded")

    test_text = """ To be, or not to be, that is the question: whether 'tis nobler in the mind to suffer the slings and arrows of outrageous fortune, or to take arms against a sea of troubles and by opposing end them. """

    # Start ffplay in subprocess to stream audio
    ffplay_process = subprocess.Popen(
        ["ffplay", "-nodisp", "-autoexit", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    async for audio_chunk in voice_client.get_voice_line(test_text):
        # Parse JSON response to extract the audio
        audio_data = json.loads(audio_chunk)
        
        # Skip final empty chunk
        if audio_data.get("isFinal", False):
            break
        
        # Decode base64-encoded MP3 chunk
        mp3_bytes = base64.b64decode(audio_data["audio"])
        mp3_segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))

        # Export audio to ffmpeg (write directly to the subprocess without a temp file)
        mp3_segment.export(ffplay_process.stdin, format="wav")

    # Close the ffplay process
    ffplay_process.stdin.close()
    ffplay_process.wait()

    print("Streaming complete!")


if __name__ == "__main__":
    asyncio.run(main())

