import os
import asyncio
import re
from functools import wraps
from aiogram import Bot
from functools import partial
from aiogram.types import FSInputFile
from src.application.use_cases import ApplicationService
from src.domain.constants import LLMPrompts, ResultExtensions
from .views import TranscibumViews, INITIAL_SELECTION, OPTIONS


def check_user_registered(func):
    @wraps(func)
    async def wrapper(self, message, *args, **kwargs):
        if not await self.transcriber_service.user_service.is_user(id=message.from_user.id):
            await self.transcriber_service.user_service.add_user(id=message.from_user.id)
        return await func(self, message, *args, **kwargs)
    return wrapper


class TranscribumController():
    def __init__(self, config, bot : Bot, transcriber_service: ApplicationService):
        self.bot : Bot = bot
        self.config = config  
        self.transcriber_service = transcriber_service
        self.views = TranscibumViews()

    async def handle_start(self, message):
        await message.answer(self.views.get_greeting())



    async def delete_old_selections(self, user_id, message_id, file_path):
        await asyncio.sleep(300)
        try:
            await self.bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="Вы не выбрали параметры, сессия отменена. Пожалуйста, отправьте файл заново.",
                reply_markup=None
            )
            self.transcriber_service.file_service.delete_files(file_path)
        except Exception:
            pass

    async def show_options_keyboard(self, message, file_path):
        user_id = message.from_user.id
        user_options = await self.transcriber_service.user_service.cash_repo.get_user_selection(user_id)
        if not user_options:
            user_options =  INITIAL_SELECTION.copy()
            await self.transcriber_service.user_service.cash_repo.set_user_selection(user_id=user_id,
                                                                                     selection=user_options)
        keyboard = self.views.get_options_keyboard(selection=user_options)
        msg = await message.answer("Выберите формат и опции:", reply_markup=keyboard)
        asyncio.create_task(self.delete_old_selections(user_id=message.from_user.id, 
                                                       message_id=msg.message_id,
                                                       file_path = file_path))

    async def handle_toggle_callback(self, callback):
        user_id = callback.from_user.id

        user_options = await self.transcriber_service.user_service.cash_repo.get_user_selection(user_id)
        if not user_options:
            user_options =  INITIAL_SELECTION.copy()
            await self.transcriber_service.user_service.cash_repo.set_user_selection(user_id=user_id,
                                                                                     selection=user_options)

        _, key_name, value = callback.data.split(":")
        current_value = bool(int(value))
        key = None
        for k in OPTIONS:
            if k.name == key_name:  
                key = k
                break

        if key is None:
            await callback.answer("Ошибка: неизвестная опция")
            return

        await self.transcriber_service.user_service.cash_repo.set_user_selection_value(user_id=user_id,
                                                                                       key=key,
                                                                                       value=not current_value)
        new_keyboard_data = await self.transcriber_service.user_service.cash_repo.get_user_selection(user_id=user_id)
        markup = self.views.get_options_keyboard(new_keyboard_data)
        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer()

    async def handle_confirm_callback(self, callback):
        user_id = callback.from_user.id
        user_options = await self.transcriber_service.user_service.cash_repo.get_user_selection(user_id)
        if not user_options:
            user_options =  INITIAL_SELECTION.copy()

        res = {"prompts":[], "formats": []}
        print(user_options.items())
        for key, value in user_options.items():
            if key in LLMPrompts.__members__.values() and user_options[key]:
                res["prompts"].append(LLMPrompts(key))
            elif key in ResultExtensions.__members__.values() and user_options[key]:
                res["formats"].append(ResultExtensions(key))


        await callback.message.delete()
        await callback.message.answer(f"Вы выбрали:\n\n{res}")

        input_path = await self.transcriber_service.user_service.cash_repo.get_user_file(user_id)
        if input_path:
            await self.transcriber_service.prepare_transcription_request(
                options = res,
                file_path=input_path,
                user_id=user_id,
                callback=self.handle_transcription_result,
                on_insufficient_funds=lambda uid: self.bot.send_message(uid, self.views.top_up_balance_message()),
                on_wrong_format=lambda uid: self.bot.send_message(uid, self.views.file_format_error())
            )
        else:
            await self.bot.send_message(user_id, text="Сессия истекла, вышлите файл заново")
    
    async def handle_callback(self, callback):
        if callback.data.startswith("toggle:"):
            await self.handle_toggle_callback(callback=callback)
        else:
            await self.handle_confirm_callback(callback=callback)




    @check_user_registered
    async def handle_new_file(self, message):
        file_obj = message.audio or message.video or message.document
        file = await message.bot.get_file(file_obj.file_id)
        file_path = file.file_path
        user_path = await self.transcriber_service.get_user_path(base_path=self.config.DOWNLOADS_DIR, 
                                                                 user_adapter_id=message.from_user.id)
        file_name = file_obj.file_name
        if not file_name:
            file_name = os.path.basename(file_path)

        input_path = os.path.join(user_path, file_name)
        await message.bot.download_file(file_path, destination=input_path)

        if not self.transcriber_service.queue.get_user_files_from_queue(message.from_user.id):
            await self.transcriber_service.user_service.cash_repo.remove_user_files(message.from_user.id)
        await self.transcriber_service.user_service.cash_repo.add_user_file(message.from_user.id, input_path)
        await self.show_options_keyboard(message=message, file_path = input_path)

    async def handle_transcription_result(self, output_files, error, user_id, ai_jobs=[]):
        if error:
            await self.bot.send_message(
                chat_id=user_id,  
                text=self.views.file_processing_error_message(error=error)
            )
            return
        for output_file in output_files:
            filename = os.path.basename(output_file )
            file = FSInputFile(output_file , filename=filename)
            await self.bot.send_document(
                    chat_id=user_id,
                    document=file
                )
        if ai_jobs:
            await self.handle_ai_jobs(file=output_files[0], ai_jobs=ai_jobs, user_id=user_id)
        self.transcriber_service.file_service.delete_files(*output_files)


    async def handle_ai_jobs(self, file, ai_jobs, user_id):
        ai_service = self.transcriber_service.ai_service
        collection_name = await asyncio.to_thread(partial(
            ai_service.make_embedding_collection,
            file_path = file
        ))
        for prompt in ai_jobs:
            answer = await asyncio.to_thread(partial(
                ai_service.generate_answer,
                prompt = prompt,
                collection_name = collection_name
            ))

            await self.bot.send_message(
                chat_id=user_id,  
                text=answer
            )

        ai_service.cleanup(collection_name)
        return 
        
    @check_user_registered
    async def handle_new_links(self, message):
        all_links = self.transcriber_service.link_service.parse_links(message.text)
        user_path = await self.transcriber_service.get_user_path(base_path=self.config.DOWNLOADS_DIR, 
                                                                 user_adapter_id=message.from_user.id)
        for link in all_links:
            file = await asyncio.to_thread(partial(
                                            self.transcriber_service.link_service.download_link,
                                            link = link,
                                            download_dir = user_path
                                            ))
            await self.transcriber_service.user_service.cash_repo.add_user_file(message.from_user.id, file)
            await self.show_options_keyboard(message=message, file_path = file)
