import unittest
from unittest.mock import AsyncMock, patch

from app.messages.notification_service import NotificationService


class NotificationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_email_delivery_runs_blocking_smtp_work_in_thread(self):
        expected = {"success": ["receiver@example.com"], "error": []}

        with patch("app.messages.notification_service.asyncio.to_thread", new=AsyncMock(return_value=expected)) as run:
            result = await NotificationService.send_to_email(
                email_host="smtp.example.com",
                login_email="sender@example.com",
                password="secret",
                sender_email="sender@example.com",
                sender_name="StreamCap",
                to_email="receiver@example.com",
                title="test",
                content="message",
            )

        assert result == expected
        run.assert_awaited_once()
        assert callable(run.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
