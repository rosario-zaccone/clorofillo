from datetime import datetime

class Measurement:
    def __init__(self, timestamp: datetime, soil_moisture: float):
        if not (0 <= soil_moisture <= 100):
            raise ValueError("soil_moisture must be between 0 and 100")
        self._timestamp = timestamp
        self._soil_moisture = soil_moisture

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def soil_moisture(self) -> float:
        return self._soil_moisture
