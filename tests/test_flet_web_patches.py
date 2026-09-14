import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.runtime.flet_web_patches import patch_flet_web_session_disconnect


class FakeSession:
    def __init__(self, session_id="session-1"):
        self.id = session_id
        self.connection = None


def build_module(crash=True):
    class FletApp:
        def __init__(self, session=None, send_queue=("pending",), websocket="old-websocket"):
            self.__session = session
            self.__send_queue = send_queue
            self.__websocket = websocket
            self.__session_timeout_seconds = 3600
            self.__crash = crash

        def __get_unique_session_id(self, session_id):
            return f"unique-{session_id}"

        async def handle(self, websocket):
            self.__websocket = websocket
            if self.__crash:
                raise RuntimeError("send_bytes failed")
            self.__send_queue = None
            self.__websocket = None

    return SimpleNamespace(
        FletApp=FletApp,
        app_manager=SimpleNamespace(disconnect_session=AsyncMock()),
    )


class FletWebSessionDisconnectGuardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = build_module()
        patch_flet_web_session_disconnect(self.module)

    async def test_aborted_handler_disconnects_owned_session(self):
        session = FakeSession()
        app = self.module.FletApp(session=session)
        session.connection = app

        with self.assertRaises(RuntimeError):
            await app.handle("websocket")

        self.module.app_manager.disconnect_session.assert_awaited_once_with("unique-session-1", 3600)
        self.assertIsNone(getattr(app, "_FletApp__send_queue"))
        self.assertIsNone(getattr(app, "_FletApp__websocket"))

    async def test_completed_handler_is_not_disconnected_again(self):
        self.module = build_module(crash=False)
        patch_flet_web_session_disconnect(self.module)
        session = FakeSession()
        app = self.module.FletApp(session=session)
        session.connection = None

        await app.handle("websocket")

        self.module.app_manager.disconnect_session.assert_not_awaited()

    async def test_reconnected_session_is_not_disconnected_by_old_handler(self):
        session = FakeSession()
        app = self.module.FletApp(session=session)
        session.connection = object()

        with self.assertRaises(RuntimeError):
            await app.handle("websocket")

        self.module.app_manager.disconnect_session.assert_not_awaited()
        self.assertEqual(getattr(app, "_FletApp__send_queue"), ("pending",))

    async def test_handler_without_session_is_ignored(self):
        app = self.module.FletApp(session=None)

        with self.assertRaises(RuntimeError):
            await app.handle("websocket")

        self.module.app_manager.disconnect_session.assert_not_awaited()

    async def test_guard_failure_does_not_mask_original_error(self):
        session = FakeSession()
        app = self.module.FletApp(session=session)
        session.connection = app
        self.module.app_manager.disconnect_session.side_effect = RuntimeError("disconnect failed")

        with self.assertRaises(RuntimeError) as context:
            await app.handle("websocket")

        self.assertEqual(str(context.exception), "send_bytes failed")
        self.assertIsNone(getattr(app, "_FletApp__send_queue"))

    def test_patch_is_idempotent(self):
        guarded_handle = self.module.FletApp.handle

        patch_flet_web_session_disconnect(self.module)

        self.assertIs(self.module.FletApp.handle, guarded_handle)


if __name__ == "__main__":
    unittest.main()
