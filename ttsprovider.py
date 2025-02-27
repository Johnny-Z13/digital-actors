import os
import asyncio
import json
import hashlib
import pickle
import time
import websockets
import torch
from pydub import AudioSegment
import io
import base64


class TTSProvider:
    def __init__(self, provider="kokoro", voice_id=None, model_id=None, lang_code='a', optimize_streaming_latency=False):
        """
        Initializes the TTS provider.
        Supported providers: "kokoro", "elevenlabs"
        """
        self.provider = provider
        self.voice_id = voice_id
        self.model_id = model_id
        self.optimize_streaming_latency = optimize_streaming_latency
        self.lang_code = lang_code

        if provider == "kokoro":
            from kokoro import KPipeline
            self.pipeline = KPipeline(lang_code=lang_code)

    async def generate_tts(self, text, voice="af_heart"):
        """
        Generates speech using the selected TTS provider.
        """
        if self.provider == "kokoro":
            async for audio in self._generate_kokoro(text, voice):
                yield audio
        elif self.provider == "elevenlabs":
            async for audio in self._generate_elevenlabs(text):
                yield audio
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")


    async def _generate_kokoro(self, text, voice):
        """
        Generates speech using Kokoro TTS and ensures the output format
        is identical to Eleven Labs (streaming MP3 as a string).
        """
        generator = self.pipeline(text, voice=voice, speed=1, split_pattern=r'\n+')

        for i, (gs, ps, audio) in enumerate(generator):
            print(f"\nKokoro generated part {i}")
            print(f"Type of audio: {type(audio)}")

            if isinstance(audio, torch.Tensor):
                print(f"Converting Tensor (shape={audio.shape}, dtype={audio.dtype}) to bytes...")

                audio = audio.detach().cpu().numpy()  # Convert Tensor to NumPy array
                audio = (audio * 32767).astype("int16")  # Scale float32 → int16 PCM

            byte_audio = audio.tobytes()  # Convert NumPy array to raw PCM bytes

            print(f"Yielding {len(byte_audio)} bytes of audio data")

            # Convert PCM to MP3 using pydub
            pcm_audio = AudioSegment(
                data=byte_audio,
                sample_width=2,  
                frame_rate=24000,  
                channels=1  
            )

            mp3_buffer = io.BytesIO()
            pcm_audio.export(mp3_buffer, format="mp3", bitrate="64k")
            mp3_bytes = mp3_buffer.getvalue()

            # Convert MP3 bytes to a string (Base64 encoding, like Eleven Labs)
            mp3_string = base64.b64encode(mp3_bytes).decode("utf-8")

            yield mp3_string  # Now returns a string, matching Eleven Labs

    async def _generate_elevenlabs(self, text):
        """
        Generates speech using Eleven Labs WebSockets API.
        """
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}&optimize_streaming_latency={self.optimize_streaming_latency}"

        async with websockets.connect(url) as websocket:
            await websocket.send(
                '{"text": " ", "voice_settings": {"stability": 0.8, "similarity_boost": 0.8}, "xi_api_key": "03fb4a0acae30e29a92545df22b62f87"}'
            )
            await websocket.send(json.dumps({"text": text}))
            await websocket.send('{"text": ""}')  # EOS

            t0 = time.time()
            async for resp in websocket:
                yield resp
                print(f"Elevenlabs latency: {time.time() - t0:.2f}s")
