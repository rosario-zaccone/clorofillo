from datetime import datetime
from clorofillo.persistence.orm_models import PlantPhotoORM

class PlantPhoto:
    def __init__(self, timestamp: datetime, is_insect: bool, path: str, id: int = None):
        self._id = id
        self.timestamp = timestamp
        self.is_insect = is_insect
        self.path = path

    @property
    def id(self):
        return self._id


    @staticmethod
    def from_orm(orm_obj):
        return PlantPhoto(
            timestamp=orm_obj.timestamp,
            is_insect=orm_obj.is_insect,
            path=orm_obj.path,
            id=getattr(orm_obj, 'id', None)
        )

    def to_orm(self, plant_pot_id=None):
        orm = PlantPhotoORM(
            timestamp=self.timestamp,
            is_insect=self.is_insect,
            path=self.path,
            plant_pot_id=plant_pot_id
        )
        if self.id is not None:
            orm.id = self.id
        return orm
