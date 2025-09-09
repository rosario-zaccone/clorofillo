# get timelapse
# get diario insetti

from clorofillo.persistence.plant_pot_repository import PlantPotRepository
# ricordati di aggiungere lòa tabella eventi/notifche per mntoficare seerbatoio vuoto e altra roba!!
class PlantPotService:
    def __init__(self, repository: PlantPotRepository):
        self.__repository = repository

    