from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from soulra.graph.state import SoulraState

SYNTHESIZE_PROMPT = """You are Soulra, an AI wisdom companion.

User situation: {situation}
Clarification: {clarify_answer}

Retrieved passages:
{passages}

GROUNDING RULES:
- Answer ONLY from the passages provided above.
- Every quote field must be verbatim text copied from a passage — no paraphrasing.
- The source_passage field must be a verbatim excerpt (≤200 chars) from the passage that grounds the card.
- If a passage does not contain sufficient wisdom for a card, omit the card rather than inventing content.
- Do not draw on general knowledge. If the answer is not in the passages, say so.

Generate a response with:
1. tradition_cards: 2-3 cards, each with tradition, author, quote (exact verbatim passage), citation, analysis (2-3 sentences applying the wisdom to this situation), source_passage (verbatim excerpt ≤200 chars)
2. action_steps: exactly 3 concrete steps the user can take today, each with n ("01"/"02"/"03"), title (short), body (1-2 sentences)"""


class TraditionCard(BaseModel):
    tradition: str
    author: str
    quote: str
    citation: str
    analysis: str
    source_passage: str  # verbatim excerpt ≤200 chars grounding this card


class ActionStep(BaseModel):
    n: str
    title: str
    body: str


class SynthesizeOutput(BaseModel):
    tradition_cards: list[TraditionCard]
    action_steps: list[ActionStep]


def _format_passage(doc: Document) -> str:
    m = doc.metadata
    label = (
        f"[{m.get('tradition', '?')} | {m.get('author', '?')} | "
        f"{m.get('source', '?')} | era: {m.get('era', '?')} | "
        f"ingested: {m.get('ingested_at', '?')}]"
    )
    return f"{label}\n{doc.page_content[:500]}"


def create_synthesize_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(SynthesizeOutput)

    async def synthesize(state: SoulraState) -> dict:
        docs = state["reranked_docs"]
        if docs:
            passages = "\n\n".join(_format_passage(d) for d in docs)
        else:
            passages = "[No source passages available — do not invent quotes.]"

        prompt = SYNTHESIZE_PROMPT.format(
            situation=state["situation"],
            clarify_answer=state.get("clarify_answer") or "not provided",
            passages=passages,
        )
        result: SynthesizeOutput = await structured_llm.ainvoke(prompt)  # type: ignore[assignment]
        return {
            "tradition_cards": [c.model_dump() for c in result.tradition_cards],
            "action_steps": [s.model_dump() for s in result.action_steps],
        }

    return synthesize
