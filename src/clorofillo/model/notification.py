from datetime import datetime
from clorofillo.persistence.orm_models import NotificationORM

class Notification:
    def __init__(self, id, timestamp, pot, description):
        self.__id = id
        self.__timestamp = timestamp
        self.__pot = pot
        self.__description = description
    
    @property
    def id(self):
        return self.__id

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def pot(self):
        return self.__pot

    @property
    def description(self):
        return self.__description
    
    @staticmethod
    def from_orm(orm_obj):
        return Notification(
            id=orm_obj.id,
            timestamp=orm_obj.timestamp,
            pot=orm_obj.pot,
            description=orm_obj.description
        )

    
    def to_orm(self, plant_pot_id=None):
        orm = NotificationORM(
            id=self.id,
            timestamp=self.timestamp,
            pot=self.pot,
            description = self.description
        )
        return orm

