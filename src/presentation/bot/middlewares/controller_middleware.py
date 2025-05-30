from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from src.presentation.bot.controllers import TranscribumController

class ControllerMiddleware(BaseMiddleware):
    def __init__(self, controller: TranscribumController):
        self.controller = controller

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["transcribum_controller"] = self.controller
        return await handler(event, data)