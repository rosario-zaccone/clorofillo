from clorofillo.persistence.orm_models import PlantPotORM, PlantPhotoORM
from clorofillo.persistence.repository import Repository
from datetime import datetime

class PlantPotRepository(Repository):
    def __init__(self, session):
        super().__init__(session, PlantPotORM)

    def get_by_id(self, entity_id):
        return self.session.query(self.entity).get(entity_id)

    def get_all(self):
        return self.session.query(self.entity).all()

    def insert(self, entity):
        self.session.add(entity)

    def remove(self, entity):
        self.session.delete(entity)
    
    def get_photos_by_date_range(self, plant_pot_id: int, date_from: datetime, date_to: datetime):
        if date_to < date_from:
            raise ValueError(f"Invalid date range: date_to ({date_to}) is before date_from ({date_from})")

        return (
            self.session.query(PlantPhotoORM)
            .filter(PlantPhotoORM.plant_pot_id == plant_pot_id)
            .filter(PlantPhotoORM.timestamp >= date_from)
            .filter(PlantPhotoORM.timestamp <= date_to)
            .filter(PlantPhotoORM.is_insect == False)
            .order_by(PlantPhotoORM.timestamp.asc())
            .all()
        )
