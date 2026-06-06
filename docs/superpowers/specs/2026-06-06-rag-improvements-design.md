# RAG Improvements Design — Soulra Backend

**Date:** 2026-06-06  
**Scope:** Low-effort + medium-effort tiers from the 15-point RAG improvement framework  
**Status:** Approved for implementation

---

## 1. Goals

Address seven known failure modes in the current Soulra retrieval-synthesis pipeline:

| # | Failure mode | Fix |
|---|---|---|
| 1 | Context labels give no author/source/freshness signal | Richer chunk headers in synthesize prompt |
| 2 | Fixed-size splitter cuts sentences; model gets half-facts | `ingested_at` metadata + better label; chunk boundary issue acknowledged, splitter unchanged (already RecursiveCharacterTextSplitter) |
| 3 | Most-relevant chunk ends up in middle of context (LLM ignores it) | U-shape reordering after reranking |
| 4 | Only 4 docs retrieved per tradition; relevant chunks may never be fetched | Retrieve 10 per tradition, Cohere rerank to top 5 |
| 5 | Prompt does not explicitly forbid non-context knowledge | Strengthened grounding instruction |
| 6 | No way to tell if a card is hallucinated vs grounded | `source_passage` field on `TraditionCard` |
| 7 | No visibility into which docs survived to synthesis | `selection_recall` structured log |

Out of scope for this sprint: conflict detection, multi-hop decomposition, HyDE, `conflict_free_rate` eval metric.

---

## 2. Architecture

### 2.1 Graph topology change

```
Before:
  retrieve → grade_docs → rewrite_query ↩
                        → clarify → retrieve_refined → synthesize

After:
  retrieve → rerank → grade_docs → rewrite_query ↩
                                 → clarify → retrieve_refined → rerank_refined → synthesize
```

Two instances of the rerank node: one for the initial retrieval path, one for the refined path after clarification. Both use the same `create_rerank_node` factory.

### 2.2 Files touched

| File | Change |
|---|---|
| `graph/nodes/rerank.py` | **New** — Cohere rerank, near-dedup, U-shape |
| `graph/builder.py` | Wire both rerank nodes into graph |
| `graph/state.py` | Add `reranked_docs: list[Document]` |
| `graph/nodes/retrieve.py` | k: 4 → 10 per tradition |
| `graph/nodes/grade.py` | Read `reranked_docs`; emit `selection_recall` log |
| `graph/nodes/synthesize.py` | Richer labels, stronger prompt, `source_passage`, temp=0 |
| `services/ingestion/chunker.py` | Stamp `ingested_at` on every chunk |
| `services/ingestion/pipeline.py` | No change needed; chunker handles metadata |
| `config.py` | `cohere_api_key: str` |
| `dependencies.py` | `get_cohere_client()` singleton |
| `main.py` | Init Cohere client in lifespan |
| `pyproject.toml` | Add `cohere>=5.0` |

---

## 3. Component Designs

### 3.1 `graph/nodes/rerank.py` (new)

**Inputs:** `state["retrieved_docs"]` (or `state["refined_docs"]`), `state["query"]`  
**Output key:** `reranked_docs`

**Algorithm:**

```
1. If docs is empty → return {output_key: []}
2. Call cohere.rerank(
       model="rerank-v3.5",
       query=state["query"],
       documents=[d.page_content for d in docs],
       top_n=min(5, len(docs)),
   )
3. Near-dedup: iterate ranked results in order; compute Jaccard similarity
   on whitespace-tokenised sets of the leading 120 chars of each pair.
   Skip any result where Jaccard > 0.8 vs any already-accepted result.
4. U-shape ordering on accepted results (N ≤ 5).
   Build output list of length N; fill alternating from front and back:
       front_ptr = 0, back_ptr = N-1
       rank 1 → output[front_ptr++]
       rank 2 → output[back_ptr--]
       rank 3 → output[front_ptr++]  ... etc.
   Works correctly for any N (1–5); middle slots have lowest LLM attention.
5. Return {output_key: u_shaped_docs}
```

**Error handling:** If Cohere call fails, log a warning and return docs in original order (graceful degradation — retrieval still works, reranking is skipped).

**Factory signature:**
```python
def create_rerank_node(cohere_client, output_key: str = "reranked_docs") -> Callable
```

### 3.2 `graph/nodes/retrieve.py`

Single change: `k=4` → `k=10` in the `retriever.search(...)` call.  
No other changes; existing concurrent-gather + exact-content dedup remain.

### 3.3 `graph/nodes/grade.py`

- Read `state["reranked_docs"]` instead of `state["retrieved_docs"]`
- After grading, emit one structured log line:

```python
logger.info(
    "selection_recall",
    total_retrieved=len(state["retrieved_docs"]),
    total_reranked=len(reranked),
    graded_sample=len(sample),
    relevant_count=relevant_count,
    chunk_ids=[d.metadata.get("id", "?") for d in sample],
)
```

### 3.4 `graph/nodes/synthesize.py`

**Context label format per chunk:**
```
[{tradition} | {author} | {source} | era: {era} | ingested: {ingested_at}]
{page_content}
```

**Grounding instruction added to SYNTHESIZE_PROMPT:**
```
GROUNDING RULES:
- Answer ONLY from the passages provided above.
- Every quote field must be verbatim text copied from a passage — no paraphrasing.
- If a passage does not contain sufficient wisdom for a card, omit the card rather than inventing content.
- Do not draw on general knowledge. If the answer is not in the passages, say so.
```

**`TraditionCard` model — new field:**
```python
source_passage: str  # verbatim excerpt (≤200 chars) that grounds this card
```

**Temperature:** `make_smart_llm()` and `make_fast_llm()` both called with `temperature=0`.  
Rationale: deterministic failures are debuggable; random hallucinations are not.

### 3.5 `services/ingestion/chunker.py`

Add `ingested_at` (ISO 8601 UTC string) to every chunk's metadata at split time:

```python
from datetime import datetime, timezone

def chunk_documents(documents: list[Document]) -> list[Document]:
    now = datetime.now(timezone.utc).isoformat()
    chunks = _splitter.split_documents(documents)
    for chunk in chunks:
        chunk.metadata.setdefault("ingested_at", now)
    return [c for c in chunks if c.page_content.strip()]
```

Stored in PGVector's `cmetadata` JSON column — no migration needed.

### 3.6 `config.py` + `dependencies.py`

```python
# config.py
cohere_api_key: str
```

```python
# dependencies.py
_cohere_client = None

def set_cohere_client(c) -> None: ...
def get_cohere_client(): ...
```

`main.py` lifespan: `import cohere; set_cohere_client(cohere.AsyncClient(settings.cohere_api_key))`.

Use `cohere.AsyncClient` so the rerank call is non-blocking inside the async graph nodes.

---

## 4. State Changes

```python
# graph/state.py — one new field
reranked_docs: list[Document]   # output of rerank node; input to grade + synthesize
```

`SoulraState` and `make_initial_state` both updated to include `reranked_docs: []`.

---

## 5. Error Handling

| Failure | Behaviour |
|---|---|
| Cohere API timeout / error | Log warning, pass `retrieved_docs` through unchanged as `reranked_docs` |
| `cohere_api_key` missing | App fails at startup (Pydantic validation) — required field, no default |
| Empty `retrieved_docs` | Rerank node short-circuits; returns `reranked_docs: []`; grade returns `not_relevant` as before |

---

## 6. Testing Notes

- `rerank` node testable in isolation: mock `cohere_client.rerank()`, assert U-shape ordering and dedup logic
- `grade` node: update fixture to pass `reranked_docs` in state
- `synthesize` node: assert `source_passage` present on every `TraditionCard`
- Chunker: assert `ingested_at` key present in every chunk's metadata

---

## 7. Out of Scope

- Conflict detection between retrieved chunks
- Multi-hop query decomposition
- HyDE (hypothetical document expansion)
- `conflict_free_rate` eval metric
- Stale-index filtering/TTL enforcement (field is stored but no filter logic this sprint)
