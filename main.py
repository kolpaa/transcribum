import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import ClientSession, ClientTimeout

from config.config_reader import config
from src.presentation.bot.handlers import common
from src.presentation.bot.middlewares.controller_middleware import ControllerMiddleware
from src.presentation.bot.controllers import TranscribumController

from src.application.use_cases import UserService, TranscriberQueueProcessor, FilesQueue, ApplicationService
from src.domain.entities import User, QueueElement
from src.infrastructure.common_services import FileService, LinkService
from src.infrastructure.transcriber.whisper_transcriber import WhisperTranscriber
from src.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from src.infrastructure.LLM.ai_service import AIService
from src.infrastructure.cash_repositories.cash_user_repository import CashUserRepository

# nohup python main.py > output.log 2>&1 &
#api-hash 528fb3e8cd77bf41d19a436cd79b7d2f
#api-id 24809041
#./telegram-bot-api --local --api-id=24809041 --api-hash=528fb3e8cd77bf41d19a436cd79b7d2f
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    session = AiohttpSession(
    api=TelegramAPIServer.from_base('http://localhost:8081'))
    bot = Bot(config.TG_BOT_TOKEN.get_secret_value(), session=session)

    files_queue = FilesQueue()
    transcriber = WhisperTranscriber({'device': config.WHISPER_DEVICE,
                                      'model': config.WHISPER_MODEL,
                                      "transcripts_dir": config.TRANSCRIPTS_DIR})
    user_service = UserService(repo=SQLAlchemyUserRepository(), cash_repo=CashUserRepository())
    ai_service = AIService(generation_model=config.LLM_MODEL, auth=config.AUTH, folder_id=config.FOLDER_ID)
    transcriber_service = ApplicationService(service=transcriber, 
                                             file_service=FileService, 
                                             user_service=user_service, 
                                             queue=files_queue,
                                             ai_service=ai_service,
                                             link_service=LinkService,
                                             config = config)
    controller = TranscribumController(config=config, bot=bot, transcriber_service=transcriber_service)
    dp.update.middleware(ControllerMiddleware(controller))
    dp.include_router(common.router)

    processor = TranscriberQueueProcessor(transcriber_service)
    asyncio.create_task(processor.start())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())
