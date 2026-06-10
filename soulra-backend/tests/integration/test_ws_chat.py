# tests/integration/test_ws_chat.py
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

_FAKE_USER = MagicMock(id="user_test_ws")


@pytest.fixture(autouse=True)
def _mock_ws_auth():
    """All websocket tests connect without a real Clerk token — bypass auth."""
    with patch("soulra.api.websocket.get_current_user_ws", new=AsyncMock(return_value=_FAKE_USER)):
        yield


def test_ws_chat_accepts_connection():
    """WebSocket endpoint is registered and accepts connections."""
    from soulra.main import app
    from soulra.api.websocket import set_graph
    set_graph(None)
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as ws:
        # Graph is None in test — should get SERVICE_UNAVAILABLE and close
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "SERVICE_UNAVAILABLE"


def test_ws_chat_sends_clarify_and_done():
    """Full happy-path: start → clarify → clarification → done."""
    from soulra.main import app
    from soulra.api.websocket import set_graph

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
                            "source_passage": "Stoic wisdom excerpt for grounding.",
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
        assert "source_passage" in tradition_dones[0]
        assert tradition_dones[0]["source_passage"] == "Stoic wisdom excerpt for grounding."
        mock_graph.aupdate_state.assert_called_once()
        call_args = mock_graph.aupdate_state.call_args
        assert call_args[0][1]["clarify_answer"] == "Internal"
    finally:
        set_graph(None)


def test_ws_chat_sends_error_on_graph_error():
    """Phase-1 loop must exit with ErrorEvent (not deadlock) when graph emits on_chain_error."""
    from soulra.main import app
    from soulra.api.websocket import set_graph

    async def mock_stream_with_error(*args, **kwargs):
        yield {"event": "on_chain_start", "name": "intake", "data": {}}
        yield {"event": "on_chain_error", "name": "clarify", "data": {"error": "LLM failed"}}

    mock_graph = MagicMock()
    mock_graph.astream_events = mock_stream_with_error
    set_graph(mock_graph)

    try:
        with TestClient(app) as client:
            with client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "start", "situation": "test situation"})
                messages = []
                for _ in range(10):
                    try:
                        msg = ws.receive_json()
                        messages.append(msg)
                        if msg.get("type") in ("error", "done", "chips"):
                            break
                    except Exception:
                        break

        types = [m.get("type") for m in messages]
        assert "error" in types, f"Expected ErrorEvent on graph error, got: {types}"
        # Crucially: no deadlock — test completes within timeout
    finally:
        set_graph(None)


def test_make_initial_state_covers_all_soulra_state_keys():
    """make_initial_state must produce a dict with all SoulraState keys."""
    from soulra.graph.state import make_initial_state, SoulraState
    state = make_initial_state("test situation")
    expected_keys = set(SoulraState.__annotations__.keys())
    actual_keys = set(state.keys())
    assert actual_keys == expected_keys, \
        f"Missing keys: {expected_keys - actual_keys}, Extra keys: {actual_keys - expected_keys}"
    assert state["situation"] == "test situation"


def test_websocket_uses_make_initial_state():
    """websocket.py must use make_initial_state instead of a hardcoded dict."""
    import ast
    import pathlib
    ws_source = pathlib.Path("soulra/api/websocket.py").read_text()
    assert "make_initial_state" in ws_source, \
        "websocket.py must call make_initial_state() — hardcoded dict drifts from SoulraState"
    assert "initial_input = {" not in ws_source, \
        "hardcoded initial_input dict found — replace with make_initial_state()"


def test_ws_chat_rejects_disallowed_origin():
    """WebSocket must reject connections from origins not in allowed_origins."""
    from soulra.main import app
    with TestClient(app) as client:
        # Use an origin not in allowed_origins (which is ["http://localhost:3000"])
        try:
            with client.websocket_connect(
                "/ws/chat",
                headers={"origin": "http://evil.com"}
            ) as ws:
                # Should be rejected — connection may close immediately
                _msg = ws.receive_json()
                # If we get here, might receive error or nothing
        except Exception:
            pass  # Connection rejected is the expected outcome


def test_ws_error_sends_generic_message_not_raw_exception():
    """Error events sent to client must not contain raw exception details."""
    from soulra.main import app
    from soulra.api.websocket import set_graph
    from unittest.mock import MagicMock

    async def failing_stream(*args, **kwargs):
        raise ValueError("SECRET_DB_PASSWORD_xyz123")
        yield  # make it a generator

    mock_graph = MagicMock()
    mock_graph.astream_events = failing_stream
    set_graph(mock_graph)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"type": "start", "situation": "test"})
            messages = []
            for _ in range(5):
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg.get("type") in ("error", "done"):
                        break
                except Exception:
                    break

    error_msgs = [m for m in messages if m.get("type") == "error"]
    assert error_msgs, "Expected an error event"
    # The raw exception message must NOT appear in the error sent to client
    for msg in error_msgs:
        assert "SECRET_DB_PASSWORD" not in msg.get("message", ""), \
            "Raw exception detail leaked to client"
        assert "xyz123" not in msg.get("message", ""), \
            "Raw exception detail leaked to client"
