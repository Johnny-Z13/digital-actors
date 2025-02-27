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
    def __init__(self, provider="elevenlabs", voice_id=None, model_id=None, lang_code='a', optimize_streaming_latency=3):
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
        is identical to Eleven Labs (streaming MP3 as a string)
        """
        generator = self.pipeline(text, voice=voice, speed=1, split_pattern=r'\n+')

        # Process audio chunks
        for _, (_, _, audio) in enumerate(generator):
            # Convert audio to MP3 and yield
            yield self._process_audio_chunk(audio, is_final=False)
        
        # Send final silent chunk
        yield self._process_audio_chunk(None, is_final=True)

    def _process_audio_chunk(self, audio, is_final=False):
        """Helper method to process audio chunks and convert to MP3."""
        if is_final:
            # Create silent audio for final chunk
            audio_segment = AudioSegment.silent(duration=100, frame_rate=44100)
        else:
            # Convert tensor or numpy array to AudioSegment
            if isinstance(audio, torch.Tensor):
                audio = audio.detach().cpu().numpy()
                audio = (audio * 32767).astype("int16")
            
            # Create AudioSegment from raw PCM
            audio_segment = AudioSegment(
                data=audio.tobytes(),
                sample_width=2,
                frame_rate=24000,
                channels=1
            ).set_frame_rate(44100)
        
        # Export to MP3 and encode as base64
        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3")
        mp3_string = base64.b64encode(mp3_buffer.getvalue()).decode("utf-8")
        
        # Return formatted JSON string
        return json.dumps({
            "audio": mp3_string,
            "isFinal": is_final,
            "normalizedAlignment": None,
            "alignment": None
        })

    async def _generate_elevenlabs(self, user_input):
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}&optimize_streaming_latency={self.optimize_streaming_latency}"

        async with websockets.connect(url) as websocket:
            # await websocket.send(user_input)
            await websocket.send(
                '{"text": " ", "voice_settings": {"stability": 0.8, "similarity_boost": 0.8}, "xi_api_key": "03fb4a0acae30e29a92545df22b62f87"}'
            )
            await websocket.send(json.dumps({"text": user_input}))
            await websocket.send('{"text": ""}')  # EOS
            t0 = time.time()
            async for resp in websocket:
                yield resp
                print(f"Elevenlabs latency: {time.time() - t0:.2f}s")
