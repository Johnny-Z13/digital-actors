"""
Dialogue state representation and traversal logic (the dialogue player).
"""

from typing import Any, List

import pydantic


ChatHistory = list[str]
Fact = str
CommunicationStyleComponent = str
Goal = str


class DialogueState(pydantic.BaseModel):
    chat_history: ChatHistory = []  # Everything that has been "said" in the dialogue so far

    # Communication style is assumed to remain constant during the simulation
    # Character facts, i.e. things that only a particular character knows, is assumed constant as well

    def serialize(self) -> dict[str, Any]:
        return {
            "chat_history": self.chat_history,
        }

    @classmethod
    def deserialize(self, json_dict: dict[str, Any]) -> "DialogueState":
        return DialogueState(
            chat_history=json_dict.get("chat_history", []),
        )


class Dialogue(pydantic.BaseModel):
    """A dialogue graph representation.
    
    Nodes are functional, every node represents a specific operation.

    Nodes keep track of the outbound edges, and are grouped into "outbound pins".
    This grouping allows to define Node classes that activate a specific path through the graph.

    The edges structure is therefore a mapping from:
        Start node index -> List of outbound pins -> List of target node indices

    The outbound pins are defined at the Node class level, using the __pins__ attribute.
    """

    facts: List[Fact] = []
    comm_style: List[CommunicationStyleComponent] = []
    goals: List[Goal] = []

    def serialize(self) -> dict[str, Any]:
        return {
            "dialogue": {
                "facts": self.facts,
                "comm_style": self.comm_style,
                "goals": self.goals,
            }
        }
            

    @classmethod
    def deserialize(cls, json_dict: dict[str, Any]) -> "Dialogue":
        if "dialogue" not in json_dict:
            raise ValueError("Invalid serialized Dialogue object.")
        data = json_dict["dialogue"]


        return Dialogue(
            facts=data.get("facts", []),
            comm_style=data.get("comm_style", []),
            goals=data.get("goals", []),
        )
