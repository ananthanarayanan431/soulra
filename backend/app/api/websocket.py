# app/api/websocket.py
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas.websocket import (
    StartMessage, ClarificationMessage,
    StatusEvent, ClarifyEvent, ChipsEvent,
    TraditionDoneEvent, ActionStepEvent, DoneEvent, ErrorEvent,
)
from app.core.logging import logger

router = APIRouter(tags=["websocket"])

_graph = None


def get_graph():
    return _graph


def set_graph(g) -> None:
    global _graph
    _graph = g


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
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
        raw = await websocket.receive_json()
        msg = StartMessage(**raw)

        await send(StatusEvent(node="intake").model_dump())

        initial_input = {
            "situation": msg.situation,
            "tradition_hints": [],
            "query": "",
            "retrieved_docs": [],
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

        async for event in graph.astream_events(initial_input, config, version="v2"):
            name = event.get("name", "")
            etype = event.get("event", "")

            if etype == "on_chain_start" and name in (
                "retrieve", "grade_docs", "rewrite_query", "clarify"
            ):
                await send(StatusEvent(node=name).model_dump())

            if etype == "on_chain_end" and name == "clarify":
                output = event.get("data", {}).get("output", {})
                question = output.get("clarify_question", "")
                chips = output.get("clarify_chips", [])
                if question:
                    await send(ClarifyEvent(question=question).model_dump())
                    await send(ChipsEvent(options=chips).model_dump())
                break  # graph is now paused at interrupt_before["retrieve_refined"]

        # Phase 2: wait for chip selection, resume graph
        raw = await websocket.receive_json()
        clarification = ClarificationMessage(**raw)

        await send(StatusEvent(node="retrieve_refined").model_dump())

        await graph.aupdate_state(
            config,
            {"clarify_answer": clarification.choice},
        )

        async for event in graph.astream_events(None, config, version="v2"):
            name = event.get("name", "")
            etype = event.get("event", "")

            if etype == "on_chain_start" and name in ("retrieve_refined", "synthesize"):
                await send(StatusEvent(node=name).model_dump())

            if etype == "on_chain_end" and name == "synthesize":
                output = event.get("data", {}).get("output", {})
                for card in output.get("tradition_cards", []):
                    await send(TraditionDoneEvent(**card).model_dump())
                for step in output.get("action_steps", []):
                    await send(ActionStepEvent(**step).model_dump())
                break

        await send(DoneEvent().model_dump())

    except WebSocketDisconnect:
        logger.info("ws_disconnected", thread_id=thread_id)
    except Exception as e:
        logger.error("ws_error", error=str(e), thread_id=thread_id)
        try:
            await send(ErrorEvent(message=str(e)).model_dump())
        except Exception:
            pass
