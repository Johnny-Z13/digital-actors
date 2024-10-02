import websockets
import asyncio
import secrets
from rich.console import Console
from protocol import Protocol

from cachedvoiceclient import CachedVoiceClient

console = Console(force_terminal=True)

async def send_response(websocket, resp):
    # Echo message back to user
    print("-> SUBTITLE", resp)
    await websocket.send(Protocol.SUBTITLE + resp)

    # Get voice line
    async for mp3_bytes in voice_client.get_voice_line(resp):
        print("-> AUDIO_MP3", len(mp3_bytes))
        await websocket.send(Protocol.AUDIO_MP3 + mp3_bytes)

async def send_state_update(websocket, type, state, value):
    print("-> STATE_UPDATE", type, state, value)
    await websocket.send(Protocol.STATE_UPDATE + type + Protocol.SEP + state + Protocol.SEP + value)

async def send_event(websocket, event_name):
    print("-> EVENT_TRIGGER", event_name)
    await websocket.send(Protocol.EVENT_TRIGGER + event_name)

##### Define behaviour here ######

state = 0

async def on_user_transcript(websocket, message):
    if state == 0:
        resp = "Hello from server! You said" + message + ". I'm going to trigger the emergency override now."

        await send_response(websocket, resp)
        await send_state_update(websocket, "string", "demo_script_state", "1.4")
        # await send_state_update(websocket, "string", "demo_flow_message", "Pod_KatoEmergencyOverridePrompt")
        state = 1
    elif state == 1:
        resp = "You should see a passphrase now."
        await send_response(websocket, resp)
        await send_state_update(websocket, "string", "demo_script_state", "1.6")
        state = 2
    elif state == 2:
        await send_event(websocket, "emergency_override_passphrase_correct")
        state = 3

async def on_event_triggered(websocket, event_name): 
    """
    Events triggered inside the game get proxied through here.
    Optionally, you can filter events here (and replace them with your own logic).
    """   
    await send_event(websocket, event_name)

###################################

async def client_handler(websocket, path):
    console.print("client connected")
    # Client connect
    pong_waiter = await websocket.ping()
    latency = await pong_waiter
    client_id = secrets.token_hex(8)
    console.print(f"New client connected {client_id} @ {websocket.remote_address[0]} - Latency: {latency*1000:.1f}ms")

    try:
        # On each incoming message from the game
        async for message in websocket:
            match message[:1]:
                case Protocol.USER_TRANSCRIPT:
                    print("<- USER_TRANSCRIPT", message[1:])
                    await on_user_transcript(websocket, message[1:])

                case Protocol.EVENT_TRIGGERED:
                    print("<- EVENT_TRIGGERED", message[1:])
                    await on_event_triggered(websocket, message[1:])

                case _:
                    print("Unknown message")
                    print(message)

    except websockets.ConnectionClosed:
        console.print(f"Client {client_id} disconnected")
    finally:
        pass
        # Client cleanup
        # stop_polling.set()


voice_client = CachedVoiceClient(None, "ChcIf9hNw4gUMX5XTD4A", "eleven_turbo_v2", 3)

print("Server ready!")
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)

start_server = websockets.serve(client_handler, "0.0.0.0", 8550)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()