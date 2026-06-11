import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.database import get_db
from soulra.models.tradition import Tradition
from soulra.schemas.responses import SuccessResponse
from soulra.schemas.tradition import (
    CreateTradition,
    PreferencesUpdate,
    TraditionOut,
    TraditionsResponse,
    TraditionUpdate,
)


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


router = APIRouter(tags=["traditions"])

_COLLECTION = "wisdom_passages"

_COUNTS_SQL = text("""
    SELECT
        cmetadata->>'tradition' AS tradition_slug,
        COUNT(*)::int              AS passages,
        COUNT(DISTINCT cmetadata->>'source')::int AS sources
    FROM langchain_pg_embedding
    WHERE collection_id = (
        SELECT uuid FROM langchain_pg_collection WHERE name = :collection
    )
    GROUP BY cmetadata->>'tradition'
""")


async def _passage_counts(db: AsyncSession) -> dict[str, dict]:
    try:
        rows = (await db.execute(_COUNTS_SQL, {"collection": _COLLECTION})).mappings().all()
        return {
            r["tradition_slug"]: {"passages": r["passages"], "sources": r["sources"]}
            for r in rows
            if r["tradition_slug"]
        }
    except Exception:
        return {}


@router.get(
    "/traditions",
    response_model=SuccessResponse[TraditionsResponse],
    summary="List wisdom traditions",
    description="Returns all wisdom traditions with live passage/source counts from the vector store and the current user selection.",
)
async def list_traditions(
    era: str | None = Query(
        default=None, description="Filter by era: ancient, medieval, perennial"
    ),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tradition).order_by(Tradition.name)
    if era and era != "all":
        stmt = stmt.where(Tradition.era == era)
    rows = (await db.execute(stmt)).scalars().all()
    counts = await _passage_counts(db)

    traditions = []
    for t in rows:
        c = counts.get(t.slug, {"passages": 0, "sources": 0})
        traditions.append(
            TraditionOut(
                slug=t.slug,
                name=t.name,
                origin=t.origin,
                era=t.era,
                sources=c["sources"],
                passages=c["passages"],
                selected=t.user_selected,
                description=t.description,
            )
        )

    return SuccessResponse(
        data=TraditionsResponse(
            traditions=traditions,
            total_sources=sum(t.sources for t in traditions),
            total_passages=sum(t.passages for t in traditions),
        )
    )


@router.get(
    "/eras",
    response_model=SuccessResponse[list[str]],
    summary="List distinct era values",
)
async def list_eras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tradition.era).distinct().order_by(Tradition.era))
    eras = [row[0] for row in result.all()]
    return SuccessResponse(data=eras)


@router.post(
    "/traditions",
    response_model=SuccessResponse[TraditionOut],
    status_code=201,
    summary="Create a new wisdom tradition",
)
async def create_tradition(body: CreateTradition, db: AsyncSession = Depends(get_db)):
    slug = body.slug or _slugify(body.name)
    if await db.get(Tradition, slug):
        raise HTTPException(status_code=409, detail=f"Tradition '{slug}' already exists")
    tradition = Tradition(
        slug=slug,
        name=body.name,
        origin=body.origin,
        era=body.era,
        user_selected=False,
        description=body.description,
    )
    db.add(tradition)
    await db.commit()
    await db.refresh(tradition)
    return SuccessResponse(
        data=TraditionOut(
            slug=tradition.slug,
            name=tradition.name,
            origin=tradition.origin,
            era=tradition.era,
            sources=0,
            passages=0,
            selected=False,
            description=tradition.description,
        )
    )


@router.put(
    "/traditions/preferences",
    status_code=204,
    summary="Update tradition selection",
    description="Replaces the current tradition selection. Pass the complete list of selected slugs.",
)
async def update_preferences(
    body: PreferencesUpdate,
    db: AsyncSession = Depends(get_db),
):
    selected_set = set(body.selected)
    rows = (await db.execute(select(Tradition))).scalars().all()
    for t in rows:
        t.user_selected = t.slug in selected_set
    await db.commit()


@router.get(
    "/traditions/{slug}",
    response_model=SuccessResponse[TraditionOut],
    summary="Get a wisdom tradition",
    description="Fetches a single tradition by slug, including live passage/source counts. Returns 404 if the slug doesn't exist.",
)
async def get_tradition(slug: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Tradition, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")
    counts = await _passage_counts(db)
    c = counts.get(row.slug, {"passages": 0, "sources": 0})
    return SuccessResponse(
        data=TraditionOut(
            slug=row.slug,
            name=row.name,
            origin=row.origin,
            era=row.era,
            sources=c["sources"],
            passages=c["passages"],
            selected=row.user_selected,
            description=row.description,
        )
    )


@router.put(
    "/traditions/{slug}",
    response_model=SuccessResponse[TraditionOut],
    summary="Update a wisdom tradition",
    description="Partially updates a tradition's name, origin, era, or description — only the provided fields change. The slug is immutable. Returns 404 if the slug doesn't exist.",
)
async def update_tradition(slug: str, body: TraditionUpdate, db: AsyncSession = Depends(get_db)):
    row = await db.get(Tradition, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")

    if body.name is not None:
        row.name = body.name
    if body.origin is not None:
        row.origin = body.origin
    if body.era is not None:
        row.era = body.era
    if body.description is not None:
        row.description = body.description
    await db.commit()
    await db.refresh(row)

    counts = await _passage_counts(db)
    c = counts.get(row.slug, {"passages": 0, "sources": 0})
    return SuccessResponse(
        data=TraditionOut(
            slug=row.slug,
            name=row.name,
            origin=row.origin,
            era=row.era,
            sources=c["sources"],
            passages=c["passages"],
            selected=row.user_selected,
            description=row.description,
        )
    )


@router.delete(
    "/traditions/{slug}",
    status_code=204,
    summary="Delete a wisdom tradition",
    description="Permanently removes a tradition by slug. Returns 404 if the slug doesn't exist, otherwise 204 No Content.",
)
async def delete_tradition(slug: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Tradition, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")
    await db.delete(row)
    await db.commit()
    return Response(status_code=204)
