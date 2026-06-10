# app/api/websocket.py
import asyncio
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from soulra.database import AsyncSessionLocal
from soulra.core.auth import get_current_user_ws
from soulra.services.practice_builder import save_conversation_and_create_arc
from soulra.schemas.websocket import (
    StartMessage, ClarificationMessage,
    StatusEvent, ClarifyEvent, ChipsEvent,
    TraditionDoneEvent, ActionStepEvent, DoneEvent, ErrorEvent,
)
from soulra.core.logging import logger
from soulra.graph.state import make_initial_state
from soulra.config import settings

router = APIRouter(tags=["websocket"])

_graph = None

WS_RECEIVE_TIMEOUT = 60  # seconds


def get_graph():
    return _graph


def set_graph(g) -> None:
    global _graph
    _graph = g


@router.websocket("/ws/chat", name="chat_ws")
async def chat_ws(websocket: WebSocket):
    origin = websocket.headers.get("origin", "")
    if origin and origin not in settings.allowed_origins:
        await websocket.close(code=1008)
        return
    await websocket.accept()

    async with AsyncSessionLocal() as auth_db:
        current_user = await get_current_user_ws(websocket, auth_db)
        await auth_db.commit()
    if current_user is None:
        await websocket.close(code=1008)
        return

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async def send(payload: dict) -> None:
        await websocket.send_text(json.dumps(payload))

    graph = get_graph()
    if graph is None:
        await send(ErrorEvent(message="Service not ready", code="SERVICE_UNAVAILABLE").model_dump())
        await websocket.close()
        return

    try:
        # Phase 1: receive situation, run graph until interrupt at retrieve_refined
        try:
            raw = await asyncio.wait_for(websocket.receive_json(), timeout=WS_RECEIVE_TIMEOUT)
        except asyncio.TimeoutError:
            await send(ErrorEvent(message="Connection timed out", code="TIMEOUT").model_dump())
            await websocket.close()
            return
        msg = StartMessage(**raw)

        await send(StatusEvent(node="intake").model_dump())

        initial_input = make_initial_state(msg.situation)

        clarify_done = False
        clarify_q = ""
        async for event in graph.astream_events(initial_input, config, version="v2"):
            name = event.get("name", "")
            etype = event.get("event", "")

            if etype == "on_chain_start" and name in (
                "retrieve", "grade_docs", "rewrite_query", "clarify"
            ):
                await send(StatusEvent(node=name).model_dump())

            if etype == "on_chain_error":
                err = event.get("data", {}).get("error", "graph error")
                await send(ErrorEvent(message=str(err), code="GRAPH_ERROR").model_dump())
                await websocket.close()
                return

            if etype == "on_chain_end" and name == "clarify":
                output = event.get("data", {}).get("output", {})
                clarify_q = output.get("clarify_question", "")
                chips = output.get("clarify_chips", [])
                if clarify_q:
                    await send(ClarifyEvent(question=clarify_q).model_dump())
                    await send(ChipsEvent(options=chips).model_dump())
                clarify_done = True
                break  # graph is now paused at interrupt_before["retrieve_refined"]

        if not clarify_done:
            await send(ErrorEvent(message="Conversation ended before clarification", code="GRAPH_INCOMPLETE").model_dump())
            await websocket.close()
            return

        # Phase 2: wait for chip selection, resume graph
        try:
            raw = await asyncio.wait_for(websocket.receive_json(), timeout=WS_RECEIVE_TIMEOUT)
        except asyncio.TimeoutError:
            await send(ErrorEvent(message="Connection timed out", code="TIMEOUT").model_dump())
            await websocket.close()
            return
        clarification = ClarificationMessage(**raw)

        await send(StatusEvent(node="retrieve_refined").model_dump())

        await graph.aupdate_state(
            config,
            {"clarify_answer": clarification.choice},
            as_node="retrieve_refined",
        )

        async for event in graph.astream_events(None, config, version="v2"):
            name = event.get("name", "")
            etype = event.get("event", "")

            if etype == "on_chain_start" and name in ("retrieve_refined", "synthesize"):
                await send(StatusEvent(node=name).model_dump())

            if etype == "on_chain_end" and name == "synthesize":
                output = event.get("data", {}).get("output", {})
                tradition_cards = output.get("tradition_cards", [])
                action_steps = output.get("action_steps", [])
                for card in tradition_cards:
                    await send(TraditionDoneEvent(**card).model_dump())
                for step in action_steps:
                    await send(ActionStepEvent(**step).model_dump())
                conv_id = str(uuid.uuid4())
                asyncio.create_task(save_conversation_and_create_arc(
                    conversation_id=conv_id,
                    thread_id=thread_id,
                    situation=msg.situation,
                    clarify_q=clarify_q,
                    clarify_ans=clarification.choice,
                    tradition_cards_data=tradition_cards,
                    action_steps_data=action_steps,
                    user_id=current_user.id,
                ))
                break

        await send(DoneEvent(conversation_id=conv_id).model_dump())

    except WebSocketDisconnect:
        logger.info("ws_disconnected", thread_id=thread_id)
    except Exception as e:
        err_ref = str(uuid.uuid4())[:8]
        logger.error("ws_error", error=str(e), thread_id=thread_id, ref=err_ref)
        try:
            await send(ErrorEvent(message=f"Internal server error, ref: {err_ref}").model_dump())
        except Exception:
            pass
