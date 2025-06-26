from src.infrastructure.repositories.models import UserModel
from src.infrastructure.repositories.database import connection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, update
from sqlalchemy.exc import SQLAlchemyError
from .dto import UserAddDTO
from src.domain.entities import User

from src.domain.interfaces import IUserRepository

class SQLAlchemyUserRepository(IUserRepository):
    model = UserModel

    @connection
    async def select_user_by_id(self,  session: AsyncSession, id):
        query = select(self.model).where(self.model.telegram_id == id)
        result = await session.execute(query)
        records = result.scalars().first()
        return records

    @connection
    async def is_user(self,  session: AsyncSession, id):
        query = select(exists().where(self.model.telegram_id == id))
        result = await session.scalar(query)
        return result

    @connection
    async def add_user(self, user: User, session: AsyncSession):
        print(user)
        _user = UserAddDTO.model_validate(user)
        new_instance = self.model(**_user.model_dump())
        session.add(new_instance)
        try:
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            raise e
        return new_instance

    @connection
    async def update_payment_data(self,  session: AsyncSession, id, paid):
        stmt = update(self.model).where(self.model.telegram_id == id).values(paid=paid)
        await session.execute(stmt)
        await session.commit()

    @connection
    async def update_paid_minutes_data(cls,  session: AsyncSession, id, paid_minutes):
        stmt = update(cls.model).where(cls.model.telegram_id == id).values(paid_minutes=paid_minutes)
        await session.execute(stmt)
        await session.commit()

    @connection
    async def get_all_users_id(self,  session: AsyncSession):
        query = select(self.model.telegram_id)
        result = await session.execute(query)
        records = result.scalars().all()
        return records