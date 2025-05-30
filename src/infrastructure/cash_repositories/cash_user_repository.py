import redis.asyncio as redis
from .redis_connection import pool
from src.domain.interfaces import ICashUserRepository

class CashUserRepository(ICashUserRepository):
    DEFAULT_TTL = 86400
    FILE_PATH_TTL = 120

    def __init__(self):
        self.r = redis.Redis(connection_pool=pool)

    async def set_user_selection(self, user_id, selection):
        for key, value in selection.items():
            await self.r.hset(f"user:{user_id}:selection", key, str(value).lower())
        await self.r.expire(f"user:{user_id}:selection", self.DEFAULT_TTL)

    async def get_user_selection(self, user_id):
        selection = await self.r.hgetall(f"user:{user_id}:selection")
        await self.r.expire(f"user:{user_id}:selection", self.DEFAULT_TTL)
        return {k.decode(): v.decode() == 'true' for k, v in selection.items()}

    async def set_user_selection_value(self, user_id, key, value):
        await self.r.hset(f"user:{user_id}:selection", key, str(value).lower())
        await self.r.expire(f"user:{user_id}:selection", self.DEFAULT_TTL)

    async def add_user_file(self, user_id, file_path):
        await self.r.rpush(f'user:{user_id}:files', file_path)
        await self.r.expire(f"user:{user_id}:files", self.DEFAULT_TTL)

    async def get_user_file(self, user_id):
        res = await self.r.lpop(f"user:{user_id}:files")
        if res:
            return res.decode()
        return res
    
    async def remove_user_files(self, user_id):
        await self.r.delete(f"user:{user_id}:files")






    async def get_user_id(self, adapter_id):
        res = await self.r.get(f'user{adapter_id}:id')
        return res

    async def is_user(self, id):
        res = await self.r.get(f'user{id}:exists')
        return res
    
    async def add_user(self, id):
        await self.r.set(f'user{id}:exists', 'true', ex = self.DEFAULT_TTL)

    async def set_user_id(self, adapter_id, id):
        await self.r.set(f'user{adapter_id}:id', str(id), ex = self.DEFAULT_TTL)
    

