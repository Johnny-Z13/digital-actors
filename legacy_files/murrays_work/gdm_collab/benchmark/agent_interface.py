from typing import Callable

import pydantic


class VirtualActorResponse(pydantic.BaseModel):
    role: str = pydantic.Field(description="The name of the character speaking the line")
    text: str = pydantic.Field(description="The text the character should say, with any annotations necessary")
    is_last: bool  = pydantic.Field(description="Should this be the last line of the dialogue?")


VirtualActor = Callable[[str], VirtualActorResponse]

