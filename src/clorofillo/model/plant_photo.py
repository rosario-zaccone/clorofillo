from datetime import datetime
from .photo_type import PhotoType

class PlantPhoto:
    def __init__(self, timestamp: datetime, photo_type: PhotoType, path: str):
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
