from datetime import datetime
from clorofillo.persistence.orm_models import NotificationORM

class Notification:
    def __init__(self, timestamp: datetime, is_notified: bool, description: str, id: int = None):
        self._id = id
        self.timestamp = timestamp
        self.is_notified = is_notified
        self.description = description

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value: int):
        if value is not None and not isinstance(value, int):
            raise ValueError("id must be an integer or None.")
        self._id = value

    @staticmethod
    def from_orm(orm_obj):
        return Notification(
            id=orm_obj.id,
            timestamp=orm_obj.timestamp,
            is_notified = orm_obj.is_notified,
            description=orm_obj.description
        )

    def to_orm(self):
        orm = NotificationORM(
            timestamp=self.timestamp,
            is_notified=self.is_notified,
            description=self.description
        )
        if self.id is not None:
            orm.id = self.id
        return orm

    def __str__(self):
        return (
            f"Notification(id={self.id}, "
            f"timestamp={self.timestamp}, "
            f"is_notified={self.is_notified}, "
            f"description={self.description})"
        )
