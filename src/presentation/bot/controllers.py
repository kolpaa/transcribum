import os
import asyncio
import re
import shutil, random, string
from functools import wraps
from aiogram import Bot
from functools import partial
from aiogram.types import FSInputFile
from src.application.use_cases import ApplicationService
from src.domain.constants import LLMPrompts, ResultExtensions
from .views import TranscibumViews, INITIAL_SELECTION, OPTIONS, GPTCallback


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

    async def check_files(self, message):
        files = self.transcriber_service.queue.get_user_files_from_queue(user_id=message.from_user.id)
        files_message = ""
        print(files)
        current_file = self.transcriber_service.queue.current_file
        offset = 0
        if current_file and current_file.user_id == message.from_user.id:
            files_message += f"Файл {1}: {os.path.basename(current_file.file_path)}\nПозиция в очереди: {0}\n\n"
            offset = 1
        for position, file in enumerate(files):
            pos = await self.transcriber_service.queue.get_position(user_id=message.from_user.id, file_path=file.file_path)
            files_message += f"Файл {position+ 1 + offset}: {os.path.basename(file.file_path)}\nПозиция в очереди: {pos + 1}\n\n"
        if files_message:
            await self.bot.send_message(chat_id=message.from_user.id, text=files_message)
        else:
            await self.bot.send_message(chat_id=message.from_user.id, text="У вас нет файлов в очереди")

    async def delete_old_selections(self, user_id, message_id, file_path):
        await asyncio.sleep(100)
        try:
            await self.bot.delete_message(chat_id=user_id, message_id=message_id)
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
            await self.add_file(user_id=user_id, options=res, input_path=file_path)
            # await self.bot.edit_message_text(
            #     chat_id=user_id,
            #     message_id=message_id,
            #     text="Вы не выбрали параметры, сессия отменена. Пожалуйста, отправьте файл заново.",
            #     reply_markup=None
            # )
            # self.transcriber_service.file_service.delete_files(file_path)
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

    async def notify_start_transcrib(self, id, file_name):
        await self.bot.send_message(text=self.views.started_transcrib(filename=file_name), chat_id=id)

    async def add_file(self, user_id, options, input_path = ""):
        if not input_path:
            input_path = await self.transcriber_service.user_service.cash_repo.get_user_file(user_id)
        await self.bot.send_message(chat_id=user_id, text=f"Файл {os.path.basename(input_path)} добавлен в очередь")
        if input_path:
            await self.transcriber_service.prepare_transcription_request(
                options = options,
                file_path=input_path,
                user_id=user_id,
                callback=self.handle_transcription_result,
                notify_start_transcrib=self.notify_start_transcrib,
                on_insufficient_funds=lambda uid: self.bot.send_message(uid, self.views.top_up_balance_message()),
                on_wrong_format=lambda uid: self.bot.send_message(uid, self.views.file_format_error())
            )
        else:
            await self.bot.send_message(user_id, text="Сессия истекла, вышлите файл заново")

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
        # await callback.message.answer(f"Вы выбрали:\n\n{res}")

        await self.add_file(user_id=user_id, options=res)
    
    async def yandex_gpt_callback(self, callback, callback_data):
        user_id = callback.from_user.id
        filepath = callback_data.file_path
        if os.path.exists(filepath):
            task = callback_data.prompt
            if task == LLMPrompts.MAKE_POST_SHORT:
                prompt = LLMPrompts.MAKE_POST
            else:
                prompt = LLMPrompts.MAKE_SUMMARY
            result = self.transcriber_service.ai_service.generate_remote_api_answer(filepath, prompt)
            await self.bot.send_message(chat_id=user_id, text=result)
            print(filepath, task)
        else:
            await self.bot.send_message(chat_id=user_id, text="Сессия истекла, отправьте файл заново")


    async def handle_callback(self, callback):
        if callback.data.startswith("toggle:"):
            await self.handle_toggle_callback(callback=callback)
        else:
            # Универсальная попытка распарсить callback как GPTCallback
            gpt_data = None
            if isinstance(callback.data, str):
                try:
                    gpt_data = GPTCallback.unpack(callback.data)
                except Exception:
                    pass

            if gpt_data:
                await self.yandex_gpt_callback(callback=callback, callback_data=gpt_data)
            else:
                await self.handle_confirm_callback(callback=callback)


    async def dev_tests(self, message):
        users = await self.transcriber_service.user_service.get_all_users_id()
        for i in users:
            try:
                await self.bot.send_message(text = self.views.bot_update(), chat_id = i)
            except Exception:
                print(i)
        print(users)

    @check_user_registered
    async def handle_new_file(self, message):
        file_obj = message.audio or message.video or message.document or message.voice
        await self.bot.send_message(
                chat_id=message.from_user.id,  
                text=self.views.started_downloading()
            )
        try:
            file = await message.bot.get_file(file_obj.file_id, request_timeout = 300)

            local_file_path = file.file_path  

            user_path = await self.transcriber_service.get_user_path(
                base_path=self.config.DOWNLOADS_DIR, 
                user_adapter_id=message.from_user.id
            )

            if file_obj == message.voice:
                file_name = "Аудиосообщение_" + str(message.message_id) + os.path.splitext(local_file_path)[1]
            else:
                file_name = file_obj.file_name or os.path.basename(local_file_path)
            input_path = os.path.join(user_path, file_name)
            shutil.copy2(local_file_path, input_path)

            if not self.transcriber_service.queue.get_user_files_from_queue(message.from_user.id):
                await self.transcriber_service.user_service.cash_repo.remove_user_files(message.from_user.id)

            await self.transcriber_service.user_service.cash_repo.add_user_file(message.from_user.id, input_path)
            await self.show_options_keyboard(message=message, file_path=input_path)
        
        except Exception as err:
            print(err)
            await self.bot.send_message(
                chat_id=message.from_user.id,  
                text=self.views.downloading_error()
            )

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
        print(ai_jobs, file)
        # new_file = self.transcriber_service.file_service.create_random_copy(file)

        ai_service = self.transcriber_service.ai_service
        # collection_name = await asyncio.to_thread(partial(
        #     ai_service.make_embedding_collection,
        #     file_path = file
        # ))
        for prompt in ai_jobs:
            answer = self.transcriber_service.ai_service.generate_remote_api_answer(file, prompt)
            await self.bot.send_message(
                chat_id=user_id,  
                text=answer,
            )
            # answer = await asyncio.to_thread(partial(
            #     ai_service.generate_answer,
            #     prompt = prompt,
            #     collection_name = collection_name
            # ))
            # if prompt == LLMPrompts.MAKE_SUMMARY:
            #     p = LLMPrompts.MAKE_SUMMURY_SHORT
            # else:
            #     p = LLMPrompts.MAKE_POST_SHORT
            # await self.bot.send_message(
            #     chat_id=user_id,  
            #     text=answer,
            #     reply_markup=self.views.get_gpt_button(new_file, p)
            # )


        # ai_service.cleanup(collection_name)
        return 
        
    @check_user_registered
    async def handle_new_links(self, message):
        all_links = self.transcriber_service.link_service.parse_links(message.text)
        user_path = await self.transcriber_service.get_user_path(base_path=self.config.DOWNLOADS_DIR, 
                                                                 user_adapter_id=message.from_user.id)
        for link in all_links:
            await self.bot.send_message(chat_id = message.from_user.id, text = self.views.started_downloading())
            file = await asyncio.to_thread(partial(
                                            self.transcriber_service.link_service.download_link,
                                            link = link,
                                            download_dir = user_path
                                            ))
            await self.transcriber_service.user_service.cash_repo.add_user_file(message.from_user.id, file)
            await self.show_options_keyboard(message=message, file_path = file)

    async def support(self, message):
         await self.bot.send_message(chat_id = message.from_user.id, text = self.views.support())
