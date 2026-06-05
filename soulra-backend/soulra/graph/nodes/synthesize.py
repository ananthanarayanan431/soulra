# app/graph/nodes/synthesize.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from soulra.graph.state import SoulraState

SYNTHESIZE_PROMPT = """You are Soulra, an AI wisdom companion.

User situation: {situation}
Clarification: {clarify_answer}

Retrieved passages:
{passages}

Generate a response with:
1. tradition_cards: 2-3 cards, each with tradition, author, quote (exact passage), citation, analysis (2-3 sentences applying the wisdom to this situation)
2. action_steps: exactly 3 concrete steps the user can take today, each with n ("01"/"02"/"03"), title (short), body (1-2 sentences)

Ground every card in the retrieved passages. Do not invent quotes."""


class TraditionCard(BaseModel):
    tradition: str
    author: str
    quote: str
    citation: str
    analysis: str


class ActionStep(BaseModel):
    n: str
    title: str
    body: str


class SynthesizeOutput(BaseModel):
    tradition_cards: list[TraditionCard]
    action_steps: list[ActionStep]


def create_synthesize_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(SynthesizeOutput)

    async def synthesize(state: SoulraState) -> dict:
        refined = state["refined_docs"]
        docs = refined if refined is not None else state["retrieved_docs"]
        passages = "\n\n".join(
            f"[{d.metadata.get('tradition', 'unknown')} — {d.metadata.get('citation', '')}]\n{d.page_content[:500]}"
            for d in docs[:8]
        )
        prompt = SYNTHESIZE_PROMPT.format(
            situation=state["situation"],
            clarify_answer=state.get("clarify_answer") or "not provided",
            passages=passages,
        )
        result: SynthesizeOutput = await structured_llm.ainvoke(prompt)
        return {
            "tradition_cards": [c.model_dump() for c in result.tradition_cards],
            "action_steps": [s.model_dump() for s in result.action_steps],
        }

    return synthesize
