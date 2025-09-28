from .orm_models import NotificationORM
from .repository import Repository

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class NotificationRepository(Repository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, NotificationORM)

    async def get_by_id(self, entity_id: int):
        result = await self.session.execute(select(self.entity).filter(self.entity.id == entity_id))
        return result.scalars().first()

    async def get_all(self):
        result = await self.session.execute(select(self.entity))
        return result.scalars().all()

    async def insert(self, entity):
        self.session.add(entity)
        await self.session.commit()

    async def remove(self, entity):
        self.session.delete(entity)
        await self.session.commit()


    async def get_not_notified(self):
        result = await self.session.execute(
            select(self.entity).filter(self.entity.is_notified == False)
        )
        # Usa .all() che restituisce una lista completa di oggetti
        notifications = await result.scalars().all()
        return notifications


    async def update_notified(self, entity_id: int):
        orm_obj = await self.get_by_id(entity_id)
        if not orm_obj:
            raise ValueError("Notification not found")
        orm_obj.is_notified = True
        await self.session.commit()
        return orm_obj
