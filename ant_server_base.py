from protocol import Protocol
import abc
import re

class AntServerBase:
    __metaclass__ = abc.ABCMeta
    def __init__(self, websocket, console, voice_client):
        self.websocket = websocket
        self.console = console
        self.voice_client = voice_client

    async def send_response(self, resp):
        # Echo message back to user
        self.console.print("[blue]->[/blue] [bold]SUBTITLE[/bold]", resp)
        await self.websocket.send(Protocol.SUBTITLE + resp)

        # Get voice line
        async for mp3_bytes in self.voice_client.get_voice_line(resp):
            self.console.print("[blue]->[/blue] [bold]AUDIO_MP3[/bold]", len(mp3_bytes))
            await self.websocket.send(Protocol.AUDIO_MP3 + mp3_bytes)

    async def send_state_update(self, type, state, value):
        self.console.print("[blue]->[/blue] [bold]STATE_UPDATE[/bold]", type, state, value)
        await self.websocket.send(Protocol.STATE_UPDATE + type + Protocol.SEP + state + Protocol.SEP + value)

    async def send_event(self, event_name):
        self.console.print("[blue]->[/blue] [bold]EVENT_TRIGGER[/bold]", event_name)
        await self.websocket.send(Protocol.EVENT_TRIGGER + event_name)

    @abc.abstractmethod
    async def on_user_transcript(self, message):
        pass

    @abc.abstractmethod
    async def on_event_triggered(self, event_name):
        pass
