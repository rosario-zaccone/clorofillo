from clorofillo.persistence.orm_models import ShotTimeORM
from clorofillo.persistence.orm_models import ConfigurationORM 
from datetime import time

class Configuration:
    def __init__(self, threshold: float, watering_mode: bool, shot_freq: list, insect_freq: int, position: int, size: float, plant: str, id: int = None):
        self._id = id
        self.threshold = threshold
        self.watering_mode = watering_mode
        self.shot_freq = shot_freq
        self.insect_freq = insect_freq
        self.position = position
        self.size = size
        self.plant = plant

    @property
    def id(self):
        return self._id
    @property
    def size(self):
        return self._size
    
    @size.setter
    def size(self, value):
        if not isinstance(value, (float, int)):
            raise ValueError("Size must be a float or int.")
        value = float(value)
        if value <= 0.0:
            raise ValueError("Size must be positive.")
        self._size = value


    @property
    def threshold(self):
        return self._threshold
    
    @threshold.setter
    def threshold(self, value):
        if not isinstance(value, (float, int)):
            raise ValueError("Threshold must be a float or int.")
        value = float(value)
        if not (0.0 <= value <= 100.0):
            raise ValueError("Threshold must be between 0.0 and 100.0.")
        self._threshold = value

    @property
    def watering_mode(self):
        return self._watering_mode
    
    @watering_mode.setter
    def watering_mode(self, value):
        if not isinstance(value, bool):
            raise ValueError("Watering mode must be a boolean.")
        self._watering_mode = value

    @property
    def shot_freq(self):
        return self._shot_freq
    

    @shot_freq.setter
    def shot_freq(self, value):
        if not isinstance(value, list):
            raise ValueError("Shot frequency must be a list of time strings (HH:MM).")

        if len(value) > 24:
            raise ValueError("Maximum 24 shot times allowed.")

        shot_times = []

        for t in value:
            if not isinstance(t, str):
                raise ValueError("Each shot time must be a string in HH:MM format.")

            try:
                h, m = map(int, t.split(":"))
                shot_times.append(time(hour=h, minute=m))
            except Exception:
                raise ValueError(f"Invalid time format: {t}. Expected HH:MM.")

        self._shot_freq = shot_times


    @property
    def insect_freq(self):
        return self._insect_freq
    
    @insect_freq.setter
    def insect_freq(self, value):
        if not isinstance(value, int):
            raise ValueError("Insect frequency must be an integer.")
        if not (value==0 or 3 <= value <= 12):
            raise ValueError("Insect frequency must be 0 or between 3 and 12 shots per minute.")
        self._insect_freq = value

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        if value < 0 or value > 180:
            raise ValueError("Invalid angle.")
        self._position = value

    @staticmethod
    def from_orm(orm_obj: ConfigurationORM):
        shot_list = [f"{st.hour:02d}:{st.minute:02d}" for st in orm_obj.shot_freq]
        return Configuration(
            threshold=orm_obj.threshold,
            watering_mode=orm_obj.watering_mode,
            shot_freq=shot_list,
            insect_freq=orm_obj.insect_freq,
            position=orm_obj.position,
            size=orm_obj.size,
            plant=orm_obj.plant,
            id=getattr(orm_obj, 'id', None)
        )

    def to_orm(self):
        orm = ConfigurationORM(
            threshold=self.threshold,
            watering_mode=self.watering_mode,
            insect_freq=self.insect_freq,
            position=self.position,
            size=self.size,
            plant=self.plant
        )
        orm.shot_freq = [ShotTimeORM(hour=t.hour, minute=t.minute) for t in self.shot_freq]
        if self._id is not None:
            orm.id = self._id
        return orm

    def __str__(self):
        return (
            f"Configuration(id={self._id}, "
            f"threshold={self.threshold}, "
            f"watering_mode={self.watering_mode}, "
            f"shot_freq={self.shot_freq}, "
            f"insect_freq={self.insect_freq},"
            f"position={self.position})"
        )
