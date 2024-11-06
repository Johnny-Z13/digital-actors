import websockets
import asyncio
import secrets
from rich.console import Console
from protocol import Protocol
import abc
import re
from project_one_demo.generate_project1_dialogue import SceneData, Query, Line, load_scene_data

from cachedvoiceclient import CachedVoiceClient

console = Console(force_terminal=True)

from ant_server import AntServer

voice_client = CachedVoiceClient(None, "ChcIf9hNw4gUMX5XTD4A", "eleven_turbo_v2", 3)

async def client_handler(websocket, path):
    # Client connect
    pong_waiter = await websocket.ping()
    latency = await pong_waiter
    client_id = secrets.token_hex(8)
    console.print(f"New client connected {client_id} @ {websocket.remote_address[0]} - Latency: {latency*1000:.1f}ms")

    server = AntServer(websocket, console, voice_client)

    try:
        # On each incoming message from the game
        async for message in websocket:
            match message[:1]:
                case Protocol.USER_TRANSCRIPT:
                    console.print("[red]<-[/red] [bold]USER_TRANSCRIPT[/bold]", message[1:])
                    await server.on_user_transcript(message[1:])

                case Protocol.EVENT_TRIGGERED:
                    console.print("[red]<-[/red] [bold]EVENT_TRIGGERED[/bold]", message[1:])
                    await server.on_event_triggered(message[1:])

                case _:
                    print("Unknown message")
                    print(message)

    except websockets.ConnectionClosed:
        console.print(f"Client {client_id} disconnected")
    finally:
        pass
        # Put any client cleanup here


scene_data = load_scene_data("meet_the_caretaker")
print(scene_data)

print("Server ready!")
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)

start_server = websockets.serve(client_handler, "0.0.0.0", 8550)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()