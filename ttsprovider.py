import os
import asyncio
import json
import time
import base64
import io
import numpy as np
import torch
import websockets
from pydub import AudioSegment
from pydub.playback import play

class TTSProvider:
    def __init__(self, provider="elevenlabs", voice_id=None, model_id=None, lang_code='a', optimize_streaming_latency=3):
        """
        Initializes the TTS provider and preloads the Kokoro model.
        """
        self.provider = provider
        self.voice_id = voice_id
        self.model_id = model_id
        self.optimize_streaming_latency = optimize_streaming_latency
        self.lang_code = lang_code

        # Configure streaming parameters for Kokoro
        self.frame_size = 24000  # 1000ms at 24kHz
        self.buffer_frames = 20  # Buffer 20 frames before sending for smoother playback

        # Preload Kokoro model to avoid delays in first request
        if provider == "kokoro":
            try:
                from kokoro import KPipeline
            except ImportError:
                raise ImportError("Kokoro module is not installed or failed to import.")
            print("Loading Kokoro model...")
            self.pipeline = KPipeline(lang_code=lang_code)
            print("Kokoro model loaded and ready.")
            try:
                import imageio_ffmpeg
            except ImportError:
                raise ImportError("imageio_ffmpeg module is not installed or failed to import.")
            # Get the ffmpeg binary path
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            # Set pydub to use this ffmpeg
            AudioSegment.converter = ffmpeg_path

            # Ensure it works
            if not ffmpeg_path:
                raise FileNotFoundError("FFmpeg could not be found or installed.")

            print("Using ffmpeg:", ffmpeg_path)

    async def generate_tts(self, text, voice="af_heart"):
        """Generates speech using the selected TTS provider."""
        if self.provider == "kokoro":
            async for audio in self._generate_kokoro(text, voice):
                yield audio
        elif self.provider == "elevenlabs":
            async for audio in self._generate_elevenlabs(text):
                yield audio
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

    async def _generate_kokoro(self, text, voice):
        start_time = time.time()  # Start timer
        first_chunk_played = False  # Track first chunk playback

        """Generates speech using Kokoro TTS with streaming optimization."""
        generator = self.pipeline(text, voice=voice, speed=1, split_pattern=r'\n+') #split_pattern=r'(?<=[.!?])|\n+'

        buffer = []
        print("Starting to process generator...")
        for chunk_idx, (gs, ps, audio) in enumerate(generator):
            print(f"Received chunk {chunk_idx} after {time.time() - start_time:.2f}s")

            if isinstance(audio, torch.Tensor):
                audio = audio.detach().cpu().numpy()
            
            for i in range(0, len(audio), self.frame_size):
                frame = audio[i:i + self.frame_size]
                
                if len(frame) > 0:
                    buffer.append(frame)

                    if len(buffer) >= self.buffer_frames or i + self.frame_size >= len(audio):
                        buffered_audio = np.concatenate(buffer)
                        
                        if not first_chunk_played:
                            first_speech_time = time.time() - start_time
                            print(f"🕒 Time to first speech: {first_speech_time:.2f} seconds")
                            first_chunk_played = True  # Mark first chunk as played

                        yield self._process_audio_chunk(buffered_audio, is_final=False)
                        
                        buffer = [buffer[-1]] if i + self.frame_size < len(audio) else []
                
                await asyncio.sleep(0.01)

        yield self._process_audio_chunk(None, is_final=True)

    def _process_audio_chunk(self, audio, is_final=False):
        """Helper method to process audio chunks and convert to MP3."""
        if is_final:
            audio_segment = AudioSegment.silent(duration=100, frame_rate=44100)
        else:
            audio = (audio * 32767).astype("int16")
            audio_segment = AudioSegment(
                data=audio.tobytes(),
                sample_width=2,
                frame_rate=24000,
                channels=1
            ).set_frame_rate(44100)

        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3")
        mp3_string = base64.b64encode(mp3_buffer.getvalue()).decode("utf-8")

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
