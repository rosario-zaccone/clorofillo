class Configuration:
    def __init__(self, threshold: float, watering_mode: bool, shot_freq: int, insect_freq: int, id: int = None):
        self.id = id
        self.threshold = threshold
        self.watering_mode = watering_mode
        self.shot_freq = shot_freq
        self.insect_freq = insect_freq

    @property
    def threshold(self):
        return self.__threshold

    @threshold.setter
    def threshold(self, value):
        if not isinstance(value, (float, int)):
            raise ValueError("Threshold must be a float or int.")
        value = float(value)
        if not (0.0 <= value <= 100.0):
            raise ValueError("Threshold must be between 0.0 and 100.0.")
        self.__threshold = value

    @property
    def watering_mode(self):
        return self.__watering_mode

    @watering_mode.setter
    def watering_mode(self, value):
        if not isinstance(value, bool):
            raise ValueError("Watering mode must be a boolean.")
        self.__watering_mode = value

    @property
    def shot_freq(self):
        return self.__shot_freq

    @shot_freq.setter
    def shot_freq(self, value):
        if not isinstance(value, int):
            raise ValueError("Shot frequency must be an integer.")
        if not (1 <= value <= 4):
            raise ValueError("Shot frequency must be between 1 and 4 shots per day.")
        self.__shot_freq = value

    @property
    def insect_freq(self):
        return self.__insect_freq

    @insect_freq.setter
    def insect_freq(self, value):
        if not isinstance(value, int):
            raise ValueError("Insect frequency must be an integer.")
        if not (5 <= value <= 15):
            raise ValueError("Insect frequency must be between 5 and 15 seconds.")
        self.__insect_freq = value

    @staticmethod
    def from_orm(orm_obj):
        return Configuration(
            threshold=orm_obj.threshold,
            watering_mode=orm_obj.watering_mode,
            shot_freq=orm_obj.shot_freq,
            insect_freq=orm_obj.insect_freq,
            id=getattr(orm_obj, 'id', None)
        )

    def to_orm(self):
        from persistence.configuration_orm import ConfigurationORM  # aggiorna il path se necessario
        orm = ConfigurationORM(
            threshold=self.threshold,
            watering_mode=self.watering_mode,
            shot_freq=self.shot_freq,
            insect_freq=self.insect_freq
        )
        # Solo se l'id esiste (ad esempio per update), lo setto. Altrimenti lo gestisce il DB.
        if self.id is not None:
            orm.id = self.id
        return orm