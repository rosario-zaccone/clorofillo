from .orm_models import ConfigurationORM
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
        orm_obj.shot_freq = new_config.shot_freq
        orm_obj.insect_freq = new_config.insect_freq

        self.session.commit()
        return orm_obj
