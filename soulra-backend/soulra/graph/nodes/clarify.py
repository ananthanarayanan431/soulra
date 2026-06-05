# app/graph/nodes/clarify.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from soulra.graph.state import SoulraState

CLARIFY_PROMPT = """You are Soulra, a wisdom companion. Before drawing on ancient traditions,
you pause to understand the user's situation more deeply.

User situation: {situation}

Generate:
1. A single, thoughtful clarifying question (max 25 words, italic-style, contemplative tone)
2. Exactly 4 chip options the user can tap to answer

The question should help you understand whether this is about:
- External circumstances (work, people, situations)
- Internal patterns (fear, approval-seeking, identity)
- Relationships
- All of the above"""


class ClarifyOutput(BaseModel):
    question: str
    chips: list[str]


def create_clarify_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(ClarifyOutput)

    async def clarify(state: SoulraState) -> dict:
        prompt = CLARIFY_PROMPT.format(situation=state["situation"])
        result: ClarifyOutput = await structured_llm.ainvoke(prompt)
        fallbacks = [f"Clarify option {i + 1}" for i in range(4)]
        chips = result.chips[:4]
        chips = chips + fallbacks[len(chips):]
        return {
            "clarify_question": result.question,
            "clarify_chips": chips,
        }

    return clarify
