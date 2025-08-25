from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import UUID

from pybotx import Bot, File, SmartAppEvent
from pybotx.missing import Missing, Undefined


class SmartApp:
    """
    Represents a SmartApp that integrates with a bot for communication and events.

    This class is designed to facilitate interaction with a bot to send smartapp
    events and notifications. Its primary purpose is to provide managing
    smartapp-related notifications and events within a chat context.

    :ivar bot: The bot instance used for communicating with the smart app.
    :type bot: Bot
    :ivar event: Optional event related to the smart app context.
    :type event: Optional[SmartAppEvent]
    :ivar bot_id: Unique identifier for the bot.
    :type bot_id: UUID
    :ivar chat_id: Unique identifier for the chat associated with the smart app.
    :type chat_id: UUID
    :ivar state: A simple namespace object for maintaining state information.
    :type state: SimpleNamespace
    """

    def __init__(
        self,
        bot: Bot,
        bot_id: UUID,
        chat_id: UUID,
        event: Optional[SmartAppEvent] = None,
    ) -> None:
        self.bot = bot
        self.event = event

        self.bot_id = bot_id
        self.chat_id = chat_id

        self.state = SimpleNamespace()

    async def send_event(
        self,
        rpc_result: Any,
        files: Optional[List[File]] = None,
        encrypted: bool = True,
    ) -> None:
        await self.bot.send_smartapp_event(
            bot_id=self.bot_id,
            chat_id=self.chat_id,
            data={
                "status": "ok",
                "type": "smartapp_rpc",
                "result": rpc_result,
            },
            files=files or [],
            encrypted=encrypted,
        )

    async def send_push(self, counter: int, body: Missing[str] = Undefined) -> None:
        await self.bot.send_smartapp_notification(
            bot_id=self.bot_id,
            chat_id=self.chat_id,
            smartapp_counter=counter,
            body=body,
        )

    async def send_custom_push(
        self,
        title: str,
        body: str,
        meta: Missing[Dict[str, Any]] = Undefined,
        wait_callback: bool = True,
        callback_timeout: Optional[float] = None,
    ) -> UUID:
        return await self.bot.send_smartapp_custom_notification(
            bot_id=self.bot_id,
            group_chat_id=self.chat_id,
            title=title,
            body=body,
            meta=meta,
            wait_callback=wait_callback,
            callback_timeout=callback_timeout,
        )
