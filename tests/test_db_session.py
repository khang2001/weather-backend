"""
Phase 0 — F1: get_db() must close the session even when the request raises.
"""


def test_get_db_closes_session_on_exception():
    from app.database.connection import get_db

    gen = get_db()
    session = next(gen)            # enters the `try`, yields the session

    closed = {"value": False}
    original_close = session.close
    session.close = lambda: (closed.__setitem__("value", True), original_close())[1]

    # Simulate the route raising mid-request; the finally block must still close.
    try:
        gen.throw(RuntimeError("boom"))
    except RuntimeError:
        pass

    assert closed["value"] is True, "get_db did not close the session on exception (F1)"
