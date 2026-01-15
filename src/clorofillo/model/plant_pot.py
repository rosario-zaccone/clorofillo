from .configuration import Configuration
from .plant_photo import PlantPhoto
from clorofillo.persistence.orm_models import PlantPotORM

class PlantPot:
    def __init__(self, id: int, configuration: Configuration, photos: list[PlantPhoto]):
        self._id = id
        self.configuration = configuration
        self.photos = photos

    @property
    def id(self) -> int:
        return self._id
    
    def get_sighting_photos(self):
        return filter(lambda x: x.is_sighting, self.photos)

    @staticmethod
    def from_orm(orm_obj):
        return PlantPot(
            id=orm_obj.id,
            configuration=Configuration.from_orm(orm_obj.configuration) if orm_obj.configuration else None,
            photos=[PlantPhoto.from_orm(p) for p in orm_obj.photos] if orm_obj.photos else []
        )

    def to_orm(self):
        orm = PlantPotORM(
            id=self.id
        )
        if self.configuration:
            orm.configuration = self.configuration.to_orm()
        if self.photos:
            orm.photos = [p.to_orm(plant_pot_id=self.id) for p in self.photos]
        return orm
    
    def __str__(self):
        return (
            f"PlantPot(id={self.id},"
            f"configuration={self.configuration}, "
            f"photos_count={len(self.photos)})"
        )