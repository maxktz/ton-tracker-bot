import asyncio
import io
import random
import string
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from aiogram import BaseMiddleware, Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.i18n import gettext as _
from bot.bot_controller import try_delete_message
from bot.services.users import add_user, user_exists
from bot.utils.command import find_command_argument
from cachetools import TTLCache
from captcha.image import ImageCaptcha
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


class states(StatesGroup):
    solve_captcha_state = State("solve_captcha_state")


    async def ask_captcha(self, user_id: int, bot: Bot, state: FSMContext) -> None:
        future = asyncio.get_running_loop().create_future()
        self.futures[user_id] = future
        await self.send_captcha(user_id, bot, state)


class AuthMiddleware:

    def __init__(
        self,
        *,
    ) -> None:
        super().__init__(
            captcha_length=captcha_length,
            captcha_width=captcha_width,
            captcha_height=captcha_height,
            captcha_fonts=captcha_fonts,
            captcha_font_sizes=captcha_font_sizes,
        )
        self.ask_captcha = ask_captcha

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        session: AsyncSession = data["session"]
        state: FSMContext = data["state"]
        message: Message = event
        user = message.from_user

        if not user:
            return await handler(event, data)

        if await user_exists(session, user.id):
            return await handler(event, data)

        referrer_id = find_command_argument(message.text)
        logger.info(f"new user registration | user_id: {user.id} | message: {message.text}")
        await add_user(session=session, user=user, referrer_id=referrer_id)
        return await handler(event, data)
