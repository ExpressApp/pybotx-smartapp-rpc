from unittest.mock import AsyncMock
from uuid import UUID

from pybotx import Document, Image

from pybotx_smartapp_rpc.smartapp import SmartApp


async def test_send_event(
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
    document: Document,
    image: Image,
) -> None:
    # - Arrange -
    smartapp = SmartApp(bot, bot_id, chat_id)

    # - Act -
    await smartapp.send_event(42, files=[document, image])

    # - Assert -
    assert len(bot.method_calls) == 1
    bot.send_smartapp_event.assert_awaited_once_with(
        bot_id=bot_id,
        chat_id=chat_id,
        files=[document, image],
        data={
            "status": "ok",
            "type": "smartapp_rpc",
            "result": 42,
        },
        encrypted=True,
    )


async def test_send_push(
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
) -> None:
    # - Arrange -
    smartapp = SmartApp(bot, bot_id, chat_id)

    # - Act -
    await smartapp.send_push(42, "Pushed!")

    # - Assert -
    assert len(bot.method_calls) == 1
    bot.send_smartapp_notification.assert_awaited_once_with(
        bot_id=bot_id,
        chat_id=chat_id,
        smartapp_counter=42,
        body="Pushed!",
    )


async def test_send_custom_push(
    bot: AsyncMock,
    bot_id: UUID,
    chat_id: UUID,
) -> None:
    # - Arrange -
    smartapp = SmartApp(bot, bot_id, chat_id)

    # - Act -
    await smartapp.send_custom_push("test", "test", {"message": "ping"})

    # - Assert -
    assert len(bot.method_calls) == 1
    bot.send_smartapp_custom_notification.assert_awaited_once_with(
        bot_id=bot_id,
        group_chat_id=chat_id,
        title="test",
        body="test",
        meta={"message": "ping"},
        wait_callback=True,
        callback_timeout=None,
    )
