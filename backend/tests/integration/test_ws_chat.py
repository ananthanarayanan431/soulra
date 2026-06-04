# tests/integration/test_ws_chat.py
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock


def test_ws_chat_accepts_connection():
    """WebSocket endpoint is registered and accepts connections."""
    from app.main import app
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as ws:
        # Graph is None in test — should get SERVICE_UNAVAILABLE and close
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "SERVICE_UNAVAILABLE"


def test_ws_chat_sends_clarify_and_done():
    """Full happy-path: start → clarify → clarification → done."""
    from app.main import app
    from app.api.websocket import set_graph

    # Build a mock graph
    clarify_events = [
        {"event": "on_chain_start", "name": "intake", "data": {}},
        {"event": "on_chain_start", "name": "retrieve", "data": {}},
        {"event": "on_chain_start", "name": "clarify", "data": {}},
        {
            "event": "on_chain_end",
            "name": "clarify",
            "data": {
                "output": {
                    "clarify_question": "Is this internal or external?",
                    "clarify_chips": ["Internal", "External", "Both", "Not sure"],
                }
            },
        },
    ]
    synthesize_events = [
        {"event": "on_chain_start", "name": "retrieve_refined", "data": {}},
        {"event": "on_chain_start", "name": "synthesize", "data": {}},
        {
            "event": "on_chain_end",
            "name": "synthesize",
            "data": {
                "output": {
                    "tradition_cards": [
                        {
                            "tradition": "Stoic",
                            "author": "Marcus Aurelius",
                            "quote": "You always own the option of having no opinion.",
                            "citation": "Meditations 6.13",
                            "analysis": "The Stoic move is to notice the request comes from outside.",
                        }
                    ],
                    "action_steps": [
                        {"n": "01", "title": "Notice yes", "body": "Pause one breath."},
                    ],
                }
            },
        },
    ]

    async def _astream_phase1(*args, **kwargs):
        for e in clarify_events:
            yield e

    async def _astream_phase2(*args, **kwargs):
        for e in synthesize_events:
            yield e

    call_count = 0

    def astream_events_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _astream_phase1()
        return _astream_phase2()

    mock_graph = MagicMock()
    mock_graph.astream_events = astream_events_side_effect
    mock_graph.aupdate_state = AsyncMock()

    set_graph(mock_graph)

    try:
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"type": "start", "situation": "I say yes too much."})

            messages = []
            # Collect until we see chips (phase 1 complete)
            for _ in range(20):
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg["type"] == "chips":
                        break
                except Exception:
                    break

            ws.send_json({"type": "clarification", "choice": "Internal"})

            # Collect until done
            for _ in range(20):
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg["type"] in ("done", "error"):
                        break
                except Exception:
                    break

        types = [m["type"] for m in messages]
        assert "clarify" in types, f"Expected clarify in {types}"
        assert "chips" in types, f"Expected chips in {types}"
        assert "done" in types, f"Expected done in {types}"
        tradition_dones = [m for m in messages if m["type"] == "tradition_done"]
        assert len(tradition_dones) == 1
        assert tradition_dones[0]["tradition"] == "Stoic"
        mock_graph.aupdate_state.assert_called_once()
        call_args = mock_graph.aupdate_state.call_args
        assert call_args[0][1]["clarify_answer"] == "Internal"
    finally:
        set_graph(None)
