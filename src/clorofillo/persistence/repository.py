from abc import ABC, abstractmethod

class Repository(ABC):
    def __init__(self, session, entity):
        self._session = session
        self._entity = entity

    @property
    def entity(self):
        return self._entity
    @property
    def session(self):
        return self._session

    @abstractmethod
    def get_by_id(self, entity_id):
        pass

    @abstractmethod
    def get_all(self):
        pass

    @abstractmethod
    def insert(self, entity):
        pass

    @abstractmethod
    def remove(self, entity):
        pass
