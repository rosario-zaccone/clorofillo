from datetime import datetime
from clorofillo.persistence.orm_models import MeasurementORM

class Measurement:
    def __init__(self, timestamp: datetime, soil_moisture: float, id: int = None):
        if not (0 <= soil_moisture <= 100):
            raise ValueError("soil_moisture must be between 0 and 100")
        self._id = id
        self._timestamp = timestamp
        self._soil_moisture = soil_moisture

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int):
        if value is not None and not isinstance(value, int):
            raise ValueError("id must be an integer or None.")
        self._id = value

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def soil_moisture(self) -> float:
        return self._soil_moisture

    @staticmethod
    def from_orm(orm_obj):
        return Measurement(
            timestamp=orm_obj.timestamp,
            soil_moisture=orm_obj.soil_moisture,
            id=getattr(orm_obj, 'id', None)
        )

    def to_orm(self, plant_pot_id=None):
        orm = MeasurementORM(
            timestamp=self.timestamp,
            soil_moisture=self.soil_moisture,
            plant_pot_id=plant_pot_id
        )
        if self.id is not None:
            orm.id = self.id
        return orm

    def __str__(self):
        return (
            f"Measurement(id={self.id}, "
            f"timestamp={self.timestamp}, "
            f"soil_moisture={self.soil_moisture})"
        )
