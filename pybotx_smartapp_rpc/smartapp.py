from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import UUID

from pybotx import Bot, File, SmartAppEvent
from pybotx.missing import Missing, Undefined


class SmartApp:
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
