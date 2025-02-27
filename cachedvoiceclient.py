import pickle
import hashlib
import os
import time
import asyncio
import websockets
import json
from rich.console import Console
from ttsprovider import TTSProvider  # Import TTSProvider

class CachedVoiceClient:
    def __init__(self, voice_id, model_id, optimize_streaming_latency, tts_provider="elevenlabs"):
        self.voice_id = voice_id
        self.model_id = model_id
        self.optimize_streaming_latency = optimize_streaming_latency
        self.tts_provider = TTSProvider(provider=tts_provider, voice_id=voice_id, model_id=model_id)

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
    import base64
    from pydub import AudioSegment
    from pydub.playback import play  # Use Pydub to play MP3

    voice_client = CachedVoiceClient(None, None, 3, tts_provider="kokoro")
    test_text = "Hi there friend, this is a test of the Kokoro TTS system."

    print("Generating speech with Kokoro...")
    audio_data = ""  # Store as a string instead of bytes

    async for audio_chunk in voice_client.get_voice_line(test_text):
        audio_data += audio_chunk  

    # Decode Base64 string back to MP3 bytes
    mp3_bytes = base64.b64decode(audio_data)
    mp3_buffer = io.BytesIO(mp3_bytes)

    # Load MP3 and play it
    mp3_audio = AudioSegment.from_mp3(mp3_buffer)

    print("Playing MP3 audio...")
    play(mp3_audio)  # Directly play the MP3


if __name__ == "__main__":
    asyncio.run(main())

