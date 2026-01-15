from .orm_models import ConfigurationORM, ShotTimeORM
from .repository import Repository

class ConfigurationRepository(Repository):
    def __init__(self, session):
        super().__init__(session, ConfigurationORM)

    def get_by_id(self, entity_id):
        return self.session.get(self.entity, entity_id)


    def get_all(self):
        return self.session.query(self.entity).all()

    def insert(self, entity):
        self.session.add(entity)

    def remove(self, entity):
        self.session.delete(entity)
    
    def update(self, entity_id, new_config):
        orm_obj = self.get_by_id(entity_id)
        if not orm_obj:
            raise ValueError("Configuration not found")

        orm_obj.threshold = new_config.threshold
        orm_obj.watering_mode = new_config.watering_mode
        orm_obj.sighting_freq = new_config.sighting_freq
        orm_obj.position = new_config.position
        orm_obj.plant = new_config.plant
        orm_obj.size = new_config.size
        orm_obj.shot_freq = [
            ShotTimeORM(hour=t.hour, minute=t.minute) for t in new_config.shot_freq
        ]

        self.session.commit()
        return orm_obj
