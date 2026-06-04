# app/graph/nodes/intake.py
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from app.graph.state import SoulraState

TRADITION_OPTIONS = ["stoic", "vedanta", "buddhist", "sufi", "taoist",
                     "jewish", "christian_mystic", "zen"]

INTAKE_PROMPT = """You are helping route a user's situation to the right wisdom traditions.
Given this situation: {situation}

Extract:
1. tradition_hints: list of 2-3 most relevant traditions from {options}
2. query: a clear, concise search query (max 15 words) capturing the core problem

Respond with a JSON object with keys "tradition_hints" and "query"."""


class IntakeOutput(BaseModel):
    tradition_hints: list[str]
    query: str


def create_intake_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(IntakeOutput)

    def intake(state: SoulraState) -> dict:
        prompt = INTAKE_PROMPT.format(
            situation=state["situation"],
            options=TRADITION_OPTIONS,
        )
        result: IntakeOutput = structured_llm.invoke(prompt)
        return {
            "tradition_hints": result.tradition_hints,
            "query": result.query,
            "rewrite_count": 0,
        }

    return intake
