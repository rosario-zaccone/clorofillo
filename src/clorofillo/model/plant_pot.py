from .configuration import Configuration
from .photo_type import PhotoType
from .plant_photo import PlantPhoto
from .measurement import Measurement

class PlantPot:
    def __init__(self, id: int, size: float, plant: str, configuration: Configuration,
                 measurements: list[Measurement], photos: list[PlantPhoto]):
        self.__id = id
        self.__size = size
        self.__plant = plant
        self.__configuration = configuration
        self.__measurements = measurements
        self.__photos = photos

    @property
    def id(self) -> int:
        return self.__id

    @property
    def size(self) -> float:
        return self.__size

    @size.setter
    def size(self, value: float):
        self.__size = value

    @property
    def plant(self) -> str:
        return self.__plant

    @plant.setter
    def plant(self, value: str):
        self.__plant = value

    @property
    def configuration(self) -> Configuration:
        return self.__configuration

    @configuration.setter
    def configuration(self, value: Configuration):
        self.__configuration = value

    @property
    def measurements(self) -> list[Measurement]:
        return self.__measurements

    def get_timelapse_photos(self) -> list[PlantPhoto]:
        return [photo for photo in self.__photos if photo.photo_type == PhotoType.TIMELAPSE]
    
    def get_insect_photos(self) -> list[PlantPhoto]:
        return [photo for photo in self.__photos if photo.photo_type == PhotoType.INSECT]
    
    def get_flower_photos(self) -> list[PlantPhoto]:
        return [photo for photo in self.__photos if photo.photo_type == PhotoType.FLOWER]
