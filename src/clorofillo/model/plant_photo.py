from datetime import datetime
from enum import Enum

class PhotoType(Enum):
    TIMELAPSE = "timelapse"
    INSECT = "insect"
    FLOWER = "flower"

class PlantPhoto:
    def __init__(self, timestamp: datetime, photo_type: PhotoType, path: str, id: int = None):
        self.id = id
        self.__timestamp = timestamp
        self.__photo_type = photo_type
        self.__path = path

    @property
    def timestamp(self) -> datetime:
        return self.__timestamp

    @property
    def photo_type(self) -> PhotoType:
        return self.__photo_type

    @property
    def path(self) -> str:
        return self.__path

    @staticmethod
    def from_orm(orm_obj):
        return PlantPhoto(
            timestamp=orm_obj.timestamp,
            photo_type=PhotoType(orm_obj.photo_type),
            path=orm_obj.path,
            id=getattr(orm_obj, 'id', None)
        )

    def to_orm(self, plant_pot_id=None):
        from persistence.plant_photo_orm import PlantPhotoORM  # aggiorna il path se necessario
        orm = PlantPhotoORM(
            timestamp=self.timestamp,
            photo_type=self.photo_type.value,
            path=self.path,
            plant_pot_id=plant_pot_id
        )
        if self.id is not None:
            orm.id = self.id
        return orm