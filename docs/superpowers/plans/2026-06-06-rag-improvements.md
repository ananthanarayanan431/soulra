# RAG Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Cohere reranking (retrieve-20 → top-5), U-shape context ordering, near-dedup, richer context labels, stronger grounding prompt, `source_passage` citation field, selection-recall logging, `ingested_at` metadata, and `temperature=0` into the Soulra LangGraph pipeline.

**Architecture:** One new `rerank` node (Cohere API) is inserted after `retrieve` and after `retrieve_refined`. All other improvements are targeted edits to existing nodes. A single new state field `reranked_docs` threads the reranked results through the graph. The `synthesize` node reads exclusively from `reranked_docs`.

**Tech Stack:** Python 3.12, LangGraph, `cohere>=5.0` AsyncClient, structlog, pytest-asyncio.

---

## File Map

| File | Action |
|---|---|
| `pyproject.toml` | Add `cohere>=5.0` |
| `soulra/config.py` | Add `cohere_api_key: str` |
| `soulra/dependencies.py` | Add Cohere client singleton (`set_cohere_client`, `get_cohere_client`) |
| `soulra/main.py` | Init Cohere `AsyncClient` in lifespan; pass to `build_graph` |
| `soulra/graph/state.py` | Add `reranked_docs: list[Document]` field |
| `soulra/services/ingestion/chunker.py` | Stamp `ingested_at` ISO string on every chunk |
| `soulra/graph/nodes/rerank.py` | **Create** — Cohere rerank, near-dedup, U-shape |
| `soulra/graph/nodes/retrieve.py` | `k=4` → `k=10` |
| `soulra/graph/nodes/grade.py` | Read `reranked_docs`; emit `selection_recall` log |
| `soulra/graph/nodes/synthesize.py` | Richer labels, grounding prompt, `source_passage` on `TraditionCard`, read `reranked_docs` |
| `soulra/services/llm/factory.py` | Add `temperature=0` |
| `soulra/graph/builder.py` | Add `cohere_client` param; wire two rerank nodes |
| `tests/unit/test_chunker.py` | Assert `ingested_at` in chunk metadata |
| `tests/unit/test_node_rerank.py` | **Create** — unit tests for jaccard, dedup, U-shape, rerank node |
| `tests/unit/test_node_retrieve_grade.py` | Add `reranked_docs` to state helper; update grade tests |
| `tests/unit/test_node_synthesize.py` | Add `reranked_docs` to state; update label/source_passage assertions |
| `tests/unit/test_llm_factory.py` | Assert `temperature == 0` |
| `tests/unit/test_graph_builder.py` | Pass `mock_cohere` to `build_graph` |

---

## Task 1: Add Cohere dependency and config key

**Files:**
- Modify: `pyproject.toml`
- Modify: `soulra/config.py`

- [ ] **Step 1: Add `cohere>=5.0` to pyproject.toml**

In `pyproject.toml`, in the `dependencies` list, add after the `httpx` line:

```toml
    "cohere>=5.0",
```

- [ ] **Step 2: Add `cohere_api_key` to config**

In `soulra/config.py`, after the `redis_url` line, add:

```python
    cohere_api_key: str
```

This is a required field (no default) — the app fails at startup validation if missing.

- [ ] **Step 3: Install the dependency**

```bash
cd soulra-backend && pip install "cohere>=5.0"
```

Expected: resolves and installs without conflict.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml soulra/config.py
git commit -m "feat(rag): add cohere dependency and config key"
```

---

## Task 2: Cohere client singleton in dependencies.py

**Files:**
- Modify: `soulra/dependencies.py`

- [ ] **Step 1: Add the singleton**

Append to the bottom of `soulra/dependencies.py`:

```python
_cohere_client = None


def set_cohere_client(c) -> None:
    global _cohere_client
    _cohere_client = c


def get_cohere_client():
    if _cohere_client is None:
        raise RuntimeError(
            "Cohere client not initialised — call set_cohere_client() during app lifespan"
        )
    return _cohere_client
```

- [ ] **Step 2: Commit**

```bash
git add soulra/dependencies.py
git commit -m "feat(rag): add Cohere client singleton to dependencies"
```

---

## Task 3: Wire Cohere client in main.py lifespan

**Files:**
- Modify: `soulra/main.py`

- [ ] **Step 1: Import and initialise in lifespan**

At the top of `main.py`, the existing import block already has `from soulra.dependencies import set_vectorstore, set_retriever` (imported inside lifespan). Add Cohere init right after `job_cache.init_redis(settings.redis_url)`, before the Alembic block:

```python
    import cohere as cohere_sdk
    from soulra.dependencies import set_cohere_client
    set_cohere_client(cohere_sdk.AsyncClient(api_key=settings.cohere_api_key))
```

- [ ] **Step 2: Pass `cohere_client` to `build_graph`**

Inside the lifespan, find the `build_graph(...)` call and add the new argument:

```python
        from soulra.dependencies import (
            get_embeddings,
            get_fast_llm,
            get_smart_llm,
            get_cohere_client,          # add this import
        )
        # ...existing code...
        graph = build_graph(
            retriever=retriever,
            fast_llm=get_fast_llm(),
            smart_llm=get_smart_llm(),
            checkpointer=checkpointer,
            cohere_client=get_cohere_client(),   # add this argument
        )
```

- [ ] **Step 3: Commit**

```bash
git add soulra/main.py
git commit -m "feat(rag): init Cohere client in app lifespan"
```

---

## Task 4: Add `reranked_docs` to graph state

**Files:**
- Modify: `soulra/graph/state.py`

- [ ] **Step 1: Add the field to SoulraState**

In `soulra/graph/state.py`, add `reranked_docs` after `retrieved_docs`:

```python
class SoulraState(TypedDict):
    situation: str
    tradition_hints: list[str]
    query: str
    retrieved_docs: list[Document]
    reranked_docs: list[Document]      # top-5 after Cohere rerank + U-shape
    grade_result: str
    clarify_question: str
    clarify_chips: list[str]
    clarify_answer: str | None
    refined_docs: list[Document]
    tradition_cards: list[dict]
    action_steps: list[dict]
    messages: Annotated[list, add_messages]
    rewrite_count: int
```

- [ ] **Step 2: Initialise the field in `make_initial_state`**

```python
def make_initial_state(situation: str) -> SoulraState:
    return SoulraState(
        situation=situation,
        tradition_hints=[],
        query="",
        retrieved_docs=[],
        reranked_docs=[],              # add this line
        grade_result="",
        clarify_question="",
        clarify_chips=[],
        clarify_answer=None,
        refined_docs=[],
        tradition_cards=[],
        action_steps=[],
        messages=[],
        rewrite_count=0,
    )
```

- [ ] **Step 3: Update `_make_state` helpers in both test files**

In `tests/unit/test_node_retrieve_grade.py`, add `"reranked_docs": []` to the `base` dict:

```python
def _make_state(**overrides):
    base = {
        "situation": "I keep saying yes to projects.",
        "query": "refusing gracefully",
        "tradition_hints": ["stoic", "buddhist"],
        "retrieved_docs": [],
        "reranked_docs": [],           # add this line
        "grade_result": "",
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    base.update(overrides)
    return base
```

In `tests/unit/test_node_synthesize.py`, update `_make_state`:

```python
def _make_state(**overrides):
    docs = [
        Document(page_content="Stoic wisdom.", metadata={
            "tradition": "stoic", "author": "Marcus Aurelius",
            "citation": "Meditations 6.13", "source": "Meditations",
            "era": "170 AD", "ingested_at": "2026-06-06T00:00:00+00:00",
        }),
    ]
    base = {
        "situation": "I say yes too much.",
        "query": "refusing",
        "tradition_hints": ["stoic"],
        "retrieved_docs": docs,
        "reranked_docs": docs,         # add this line
        "grade_result": "relevant",
        "clarify_question": "Is this internal?",
        "clarify_chips": ["Yes", "No"],
        "clarify_answer": "Yes",
        "refined_docs": docs,
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    base.update(overrides)
    return base
```

Also update the inline state dict inside `test_grade_node_calls_ainvoke_concurrently` to include `"reranked_docs": docs`.

- [ ] **Step 4: Commit**

```bash
git add soulra/graph/state.py tests/unit/test_node_retrieve_grade.py tests/unit/test_node_synthesize.py
git commit -m "feat(rag): add reranked_docs field to SoulraState"
```

---

## Task 5: Stamp `ingested_at` on every chunk

**Files:**
- Modify: `soulra/services/ingestion/chunker.py`
- Modify: `tests/unit/test_chunker.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_chunker.py`:

```python
def test_chunk_documents_stamps_ingested_at():
    docs = [Document(page_content="Short text about Stoicism.", metadata={"tradition": "stoic"})]
    chunks = chunk_documents(docs)
    assert chunks
    for chunk in chunks:
        assert "ingested_at" in chunk.metadata, "Each chunk must have an ingested_at timestamp"
        # Must be a non-empty ISO 8601 string
        assert isinstance(chunk.metadata["ingested_at"], str)
        assert "T" in chunk.metadata["ingested_at"]  # ISO 8601 contains a T separator
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd soulra-backend && pytest tests/unit/test_chunker.py::test_chunk_documents_stamps_ingested_at -v
```

Expected: FAIL — `AssertionError: Each chunk must have an ingested_at timestamp`

- [ ] **Step 3: Implement the change in chunker.py**

Replace `soulra/services/ingestion/chunker.py` with:

```python
from datetime import datetime, timezone

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    length_function=len,
)


def chunk_documents(documents: list[Document]) -> list[Document]:
    now = datetime.now(timezone.utc).isoformat()
    chunks = _splitter.split_documents(documents)
    for chunk in chunks:
        chunk.metadata.setdefault("ingested_at", now)
    return [c for c in chunks if c.page_content.strip()]
```

- [ ] **Step 4: Run all chunker tests**

```bash
cd soulra-backend && pytest tests/unit/test_chunker.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add soulra/services/ingestion/chunker.py tests/unit/test_chunker.py
git commit -m "feat(rag): stamp ingested_at on every chunk for freshness tracking"
```

---

## Task 6: Create the rerank node

**Files:**
- Create: `soulra/graph/nodes/rerank.py`
- Create: `tests/unit/test_node_rerank.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_node_rerank.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


def _doc(content: str, **meta) -> Document:
    return Document(page_content=content, metadata=meta)


# ── _jaccard ────────────────────────────────────────────────────────────────

def test_jaccard_identical_texts():
    from soulra.graph.nodes.rerank import _jaccard
    assert _jaccard("the quick brown fox", "the quick brown fox") == 1.0


def test_jaccard_no_overlap():
    from soulra.graph.nodes.rerank import _jaccard
    assert _jaccard("alpha beta", "gamma delta") == 0.0


def test_jaccard_partial_overlap():
    from soulra.graph.nodes.rerank import _jaccard
    # shared: {"the"} — union: {"the", "cat", "dog"} → 1/3
    score = _jaccard("the cat", "the dog")
    assert abs(score - 1 / 3) < 1e-6


def test_jaccard_empty_strings():
    from soulra.graph.nodes.rerank import _jaccard
    assert _jaccard("", "") == 1.0


# ── _near_dedup ──────────────────────────────────────────────────────────────

def test_near_dedup_keeps_distinct_docs():
    from soulra.graph.nodes.rerank import _near_dedup
    docs = [_doc("Stoic wisdom about courage"), _doc("Buddhist teaching on impermanence")]
    result = _near_dedup(docs)
    assert len(result) == 2


def test_near_dedup_drops_near_duplicate():
    from soulra.graph.nodes.rerank import _near_dedup
    # Almost identical leading 120 chars
    base = "word " * 20           # 100 chars of shared content
    docs = [_doc(base + " extra_a"), _doc(base + " extra_b")]
    result = _near_dedup(docs)
    # Second doc is a near-duplicate of the first — should be dropped
    assert len(result) == 1
    assert result[0].page_content == docs[0].page_content


def test_near_dedup_keeps_first_and_drops_later():
    from soulra.graph.nodes.rerank import _near_dedup
    base = "identical content " * 7
    d1 = _doc(base + "end1")
    d2 = _doc(base + "end2")
    d3 = _doc("completely different wisdom passage about impermanence")
    result = _near_dedup([d1, d2, d3])
    assert len(result) == 2
    assert result[0] is d1
    assert result[1] is d3


# ── _u_shape ────────────────────────────────────────────────────────────────

def test_u_shape_empty():
    from soulra.graph.nodes.rerank import _u_shape
    assert _u_shape([]) == []


def test_u_shape_single_doc():
    from soulra.graph.nodes.rerank import _u_shape
    d = _doc("only doc")
    assert _u_shape([d]) == [d]


def test_u_shape_two_docs():
    from soulra.graph.nodes.rerank import _u_shape
    d1, d2 = _doc("rank1"), _doc("rank2")
    result = _u_shape([d1, d2])
    # rank1 → slot 0, rank2 → slot 1 (last)
    assert result == [d1, d2]


def test_u_shape_three_docs():
    from soulra.graph.nodes.rerank import _u_shape
    d1, d2, d3 = _doc("r1"), _doc("r2"), _doc("r3")
    result = _u_shape([d1, d2, d3])
    # r1 → 0, r2 → 2 (last), r3 → 1 (middle)
    assert result == [d1, d3, d2]


def test_u_shape_five_docs():
    from soulra.graph.nodes.rerank import _u_shape
    docs = [_doc(f"r{i}") for i in range(1, 6)]
    result = _u_shape(docs)
    # slot 0=r1, slot 1=r3, slot 2=r5, slot 3=r4, slot 4=r2
    assert result[0].page_content == "r1"   # most relevant → first
    assert result[4].page_content == "r2"   # 2nd most → last
    assert result[2].page_content == "r5"   # least relevant → middle


# ── rerank node ──────────────────────────────────────────────────────────────

def _make_state(**overrides):
    base = {
        "situation": "I feel overwhelmed",
        "query": "equanimity under pressure",
        "tradition_hints": ["stoic"],
        "retrieved_docs": [],
        "reranked_docs": [],
        "grade_result": "",
        "clarify_question": "",
        "clarify_chips": [],
        "clarify_answer": None,
        "refined_docs": [],
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_rerank_node_empty_docs_returns_empty():
    from soulra.graph.nodes.rerank import create_rerank_node
    mock_cohere = MagicMock()
    node = create_rerank_node(mock_cohere)
    result = await node(_make_state(retrieved_docs=[]))
    assert result == {"reranked_docs": []}
    mock_cohere.rerank.assert_not_called()


@pytest.mark.asyncio
async def test_rerank_node_calls_cohere_and_reorders():
    from soulra.graph.nodes.rerank import create_rerank_node

    d0 = _doc("least relevant passage")
    d1 = _doc("most relevant stoic passage about equanimity")
    d2 = _doc("moderately relevant passage")

    # Cohere ranks: index 1 first, index 2 second, index 0 third
    mock_result = [
        MagicMock(index=1, relevance_score=0.95),
        MagicMock(index=2, relevance_score=0.70),
        MagicMock(index=0, relevance_score=0.30),
    ]
    mock_cohere = MagicMock()
    mock_cohere.rerank = AsyncMock(return_value=MagicMock(results=mock_result))

    node = create_rerank_node(mock_cohere)
    state = _make_state(retrieved_docs=[d0, d1, d2])
    result = await node(state)

    reranked = result["reranked_docs"]
    # After U-shape with 3 docs: rank1→slot0, rank2→slot2(last), rank3→slot1
    assert reranked[0] is d1   # most relevant at front
    assert reranked[-1] is d2  # 2nd most relevant at back
    mock_cohere.rerank.assert_called_once_with(
        model="rerank-v3.5",
        query="equanimity under pressure",
        documents=["least relevant passage",
                   "most relevant stoic passage about equanimity",
                   "moderately relevant passage"],
        top_n=3,
    )


@pytest.mark.asyncio
async def test_rerank_node_falls_back_on_cohere_failure():
    from soulra.graph.nodes.rerank import create_rerank_node

    docs = [_doc(f"doc{i}") for i in range(7)]
    mock_cohere = MagicMock()
    mock_cohere.rerank = AsyncMock(side_effect=Exception("API unavailable"))

    node = create_rerank_node(mock_cohere)
    result = await node(_make_state(retrieved_docs=docs))

    # Graceful degradation: returns first 5 docs in original order
    assert len(result["reranked_docs"]) == 5
    assert result["reranked_docs"][0] is docs[0]


@pytest.mark.asyncio
async def test_rerank_node_uses_custom_input_output_keys():
    from soulra.graph.nodes.rerank import create_rerank_node

    d = _doc("refined passage")
    mock_cohere = MagicMock()
    mock_cohere.rerank = AsyncMock(
        return_value=MagicMock(results=[MagicMock(index=0, relevance_score=0.9)])
    )
    node = create_rerank_node(mock_cohere, input_key="refined_docs", output_key="reranked_docs")
    state = _make_state(refined_docs=[d])
    result = await node(state)
    assert "reranked_docs" in result
    assert len(result["reranked_docs"]) == 1
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
cd soulra-backend && pytest tests/unit/test_node_rerank.py -v
```

Expected: ModuleNotFoundError or ImportError — `rerank.py` does not exist yet.

- [ ] **Step 3: Implement `soulra/graph/nodes/rerank.py`**

Create `soulra/graph/nodes/rerank.py`:

```python
from langchain_core.documents import Document
from soulra.core.logging import logger
from soulra.graph.state import SoulraState


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _near_dedup(docs: list[Document], threshold: float = 0.8) -> list[Document]:
    accepted: list[Document] = []
    for doc in docs:
        lead = doc.page_content[:120]
        if not any(_jaccard(lead, a.page_content[:120]) > threshold for a in accepted):
            accepted.append(doc)
    return accepted


def _u_shape(docs: list[Document]) -> list[Document]:
    n = len(docs)
    if n == 0:
        return []
    result: list[Document | None] = [None] * n
    front, back = 0, n - 1
    for i, doc in enumerate(docs):
        if i % 2 == 0:
            result[front] = doc
            front += 1
        else:
            result[back] = doc
            back -= 1
    return [d for d in result if d is not None]


def create_rerank_node(cohere_client, input_key: str = "retrieved_docs", output_key: str = "reranked_docs"):
    async def rerank(state: SoulraState) -> dict:
        docs: list[Document] = state.get(input_key) or []
        if not docs:
            return {output_key: []}

        try:
            response = await cohere_client.rerank(
                model="rerank-v3.5",
                query=state["query"],
                documents=[d.page_content for d in docs],
                top_n=min(5, len(docs)),
            )
            ranked = [docs[r.index] for r in response.results]
        except Exception as exc:
            logger.warning("rerank_failed_fallback", error=str(exc))
            ranked = docs[:5]

        deduped = _near_dedup(ranked)
        shaped = _u_shape(deduped)
        return {output_key: shaped}

    return rerank
```

- [ ] **Step 4: Run all rerank tests**

```bash
cd soulra-backend && pytest tests/unit/test_node_rerank.py -v
```

Expected: all 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add soulra/graph/nodes/rerank.py tests/unit/test_node_rerank.py
git commit -m "feat(rag): add Cohere rerank node with near-dedup and U-shape ordering"
```

---

## Task 7: Increase retrieve k from 4 to 10

**Files:**
- Modify: `soulra/graph/nodes/retrieve.py`
- Modify: `tests/unit/test_node_retrieve_grade.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_node_retrieve_grade.py`:

```python
@pytest.mark.asyncio
async def test_retrieve_node_requests_k10_per_tradition(mock_vectorstore):
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever
    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)
    await retrieve(_make_state())
    # Each call to asimilarity_search must request k=10
    for call in mock_vectorstore.asimilarity_search.call_args_list:
        assert call.kwargs.get("k", call.args[1] if len(call.args) > 1 else None) == 10, \
            f"Expected k=10 but got: {call}"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd soulra-backend && pytest tests/unit/test_node_retrieve_grade.py::test_retrieve_node_requests_k10_per_tradition -v
```

Expected: FAIL — assertion error showing k=4.

- [ ] **Step 3: Update retrieve.py**

In `soulra/graph/nodes/retrieve.py`, change `k=4` to `k=10` in the `retriever.search(...)` call:

```python
        results = await asyncio.gather(
            *[retriever.search(query, tradition_filter=hint, k=10) for hint in hints]
        )
```

- [ ] **Step 4: Run retrieve tests**

```bash
cd soulra-backend && pytest tests/unit/test_node_retrieve_grade.py -k "retrieve" -v
```

Expected: all retrieve tests PASS.

- [ ] **Step 5: Commit**

```bash
git add soulra/graph/nodes/retrieve.py tests/unit/test_node_retrieve_grade.py
git commit -m "feat(rag): increase retrieval k from 4 to 10 per tradition"
```

---

## Task 8: Update grade node to read `reranked_docs` and emit selection_recall log

**Files:**
- Modify: `soulra/graph/nodes/grade.py`
- Modify: `tests/unit/test_node_retrieve_grade.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_node_retrieve_grade.py`:

```python
@pytest.mark.asyncio
async def test_grade_node_reads_from_reranked_docs_not_retrieved():
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    # reranked_docs has 1 doc; retrieved_docs has 5 irrelevant-looking ones
    reranked = [Document(page_content="Reranked stoic wisdom.", metadata={})]
    retrieved = [Document(page_content=f"retrieved-{i}", metadata={}) for i in range(5)]
    state = _make_state(reranked_docs=reranked, retrieved_docs=retrieved)
    result = await grade(state)
    # Grade is called once (for the 1 doc in reranked_docs)
    assert mock_llm.ainvoke.call_count == 1
    assert result["grade_result"] == "relevant"


@pytest.mark.asyncio
async def test_grade_node_emits_selection_recall_log(caplog):
    import logging
    from soulra.graph.nodes.grade import create_grade_node, GradeOutput
    from unittest.mock import AsyncMock
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=GradeOutput(score="yes"))
    grade = create_grade_node(mock_llm)

    retrieved = [Document(page_content=f"r{i}", metadata={"id": f"id{i}"}) for i in range(10)]
    reranked = retrieved[:3]
    await grade(_make_state(retrieved_docs=retrieved, reranked_docs=reranked))
    # structlog logs to stdout, not caplog — just verify no exception is raised
    # (The log is verified by observing it in the integration environment)
```

- [ ] **Step 2: Run the failing tests**

```bash
cd soulra-backend && pytest tests/unit/test_node_retrieve_grade.py::test_grade_node_reads_from_reranked_docs_not_retrieved -v
```

Expected: FAIL — grade reads `retrieved_docs`, so `ainvoke` is called 5 times not 1.

- [ ] **Step 3: Update grade.py**

Replace `soulra/graph/nodes/grade.py` with:

```python
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
        docs = state["reranked_docs"]
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

        logger.info(
            "selection_recall",
            total_retrieved=len(state["retrieved_docs"]),
            total_reranked=len(docs),
            graded_sample=len(sample),
            relevant_count=relevant_count,
            grade_result=grade_result,
            chunk_ids=[d.metadata.get("id", "?") for d in sample],
        )

        return {"grade_result": grade_result}

    return grade
```

- [ ] **Step 4: Update existing grade tests that pass `retrieved_docs` for grading**

In `tests/unit/test_node_retrieve_grade.py`, update these tests to pass docs via `reranked_docs`:

`test_grade_node_returns_relevant_when_majority_score_yes`:
```python
    result = await grade(_make_state(reranked_docs=docs))
```

`test_grade_node_returns_not_relevant_when_majority_score_no`:
```python
    docs = [Document(page_content="Recipes for pasta.", metadata={})]
    result = await grade(_make_state(reranked_docs=docs))
```

`test_grade_node_returns_relevant_for_single_doc_with_yes_score`:
```python
    docs = [Document(page_content="Stoic wisdom about equanimity.", metadata={})]
    result = await grade(_make_state(reranked_docs=docs))
```

`test_grade_node_returns_not_relevant_for_empty_docs`:
```python
    result = await grade(_make_state(reranked_docs=[]))
```

`test_grade_node_calls_ainvoke_concurrently`: update the state dict to include `"reranked_docs": docs` instead of relying on `retrieved_docs`:
```python
    state = {
        "situation": "test", "query": "test query",
        "retrieved_docs": docs,
        "reranked_docs": docs,    # grade reads from here now
        "tradition_hints": [],
        "grade_result": "", "clarify_question": "", "clarify_chips": [],
        "clarify_answer": None, "refined_docs": [], "tradition_cards": [],
        "action_steps": [], "messages": [], "rewrite_count": 0,
    }
```

- [ ] **Step 5: Run all grade tests**

```bash
cd soulra-backend && pytest tests/unit/test_node_retrieve_grade.py -k "grade" -v
```

Expected: all grade tests PASS.

- [ ] **Step 6: Commit**

```bash
git add soulra/graph/nodes/grade.py tests/unit/test_node_retrieve_grade.py
git commit -m "feat(rag): grade reads reranked_docs; add selection_recall structured log"
```

---

## Task 9: Update synthesize node

**Files:**
- Modify: `soulra/graph/nodes/synthesize.py`
- Modify: `tests/unit/test_node_synthesize.py`

- [ ] **Step 1: Write the failing tests**

Replace the full `tests/unit/test_node_synthesize.py` with:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


def _make_state(**overrides):
    docs = [
        Document(page_content="Stoic wisdom on equanimity.", metadata={
            "tradition": "stoic", "author": "Marcus Aurelius",
            "source": "Meditations", "era": "170 AD",
            "citation": "Meditations 6.13",
            "ingested_at": "2026-06-06T00:00:00+00:00",
        }),
    ]
    base = {
        "situation": "I say yes too much.",
        "query": "refusing",
        "tradition_hints": ["stoic"],
        "retrieved_docs": docs,
        "reranked_docs": docs,
        "grade_result": "relevant",
        "clarify_question": "Is this internal?",
        "clarify_chips": ["Yes", "No"],
        "clarify_answer": "Yes",
        "refined_docs": docs,
        "tradition_cards": [],
        "action_steps": [],
        "messages": [],
        "rewrite_count": 0,
    }
    base.update(overrides)
    return base


def _mock_llm_with_output(output):
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=output)
    return mock_llm


@pytest.mark.asyncio
async def test_synthesize_produces_tradition_cards_and_action_steps():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep,
    )
    mock_output = SynthesizeOutput(
        tradition_cards=[
            TraditionCard(
                tradition="Stoic",
                author="Marcus Aurelius",
                quote="You always own the option of having no opinion.",
                citation="Meditations 6.13",
                analysis="The Stoic move is to pause before committing.",
                source_passage="You always own the option of having no opinion.",
            )
        ],
        action_steps=[
            ActionStep(n="01", title="Notice the moment of yes", body="Pause for one breath."),
            ActionStep(n="02", title="Name what you want", body="Write one sentence."),
            ActionStep(n="03", title="Say a small no", body="Decline one small thing."),
        ],
    )
    synthesize = create_synthesize_node(_mock_llm_with_output(mock_output))
    result = await synthesize(_make_state())
    assert len(result["tradition_cards"]) == 1
    assert result["tradition_cards"][0]["tradition"] == "Stoic"
    assert len(result["action_steps"]) == 3


@pytest.mark.asyncio
async def test_synthesize_tradition_card_has_source_passage():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep,
    )
    mock_output = SynthesizeOutput(
        tradition_cards=[
            TraditionCard(
                tradition="Buddhist",
                author="Pema Chödrön",
                quote="Lean into the sharp points.",
                citation="When Things Fall Apart",
                analysis="Resistance makes things worse.",
                source_passage="Lean into the sharp points and fully experience them.",
            )
        ],
        action_steps=[
            ActionStep(n="01", title="t1", body="b1"),
            ActionStep(n="02", title="t2", body="b2"),
            ActionStep(n="03", title="t3", body="b3"),
        ],
    )
    synthesize = create_synthesize_node(_mock_llm_with_output(mock_output))
    result = await synthesize(_make_state())
    card = result["tradition_cards"][0]
    assert "source_passage" in card, "TraditionCard must include source_passage for grounding verification"
    assert card["source_passage"]   # must be non-empty


@pytest.mark.asyncio
async def test_synthesize_reads_from_reranked_docs():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep,
    )
    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self
        async def ainvoke(self, prompt):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[TraditionCard(
                    tradition="S", author="A", quote="q", citation="c",
                    analysis="a", source_passage="sp",
                )],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    reranked_doc = Document(page_content="RERANKED wisdom.", metadata={
        "tradition": "stoic", "author": "Marcus", "source": "Med",
        "era": "170AD", "ingested_at": "2026-06-06T00:00:00+00:00",
    })
    result = await synthesize(_make_state(reranked_docs=[reranked_doc]))
    assert "RERANKED wisdom." in captured_prompt[0], \
        "synthesize must read from reranked_docs"


@pytest.mark.asyncio
async def test_synthesize_context_label_includes_metadata_fields():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep,
    )
    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self
        async def ainvoke(self, prompt):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[TraditionCard(
                    tradition="S", author="A", quote="q", citation="c",
                    analysis="a", source_passage="sp",
                )],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    doc = Document(page_content="wisdom here", metadata={
        "tradition": "stoic", "author": "Marcus Aurelius",
        "source": "Meditations", "era": "170 AD",
        "ingested_at": "2026-06-06T00:00:00+00:00",
    })
    await synthesize(_make_state(reranked_docs=[doc]))
    prompt = captured_prompt[0]
    assert "Marcus Aurelius" in prompt
    assert "Meditations" in prompt
    assert "170 AD" in prompt
    assert "2026-06-06" in prompt   # ingested_at visible to LLM


@pytest.mark.asyncio
async def test_synthesize_prompt_contains_grounding_instruction():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep,
    )
    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self
        async def ainvoke(self, prompt):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[TraditionCard(
                    tradition="S", author="A", quote="q", citation="c",
                    analysis="a", source_passage="sp",
                )],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    await synthesize(_make_state())
    prompt = captured_prompt[0]
    assert "ONLY" in prompt, "Prompt must contain strong grounding instruction"
    assert "verbatim" in prompt.lower(), "Prompt must require verbatim quotes"


@pytest.mark.asyncio
async def test_synthesize_caps_content_at_500_chars():
    from soulra.graph.nodes.synthesize import (
        create_synthesize_node, SynthesizeOutput, TraditionCard, ActionStep,
    )
    captured_prompt = []

    class CaptureLLM:
        def with_structured_output(self, schema):
            return self
        async def ainvoke(self, prompt):
            captured_prompt.append(prompt)
            return SynthesizeOutput(
                tradition_cards=[TraditionCard(
                    tradition="S", author="A", quote="q", citation="c",
                    analysis="a", source_passage="sp",
                )],
                action_steps=[ActionStep(n="01", title="t", body="b")],
            )

    synthesize = create_synthesize_node(CaptureLLM())
    doc = Document(page_content="X" * 2000, metadata={
        "tradition": "stoic", "author": "A", "source": "B",
        "era": "?", "ingested_at": "2026-06-06T00:00:00+00:00",
    })
    await synthesize(_make_state(reranked_docs=[doc]))
    assert "X" * 501 not in captured_prompt[0]
    assert "X" * 499 in captured_prompt[0]
```

- [ ] **Step 2: Run the failing tests**

```bash
cd soulra-backend && pytest tests/unit/test_node_synthesize.py -v
```

Expected: several FAIL — missing `source_passage` field, wrong docs key, missing metadata in labels.

- [ ] **Step 3: Implement updated synthesize.py**

Replace `soulra/graph/nodes/synthesize.py` with:

```python
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
    source_passage: str   # verbatim excerpt ≤200 chars grounding this card


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
        result: SynthesizeOutput = await structured_llm.ainvoke(prompt)
        return {
            "tradition_cards": [c.model_dump() for c in result.tradition_cards],
            "action_steps": [s.model_dump() for s in result.action_steps],
        }

    return synthesize
```

- [ ] **Step 4: Run all synthesize tests**

```bash
cd soulra-backend && pytest tests/unit/test_node_synthesize.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add soulra/graph/nodes/synthesize.py tests/unit/test_node_synthesize.py
git commit -m "feat(rag): richer context labels, grounding prompt, source_passage citation field"
```

---

## Task 10: Set temperature=0 on all LLMs

**Files:**
- Modify: `soulra/services/llm/factory.py`
- Modify: `tests/unit/test_llm_factory.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_llm_factory.py`:

```python
def test_make_chat_llm_uses_temperature_zero():
    with patch("soulra.services.llm.factory.settings") as mock_settings:
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.smart_model = "anthropic/claude-opus-4-8"
        from soulra.services.llm.factory import make_chat_llm
        llm = make_chat_llm("anthropic/claude-opus-4-8")
        assert llm.temperature == 0, \
            f"LLM temperature must be 0 for deterministic RAG output, got {llm.temperature}"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd soulra-backend && pytest tests/unit/test_llm_factory.py::test_make_chat_llm_uses_temperature_zero -v
```

Expected: FAIL — temperature is not set (defaults to 0.7 or similar).

- [ ] **Step 3: Add temperature=0 to factory.py**

In `soulra/services/llm/factory.py`, update `make_chat_llm`:

```python
def make_chat_llm(model: str, streaming: bool = True) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_BASE,
        api_key=settings.openrouter_api_key,
        streaming=streaming,
        temperature=0,
    )
```

- [ ] **Step 4: Run all factory tests**

```bash
cd soulra-backend && pytest tests/unit/test_llm_factory.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add soulra/services/llm/factory.py tests/unit/test_llm_factory.py
git commit -m "feat(rag): set temperature=0 for deterministic LLM output"
```

---

## Task 11: Wire rerank nodes into the graph builder

**Files:**
- Modify: `soulra/graph/builder.py`
- Modify: `tests/unit/test_graph_builder.py`

- [ ] **Step 1: Write the failing test**

Replace the `test_graph_builds_without_error` test in `tests/unit/test_graph_builder.py`:

```python
def test_graph_builds_without_error():
    from langgraph.checkpoint.memory import MemorySaver
    from soulra.graph.builder import build_graph

    mock_cohere = MagicMock()
    graph = build_graph(
        retriever=MagicMock(),
        fast_llm=MagicMock(),
        smart_llm=MagicMock(),
        checkpointer=MemorySaver(),
        cohere_client=mock_cohere,
    )
    assert graph is not None


def test_graph_contains_rerank_nodes():
    from langgraph.checkpoint.memory import MemorySaver
    from soulra.graph.builder import build_graph

    graph = build_graph(
        retriever=MagicMock(),
        fast_llm=MagicMock(),
        smart_llm=MagicMock(),
        checkpointer=MemorySaver(),
        cohere_client=MagicMock(),
    )
    node_names = set(graph.nodes.keys())
    assert "rerank" in node_names, "Graph must contain a 'rerank' node"
    assert "rerank_refined" in node_names, "Graph must contain a 'rerank_refined' node"
```

- [ ] **Step 2: Run to confirm the tests fail**

```bash
cd soulra-backend && pytest tests/unit/test_graph_builder.py -v
```

Expected: FAIL — `build_graph` has no `cohere_client` param.

- [ ] **Step 3: Update the existing edge-routing tests**

The three `test_route_after_grade_*` tests reference a state dict without `reranked_docs`. Add it to each:

```python
def test_route_after_grade_returns_rewrite_when_not_relevant():
    from soulra.graph.edges import route_after_grade
    state = {
        "grade_result": "not_relevant", "rewrite_count": 0,
        "situation": "", "tradition_hints": [], "query": "",
        "retrieved_docs": [], "reranked_docs": [],
        "clarify_question": "", "clarify_chips": [], "clarify_answer": None,
        "refined_docs": [], "tradition_cards": [], "action_steps": [],
        "messages": [],
    }
    assert route_after_grade(state) == "rewrite_query"
```

Apply the same `"reranked_docs": []` addition to the other two `route_after_grade` tests.

- [ ] **Step 4: Update builder.py**

Replace `soulra/graph/builder.py` with:

```python
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI

from soulra.graph.state import SoulraState
from soulra.graph.edges import route_after_grade
from soulra.graph.nodes.intake import create_intake_node
from soulra.graph.nodes.retrieve import create_retrieve_node
from soulra.graph.nodes.rerank import create_rerank_node
from soulra.graph.nodes.grade import create_grade_node
from soulra.graph.nodes.rewrite import create_rewrite_node
from soulra.graph.nodes.clarify import create_clarify_node
from soulra.graph.nodes.synthesize import create_synthesize_node
from soulra.services.retrieval.retriever import WisdomRetriever


def build_graph(
    retriever: WisdomRetriever,
    fast_llm: ChatOpenAI,
    smart_llm: ChatOpenAI,
    checkpointer: BaseCheckpointSaver,
    cohere_client,
):
    workflow = StateGraph(SoulraState)

    workflow.add_node("intake", create_intake_node(fast_llm))
    workflow.add_node("retrieve", create_retrieve_node(retriever))
    workflow.add_node("rerank", create_rerank_node(cohere_client, input_key="retrieved_docs", output_key="reranked_docs"))
    workflow.add_node("grade_docs", create_grade_node(fast_llm))
    workflow.add_node("rewrite_query", create_rewrite_node(fast_llm))
    workflow.add_node("clarify", create_clarify_node(fast_llm))
    workflow.add_node("retrieve_refined", create_retrieve_node(retriever, output_key="refined_docs"))
    workflow.add_node("rerank_refined", create_rerank_node(cohere_client, input_key="refined_docs", output_key="reranked_docs"))
    workflow.add_node("synthesize", create_synthesize_node(smart_llm))

    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "retrieve")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "grade_docs")
    workflow.add_conditional_edges("grade_docs", route_after_grade)
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("clarify", "retrieve_refined")
    workflow.add_edge("retrieve_refined", "rerank_refined")
    workflow.add_edge("rerank_refined", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["retrieve_refined"],
    )
```

- [ ] **Step 5: Run all graph builder tests**

```bash
cd soulra-backend && pytest tests/unit/test_graph_builder.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Run the full unit test suite**

```bash
cd soulra-backend && pytest tests/unit/ -v
```

Expected: all tests PASS (no regressions).

- [ ] **Step 7: Commit**

```bash
git add soulra/graph/builder.py tests/unit/test_graph_builder.py
git commit -m "feat(rag): wire Cohere rerank nodes into LangGraph pipeline"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| `cohere>=5.0` dependency | Task 1 |
| `cohere_api_key` in config | Task 1 |
| Cohere client singleton | Task 2 |
| Lifespan init + `build_graph` arg | Task 3 |
| `reranked_docs` state field | Task 4 |
| `ingested_at` on every chunk | Task 5 |
| Rerank node: Cohere call, near-dedup, U-shape | Task 6 |
| `retrieve` k=10 | Task 7 |
| `grade` reads `reranked_docs`; `selection_recall` log | Task 8 |
| Richer context labels | Task 9 |
| Grounding instruction | Task 9 |
| `source_passage` on `TraditionCard` | Task 9 |
| `synthesize` reads `reranked_docs` | Task 9 |
| `temperature=0` | Task 10 |
| Rerank nodes in graph, `rerank_refined` path | Task 11 |

All spec requirements covered. ✓
