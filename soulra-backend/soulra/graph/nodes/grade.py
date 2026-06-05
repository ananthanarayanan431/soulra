# app/graph/nodes/grade.py
import asyncio
from math import ceil
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from soulra.core.logging import logger
from soulra.graph.state import SoulraState

GRADE_PROMPT = """Does this retrieved document contain wisdom relevant to the user's situation?

User situation: {situation}
Search query: {query}
Document: {content}

Answer with JSON: {{"score": "yes"}} if relevant, {{"score": "no"}} if not."""


class GradeOutput(BaseModel):
    score: str  # "yes" | "no"


GRADE_SAMPLE_SIZE = 4


def create_grade_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(GradeOutput)

    async def _safe_grade(prompt: str) -> GradeOutput:
        try:
            return await structured_llm.ainvoke(prompt)
        except Exception as exc:
            logger.error("grade_llm_failed", error=str(exc))
            return GradeOutput(score="no")

    async def grade(state: SoulraState) -> dict:
        docs = state["retrieved_docs"]
        if not docs:
            return {"grade_result": "not_relevant"}

        sample = docs[:GRADE_SAMPLE_SIZE]
        prompts = [
            GRADE_PROMPT.format(
                situation=state["situation"],
                query=state["query"],
                content=doc.page_content[:500],
            )
            for doc in sample
        ]
        results: list[GradeOutput] = await asyncio.gather(
            *[_safe_grade(p) for p in prompts]
        )
        relevant_count = sum(1 for r in results if r.score == "yes")
        sampled_count = len(sample)
        threshold = max(1, ceil(sampled_count / 2))
        grade_result = "relevant" if relevant_count >= threshold else "not_relevant"
        return {"grade_result": grade_result}

    return grade
