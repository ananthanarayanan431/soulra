from fastapi import APIRouter, HTTPException, Query
from soulra.schemas.passage import PassageOut
from soulra.schemas.responses import SuccessResponse

router = APIRouter(tags=["passages"])


def _get_vs():
    from soulra.dependencies import get_vectorstore
    return get_vectorstore()


@router.get("/passages", response_model=SuccessResponse[list[PassageOut]])
async def list_passages(
    tradition: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    vectorstore = _get_vs()
    filter_kwargs: dict = {"k": limit}
    if tradition:
        filter_kwargs["filter"] = {"tradition": tradition}
    try:
        docs = await vectorstore.asimilarity_search("wisdom", **filter_kwargs)
    except Exception:
        docs = []
    return SuccessResponse(data=[
        PassageOut(
            id=d.metadata.get("id", str(i)),
            content=d.page_content,
            tradition=d.metadata.get("tradition"),
            author=d.metadata.get("author"),
            source=d.metadata.get("source"),
            era=d.metadata.get("era"),
            citation=d.metadata.get("citation"),
        )
        for i, d in enumerate(docs)
    ])


@router.delete("/passages/{passage_id}", status_code=204)
async def delete_passage(passage_id: str):
    vectorstore = _get_vs()
    try:
        await vectorstore.adelete(ids=[passage_id])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=SuccessResponse[list[dict]])
async def list_collections():
    vectorstore = _get_vs()
    return SuccessResponse(data=[{"name": vectorstore.collection_name}])
