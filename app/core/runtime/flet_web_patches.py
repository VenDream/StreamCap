"""Runtime guards for Flet web defects that cannot be fixed upstream yet."""

from ...utils.logger import logger


async def _disconnect_aborted_session(connection, app_manager) -> None:
    """Detach a session whose FletApp handler exited before cleanup."""
    session = getattr(connection, "_FletApp__session", None)
    send_queue = getattr(connection, "_FletApp__send_queue", None)
    if session is None or send_queue is None:
        return
    if getattr(session, "connection", None) is not connection:
        return

    try:
        await app_manager.disconnect_session(
            connection._FletApp__get_unique_session_id(session.id),
            connection._FletApp__session_timeout_seconds,
        )
    finally:
        connection._FletApp__websocket = None
        connection._FletApp__send_queue = None


def patch_flet_web_session_disconnect(flet_app_module=None) -> None:
    """Guarantee Flet web session cleanup when the outbound send loop aborts.

    Flet 0.85.3 only calls ``app_manager.disconnect_session()`` after both
    WebSocket loops finish normally. When the browser closes while outbound
    messages are still queued, ``FletApp.__send_loop`` raises on
    ``send_bytes`` and ``handle()`` aborts before disconnecting the session.
    The orphaned session keeps its ``connection`` reference, so StreamCap
    keeps broadcasting recording-card updates into the dead connection's
    unbounded ``asyncio.Queue``. This accumulated 2.5 million messages
    (about 1.7 GB) in production over four days and caused the container OOM.
    """
    if flet_app_module is None:
        from flet_web.fastapi import flet_app as flet_app_module

    flet_app_class = flet_app_module.FletApp
    original_handle = flet_app_class.handle
    if getattr(original_handle, "_streamcap_disconnect_guard", False):
        return
    if not hasattr(flet_app_class, "_FletApp__get_unique_session_id"):
        logger.warning("Flet web internals changed; session disconnect guard was not installed")
        return

    app_manager = flet_app_module.app_manager

    async def handle_with_disconnect_guard(self, websocket):
        try:
            await original_handle(self, websocket)
        finally:
            try:
                await _disconnect_aborted_session(self, app_manager)
            except Exception:
                logger.exception("Flet web session disconnect guard failed")

    handle_with_disconnect_guard._streamcap_disconnect_guard = True
    flet_app_class.handle = handle_with_disconnect_guard
    logger.info("Flet web session disconnect guard installed")
