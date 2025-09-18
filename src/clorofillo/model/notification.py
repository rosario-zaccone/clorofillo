from datetime import datetime
from clorofillo.persistence.orm_models import NotificationORM

class Notification:
    def __init__(self, id, timestamp, pot, description):
        self._id = id
        self._timestamp = timestamp
        self._pot = pot
        self._description = description
    
    @property
    def id(self):
        return self._id

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def pot(self):
        return self._pot

    @property
    def description(self):
        return self._description
    
    @staticmethod
    def from_orm(orm_obj):
        return Notification(
            id=orm_obj.id,
            timestamp=orm_obj.timestamp,
            pot=orm_obj.pot,
            description=orm_obj.description
        )

    
    def to_orm(self):
        orm = NotificationORM(
            id=self.id,
            timestamp=self.timestamp,
            pot=self.pot,
            description = self.description
        )
        return orm

