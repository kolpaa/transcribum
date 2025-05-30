from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, Audio
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.chat_action import ChatActionMiddleware
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import flags, types, Bot
import asyncio
from src.presentation.bot.states import RegularStates
from config.config_reader import config
from src.application.use_cases import UserService
from src.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from src.presentation.bot.controllers import TranscribumController

from src.domain.entities import User
from src.domain.constants import LLMPrompts, ResultExtensions


router = Router()

@router.message(F.audio | F.video | F.document)
async def handle_file(message, transcribum_controller: TranscribumController):
    await transcribum_controller.handle_new_file(message)


@router.callback_query()
async def handle_callback(callback: types.CallbackQuery, transcribum_controller : TranscribumController):
    await transcribum_controller.handle_callback(callback)


@router.message(Command("start"))
async def start_selection(message: types.Message, transcribum_controller : TranscribumController):
    await transcribum_controller.handle_start(message)


@router.message(F.text)
async def handle_link(message, transcribum_controller : TranscribumController):
    await transcribum_controller.handle_new_links(message)