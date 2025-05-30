from abc import ABC, abstractmethod
from typing import List
from .entities import User

class IUserRepository(ABC):
    @abstractmethod
    async def select_user_by_id(self, id) -> User: pass

    @abstractmethod
    async def is_user(self, id) -> bool: pass

    @abstractmethod
    async def add_user(self, user: User) -> User: pass

    @abstractmethod
    async def update_payment_data(self, id, paid) -> bool: pass

    @abstractmethod
    async def update_paid_minutes_data(self, id, paid_minutes) -> bool: pass


class ICashUserRepository(ABC):
    @abstractmethod
    async def set_user_selection(self, user_id, selection):
        pass

    @abstractmethod
    async def get_user_selection(self, user_id):
        pass

    @abstractmethod    
    async def set_user_selection_value(self, user_id, key, value):
        pass

    @abstractmethod
    async def get_user_id(self, adapter_id) -> str: pass
    
    @abstractmethod
    async def is_user(self, id) -> bool: pass

    @abstractmethod
    async def add_user(self, id): pass

    @abstractmethod
    async def set_user_id(self, adapter_id, id): pass

    @abstractmethod
    async def add_user_file(self, user_id, file_path):
        pass
    
    @abstractmethod
    async def get_user_file(self, user_id):
        pass

    @abstractmethod
    async def remove_user_files(self, user_id): pass



class ITranscriber(ABC):
    @abstractmethod
    def transcribe(self, file_path: str) ->  str: pass

    @abstractmethod
    def set_transcrib_path(path: str) -> str: pass


class IFileService(ABC):
    @classmethod
    @abstractmethod
    def delete_files(cls, *files) ->  bool: pass

    @classmethod
    @abstractmethod
    def delete_all_from_folders(cls, *folders: str) -> bool: pass

    @classmethod
    @abstractmethod
    def covert_media_to_wav(cls, filepath: str) ->  str: pass

    @classmethod
    @abstractmethod
    def get_media_duration(cls, file_path: str) ->  int: pass

    @classmethod
    @abstractmethod
    def add_directory(cls, base_path : str, path : str) -> str: pass

    @classmethod
    @abstractmethod
    def convert_txt_to_ext(cls, txt_path : str, ext : str) -> str | None: pass


class ILinkService(ABC):

    @classmethod
    @abstractmethod
    def parse_links(cls, raw_links: str) ->  List[str]: pass

    @classmethod
    @abstractmethod
    def download_link(cls, link: str, download_dir: str) ->  str: pass

class IMessageService(ABC):
    @abstractmethod
    async def send_message(self, id : int, message: str) -> bool: pass


class IAIService(ABC):
    @abstractmethod
    def make_embedding_collection(self, file_path: str) -> str:
        """Загружает текст из файла и создает эмбеддинги."""
        pass

    @abstractmethod
    def generate_answer(self, prompt: str, collection_name: str) -> str:
        """Генерирует ответ на основе подготовленных данных."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Освобождает ресурсы (например, удаляет коллекцию ChromaDB)."""
        pass





