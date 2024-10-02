import websockets
import asyncio
import secrets
from rich.console import Console
from protocol import Protocol
import abc
import re

from cachedvoiceclient import CachedVoiceClient

console = Console(force_terminal=True)

class AntServerBase:
    __metaclass__ = abc.ABCMeta
    def __init__(self, websocket):
        self.websocket = websocket

    async def send_response(self, resp):
        # Echo message back to user
        print("-> SUBTITLE", resp)
        await self.websocket.send(Protocol.SUBTITLE + resp)

        # Get voice line
        async for mp3_bytes in voice_client.get_voice_line(resp):
            print("-> AUDIO_MP3", len(mp3_bytes))
            await self.websocket.send(Protocol.AUDIO_MP3 + mp3_bytes)

    async def send_state_update(self, type, state, value):
        print("-> STATE_UPDATE", type, state, value)
        await self.websocket.send(Protocol.STATE_UPDATE + type + Protocol.SEP + state + Protocol.SEP + value)

    async def send_event(self, event_name):
        print("-> EVENT_TRIGGER", event_name)
        await self.websocket.send(Protocol.EVENT_TRIGGER + event_name)

    @abc.abstractmethod
    async def on_user_transcript(self, message):
        pass

    @abc.abstractmethod
    async def on_event_triggered(self, event_name):
        pass

##### Define behaviour here ######

class AntServer(AntServerBase):
    def __init__(self, websocket):
        super().__init__(websocket)
        self.state = 0

    async def on_user_transcript(self, message):
        # Handle luna messages (http://forge.internal.iconicgames.ai/editor/11/). This won't match everything.
        if re.match(r'^\s*(computer|luna)\s+(scan|scam|skin|scot)\s*(room|vicinity|area|pod|cryopod|hsp|door|wall|server)?\s*$', message, re.IGNORECASE):
            await self.send_event("eyeOS_VC_ScanRoom")
            return
        if re.match(r'^\s*(computer|luna).*(gravity|zero\s*g).*\s*$', message, re.IGNORECASE):
            await self.send_event("eyeOS_VC_ToggleGravity")
            return
        
        # Otherwise, we simply progress the script. You'll want an LLM to do this instead and converse with the user inbetween.
        match self.state:
            case 0:
                # Start the emergency override sequence
                resp = "Hello from server! You said" + message + ". I'm going to trigger the emergency override now."

                await self.send_response(resp)

                await asyncio.sleep(5)
                await self.send_state_update("string", "demo_script_state", "1.4") # Note that this triggers a forced voice line.

                self.state = 1

            case 1:
                # Show the passphrase
                resp = "You should see a passphrase now."
                await self.send_response(resp)
                await self.send_state_update("string", "demo_script_state", "1.6") # No voice line here.
                self.state = 2

            case 2:
                # Open the pod
                await self.send_event("emergency_override_passphrase_correct") # Forced voice line.
                self.state = 4

            # case 3:
            #     # Activate eyeOS (with voice line). You could avoid the forced voice line by setting the states from kato_chamber_outside_pod manually.
            #     await self.send_state_update("string", "demo_script_state", "2.1.1")
            #     await self.send_event("kato_chamber_outside_pod")
            #     self.state = 4

            case 4:
                # Fail the other pod
                await self.send_response("I'm going to fail the other pod now.")
                await self.send_state_update("string", "demo_script_state", "2.5")
                await self.send_state_update("string", "demo_flow_message", "Chamber_OtherPodFail")
                self.state = 5

            case 5:
                # Fail everything
                await self.send_response("I'm going to fail everything now.")
                await self.send_state_update("string", "demo_script_state", "2.8")
                await self.send_state_update("string", "demo_flow_message", "Chamber_EverythingFail")

    async def on_event_triggered(self, event_name): 
        """
        Events triggered inside the game get proxied through here.
        Optionally, you can filter events here (and replace them with your own logic).
        """   
        await self.send_event(event_name)

###################################

async def client_handler(websocket, path):
    console.print("client connected")
    # Client connect
    pong_waiter = await websocket.ping()
    latency = await pong_waiter
    client_id = secrets.token_hex(8)
    console.print(f"New client connected {client_id} @ {websocket.remote_address[0]} - Latency: {latency*1000:.1f}ms")

    server = AntServer(websocket)

    try:
        # On each incoming message from the game
        async for message in websocket:
            match message[:1]:
                case Protocol.USER_TRANSCRIPT:
                    print("<- USER_TRANSCRIPT", message[1:])
                    await server.on_user_transcript(message[1:])

                case Protocol.EVENT_TRIGGERED:
                    print("<- EVENT_TRIGGERED", message[1:])
                    await server.on_event_triggered(message[1:])

                case _:
                    print("Unknown message")
                    print(message)

    except websockets.ConnectionClosed:
        console.print(f"Client {client_id} disconnected")
    finally:
        pass
        # Put any client cleanup here

voice_client = CachedVoiceClient(None, "ChcIf9hNw4gUMX5XTD4A", "eleven_turbo_v2", 3)

print("Server ready!")
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)

start_server = websockets.serve(client_handler, "0.0.0.0", 8550)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()