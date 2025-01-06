from ant_server_base import AntServerBase
import re
import asyncio
import time
from project_one_demo.generate_project1_dialogue import reset_reponse_handler, handle_player_reponse, start_scene, Line

class AntServer(AntServerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = 0
        reset_reponse_handler()
 
 
    async def sample_transcript_handler(self, message):

        """
        Triggered when the user says something with the transcript provided.
        You can do a few things here:
        - await self.send_response(str): Reply with the given voice line.
        - await self.send_state_update(type, state, value): Update the game state.
        - await self.send_event(event_name): Trigger an event in-game (seen in forge). Note that the preconditions need to match for this to succeed.
        - await asyncio.sleep(secs): Wait for the given number of seconds.
        """
        # Handle luna messages (http://forge.internal.iconicgames.ai/editor/11/). This won't match everything.
        if re.match(r'^\s*(computer|luna)\s+(sc\w*|sk\w*)\s*(room|vicinity|area|pod|cryopod|hsp|door|wall|server)?\s*$', message, re.IGNORECASE):
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


    async def process_results(self, lines, state_changes):
        for line in lines or []:
            if line.delay > 0.0:
                time.sleep(line.delay)
            if line.text:
                await self.send_response(line.text)

        for change in state_changes or []:
            if change.name and change.value:
                type = "int" if change.name == "demo_flow_state" else "string"
                await self.send_state_update(type, change.name, change.value)


    async def on_user_transcript(self, message):

        # Handle luna messages (http://forge.internal.iconicgames.ai/editor/11/). This won't match everything.
        if re.match(r'^\s*(computer|luna|lunar)\b.*$', message, re.IGNORECASE):
            if re.match(r'^\s*(computer|luna|lunar)\s+(sc\w*|sk\w*).*$', message, re.IGNORECASE):
                await self.send_event("eyeOS_VC_ScanRoom")
                return
            if re.match(r'^\s*(computer|luna|lunar).*(gravity|zero\s*g).*(on)\s*$', message, re.IGNORECASE):
                await self.send_event("eyeOS_VC_GravityOn")
                return
            if re.match(r'^\s*(computer|luna|lunar).*(gravity|zero\s*g).*(off)\s*$', message, re.IGNORECASE):
                await self.send_event("eyeOS_VC_GravityOff")
                return
            if re.match(r'^\s*(computer|luna|lunar)\s+gravity\b.*$', message, re.IGNORECASE):
                await self.send_event("eyeOS_VC_GravityToggle")
                return
            if re.match(r'^\s*(computer|luna|lunar).*(open).*(door)\s*$', message, re.IGNORECASE):
                await self.send_event("eyeOS_VC_OpenDoor")
                return
        else:
            result = handle_player_reponse(message, False)
            if result:
                await self.process_results(result[0], result[1])


    async def on_event_triggered(self, event_name): 
        """
        Events triggered inside the game get proxied through here.
        Optionally, you can filter events here (and replace them with your own logic).
        """   
        if event_name == "kato_chamber_outside_pod": # This gets sent twice by the game - start_scene ensures it only loads once.
            result = start_scene("locate_an_engineer")
            if result:
                await self.process_results(result[0], result[1])

        if event_name == "kato_chamber_fail_what_happened" or event_name == "player_chamber_no_way_out":
            result = start_scene("describe_the_failures")
            if result:
                await self.process_results(result[0], result[1])
                
        #if event_name == "kato_chamber_zero_g_comment":
        #    result = handle_player_reponse("what zero g is like", True)
        #    if result:
        #        await self.process_results(result[0], result[1])
                
        #if event_name == "kato_chamber_found_exit":
        #    result = handle_player_reponse("player is near the exit", True)
        #    if result:
        #        await self.process_results(result[0], result[1])
                
        # if event_name == "kato_chamber_door_code":
        #     result = handle_player_reponse("player tried to open door but access was denied", True)
        #     if result:
        #         await self.process_results(result[0], result[1])
        #
        if event_name == "kato_chamber_door_open":
            result = handle_player_reponse("the door has opened, tell the player to get going to the control room", True)
            if result:
                await self.process_results(result[0], result[1])

        await self.send_event(event_name)
