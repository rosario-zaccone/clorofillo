from datetime import datetime
from photo_type import PhotoType

class PlantPhoto:
    def __init__(self, timestamp: datetime, type: PhotoType, path: str):
        self.__timestamp = timestamp
        self.__type = type
        self.__path = path

    @property
    def timestamp(self) -> datetime:
        return self.__timestamp

    @property
    def type(self) -> PhotoType:
        return self.__type

    @property
    def path(self) -> str:
        return self.__path
