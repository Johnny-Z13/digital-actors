import pickle
import hashlib
import os
import time
import asyncio
import websockets
from rich.console import Console

class CachedVoiceClient:
    def __init__(self, _, voice_id, model_id, optimize_streaming_latency):
        self.voice_id = voice_id
        self.model_id = model_id
        self.optimize_streaming_latency = optimize_streaming_latency

    #     self.graph = graph

    # async def update_cache(self):
    #     # This needs to be separate because it's async >:(
    #     for entry in self.graph.entries + self.graph.triggered_entries:
    #         if not self.is_cached(entry.response):
    #             async for resp in self.get_voice_line(entry.response):
    #                 pass

    def is_cached(self, tts_text):
        entry_details = (self.voice_id, self.model_id, self.optimize_streaming_latency, tts_text)
        entry_hash = hashlib.md5(str(entry_details).encode(), usedforsecurity=False).hexdigest()
        return os.path.exists(f"./voicecache/{entry_hash}.pkl")

    async def get_voice_line(self, tts_text):
        entry_details = (self.voice_id, self.model_id, self.optimize_streaming_latency, tts_text)
        entry_hash = hashlib.md5(str(entry_details).encode(), usedforsecurity=False).hexdigest()

        os.makedirs("./voicecache", exist_ok=True)

        if os.path.exists(f"./voicecache/{entry_hash}.pkl"):
            with open(f"./voicecache/{entry_hash}.pkl", "rb") as f:
                responses = pickle.load(f)

            print("Loaded TTS from cache")
            for resp in responses:
                yield resp

        else:
            responses = []  # for caching
            print("Fetching TTS from elevenlabs...")
            async for resp in self.get_elevenlabs_websocket_resps(tts_text):
                yield resp
                responses.append(resp)

            with open(f"./voicecache/{entry_hash}.pkl", "wb") as f:
                pickle.dump(responses, f, protocol=5)

    async def get_elevenlabs_websocket_resps(self, user_input):
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}&optimize_streaming_latency={self.optimize_streaming_latency}"

        async with websockets.connect(url) as websocket:
            # await websocket.send(user_input)
            await websocket.send(
                '{"text": " ", "voice_settings": {"stability": 0.8, "similarity_boost": 0.8}, "xi_api_key": "03fb4a0acae30e29a92545df22b62f87"}'
            )
            await websocket.send(f'{{"text": "{user_input}"}}')
            await websocket.send('{"text": ""}')  # EOS
            t0 = time.time()
            async for resp in websocket:
                yield resp
                print(f"Elevenlabs latency: {time.time() - t0:.2f}s")
