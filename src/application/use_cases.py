from typing import List, Optional
import asyncio
import os
from functools import partial
from collections import deque, defaultdict

from src.domain.interfaces import IUserRepository, ITranscriber, IFileService, ILinkService, IAIService, ICashUserRepository
from src.domain.entities import User, QueueElement
from src.domain.constants import AudioExtensions, VideoExtensions, ResultExtensions, LLMPrompts


class UserService:
    def __init__(self, repo: IUserRepository, cash_repo: ICashUserRepository):
        self.repo = repo
        self.cash_repo = cash_repo

    async def add_user(self, id, paid=False, paid_minutes=0):
        user = User(telegram_id=id, paid=paid, paid_minutes=paid_minutes)
        await self.repo.add_user(user)

    async def is_user(self, id):
        cashed = await self.cash_repo.is_user(id)
        if cashed:
            return cashed
        is_exists = await self.repo.is_user(id=id)
        await self.cash_repo.add_user(id)
        return is_exists
    
    async def get_paid_minutes(self, id):
        user = await self.repo.select_user_by_id(id=id)
        minutes = User.model_validate(user).paid_minutes
        return minutes
    
    async def get_user_id(self, adapter_id):
        cashed = await self.cash_repo.get_user_id(adapter_id)
        if cashed:
            return int(cashed)
        user = await self.repo.select_user_by_id(id=adapter_id)
        id = User.model_validate(user).id
        await self.cash_repo.set_user_id(adapter_id=adapter_id,
                                   id=id)
        return id
    
    async def get_all_users_id(self):
        ids = await self.repo.get_all_users_id()
        return ids
    
    
class FilesQueue:
    def __init__(self):
        self.user_queues = defaultdict(deque) 
        self.user_order = deque()              
        self.lock = asyncio.Lock()
        self.not_empty = asyncio.Condition()
        self.current_file = None

    async def add_file_to_queue(self, queue_element: QueueElement):
        async with self.lock:
            user_id = queue_element.user_id
            if not self.user_queues[user_id]:
                self.user_order.append(user_id)  
            self.user_queues[user_id].append(queue_element)

        async with self.not_empty:
            self.not_empty.notify()

    async def get_file_from_queue(self) -> Optional[QueueElement]:
        async with self.not_empty:
            await self.not_empty.wait_for(lambda: any(self.user_queues.values()))

        async with self.lock:
            if not self.user_order:
                return None

            for _ in range(len(self.user_order)):
                user_id = self.user_order.popleft()
                if self.user_queues[user_id]:
                    element = self.user_queues[user_id].popleft()
                    if self.user_queues[user_id]:
                        self.user_order.append(user_id)
                    else:
                        del self.user_queues[user_id] 
                    return element
            return None
        
    async def get_position(self, user_id: int, file_path: str) -> Optional[int]:
        async with self.lock:
            position = 0

            temp_queues = {uid: deque(q) for uid, q in self.user_queues.items()}
            temp_user_order = deque(self.user_order)

            while temp_user_order:
                uid = temp_user_order.popleft()
                if temp_queues[uid]:
                    element = temp_queues[uid].popleft()
                    if element.user_id == user_id and element.file_path == file_path:
                        return position
                    position += 1
                    if temp_queues[uid]:
                        temp_user_order.append(uid)
            return None  
        
    def get_user_files_from_queue(self, user_id: int):
        return self.user_queues[user_id]

    
class ApplicationService:
    def __init__(self, service: ITranscriber, 
                 file_service: IFileService, 
                 user_service: UserService, 
                 queue: FilesQueue, 
                 link_service: ILinkService,
                 ai_service: IAIService,
                 config):
        self.service = service
        self.file_service = file_service
        self.user_service = user_service
        self.link_service = link_service
        self.queue = queue
        self.ai_service = ai_service
        self.config = config
        self.transcripts_path = config.TRANSCRIPTS_DIR
    
    async def transcribe(self, file_path, user_adapter_id, delete_input_file=False, needed_formats = []):
        if not self.is_extension_correct(file_path):
            self.file_service.delete_files(file_path)
            return None
        wav_filepath = self.file_service.covert_media_to_wav(filepath=file_path)
        path_to_transcrib = await self.get_user_path(user_adapter_id=user_adapter_id, base_path=self.transcripts_path)
        self.service.set_transcrib_path(path_to_transcrib)
        result = await asyncio.to_thread(partial(
                                self.service.transcribe,
                                file_path = wav_filepath
                                    ))
        if delete_input_file:
            self.file_service.delete_files(wav_filepath)
        all_files = self.prepare_needed_fromats(base_file=result, formats=needed_formats)
        return all_files
    
    def prepare_needed_fromats(self, base_file, formats=[]):
        all_files = [base_file]
        for ext in formats:
            new_file = self.file_service.convert_txt_to_ext(base_file, ext)
            if new_file:
                all_files.append(new_file)
        return all_files

    def is_extension_correct(self, filepath):
        ext = filepath.split('.')[-1].lower()
        supported = {e.value for e in (*AudioExtensions, *VideoExtensions)}
        return ext in supported
    
    async def prepare_transcription_request(self, options, file_path: str, user_id: int, callback: callable, notify_start_transcrib: callable, on_insufficient_funds: callable, on_wrong_format: callable):
        if not self.is_extension_correct(file_path):
            await on_wrong_format(user_id)
            return
        file_duration = self.file_service.get_media_duration(file_path)
        paid_minutes = await self.user_service.get_paid_minutes(id=user_id)
        # if paid_minutes < file_duration:
        #     await on_insufficient_funds(user_id)
        #     self.file_service.delete_files(file_path)
        #     return
        queue_element = QueueElement(user_id=user_id, 
                                     file_path=file_path, 
                                     callback=callback, 
                                     notify_start_transcrib=notify_start_transcrib,
                                     options=options)
        await self.queue.add_file_to_queue(queue_element)

    async def get_user_path(self, user_adapter_id: int, base_path: str):
        user_id = await self.user_service.get_user_id(user_adapter_id)
        path = self.file_service.add_directory(base_path, str(user_id))
        return path


class TranscriberQueueProcessor:
    def __init__(self, transcriber_service: ApplicationService):
        self.application_service = transcriber_service
        self.files_queue : FilesQueue = self.application_service.queue
        self.user_service : UserService = self.application_service.user_service
        self.running = False
        self.active_tasks = 0
        self.task_lock = asyncio.Lock()

    async def monitor_queue(self):
        while self.running:
            await asyncio.sleep(1800) 
            async with self.files_queue.lock:
                is_empty = not any(self.files_queue.user_queues.values())
            
            async with self.task_lock:
                no_active_tasks = self.active_tasks == 0

            if is_empty and no_active_tasks:
                self.application_service.file_service.delete_all_from_folders(self.application_service.config.DOWNLOADS_DIR,
                                                                              self.application_service.config.TRANSCRIPTS_DIR)

    async def start(self):
        self.running = True
        monitor_task = asyncio.create_task(self.monitor_queue())
        while self.running:
            queue_item : QueueElement = await self.files_queue.get_file_from_queue()
            if queue_item is None:
                await asyncio.sleep(0.5)
                continue
            try:
                async with self.task_lock:
                    self.active_tasks += 1
                await queue_item.notify_start_transcrib(id = queue_item.user_id, file_name = os.path.basename(queue_item.file_path))
                self.files_queue.current_file = queue_item
                output_files = await self.application_service.transcribe(file_path=queue_item.file_path,
                                                            delete_input_file = True,
                                                            user_adapter_id = queue_item.user_id,
                                                            needed_formats = queue_item.options["formats"])
                await queue_item.callback(output_files, None, queue_item.user_id, ai_jobs = queue_item.options["prompts"])
            except Exception as e:
                 await queue_item.callback(None, e, queue_item.user_id)
            finally:
                async with self.task_lock:
                    self.active_tasks -= 1
        monitor_task.cancel()

    def stop(self):
        self.running = False


