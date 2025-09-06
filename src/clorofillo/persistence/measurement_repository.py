from .orm_models import MeasurementORM
from .repository import Repository

class MeasurementRepository(Repository):
    def __init__(self, session):
        super().__init__(session, MeasurementORM)

    def get_by_id(self, entity_id):
        return self.session.query(self.entity).get(entity_id)

    def get_all(self):
        return self.session.query(self.entity).all()

    def insert(self, entity):
        self.session.add(entity)

    def remove(self, entity):
        self.session.delete(entity)
