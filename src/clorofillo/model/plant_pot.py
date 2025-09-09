from .configuration import Configuration
from .plant_photo import PlantPhoto
from .measurement import Measurement
from clorofillo.persistence.orm_models import PlantPotORM

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

    @property
    def photos(self) -> list[PlantPhoto]:
        return self.__photos
    
    def add_photo(self, photo: PlantPhoto):
        self.photos.append(photo)
    
    def add_measurement(self, measurement: Measurement):
        self.measurements.append(measurement)

    @staticmethod
    def from_orm(orm_obj):
        return PlantPot(
            id=orm_obj.id,
            size=orm_obj.size,
            plant=orm_obj.plant,
            configuration=Configuration.from_orm(orm_obj.configuration) if orm_obj.configuration else None,
            measurements=[Measurement.from_orm(m) for m in orm_obj.measurements] if orm_obj.measurements else [],
            photos=[PlantPhoto.from_orm(p) for p in orm_obj.photos] if orm_obj.photos else []
        )

    def to_orm(self):
        orm = PlantPotORM(
            id=self.id,
            size=self.size,
            plant=self.plant
        )
        if self.configuration:
            orm.configuration = self.configuration.to_orm()
        if self.measurements:
            orm.measurements = [m.to_orm(plant_pot_id=self.id) for m in self.measurements]
        if self.photos:
            orm.photos = [p.to_orm(plant_pot_id=self.id) for p in self.photos]
        return orm