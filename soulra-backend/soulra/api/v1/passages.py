from fastapi import APIRouter, HTTPException, Query
from soulra.core.logging import logger
from soulra.schemas.passage import PassageOut
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["passages"])


def _get_vs():
    from soulra.dependencies import get_vectorstore
    return get_vectorstore()


@router.get("/passages", response_model=SuccessResponse[list[PassageOut]])
async def list_passages(
    tradition: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),  # reserved: applied when similarity search is replaced by SQL listing
):
    vectorstore = _get_vs()
    filter_kwargs: dict = {"k": limit}
    if tradition:
        filter_kwargs["filter"] = {"tradition": tradition}
    try:
        docs = await vectorstore.asimilarity_search("wisdom", **filter_kwargs)
    except Exception:
        logger.exception("passages_similarity_search_failed")
        raise HTTPException(status_code=503, detail="Passage search unavailable")
    passages = []
    for d in docs:
        pid = d.metadata.get("id")
        if not pid:
            logger.warning("passage_missing_id", metadata=d.metadata)
            continue
        passages.append(PassageOut(
            id=pid,
            content=d.page_content,
            tradition=d.metadata.get("tradition"),
            author=d.metadata.get("author"),
            source=d.metadata.get("source"),
            era=d.metadata.get("era"),
            citation=d.metadata.get("citation"),
        ))
    return SuccessResponse(data=passages)


@router.delete("/passages/{passage_id}", status_code=204)
async def delete_passage(passage_id: str):
    vectorstore = _get_vs()
    try:
        await vectorstore.adelete(ids=[passage_id])
    except Exception:
        logger.exception("passage_delete_failed", passage_id=passage_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/collections", response_model=SuccessResponse[list[dict]])
async def list_collections():
    vectorstore = _get_vs()
    return SuccessResponse(data=[{"name": vectorstore.collection_name}])
