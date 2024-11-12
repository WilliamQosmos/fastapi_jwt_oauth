from abc import abstractmethod
from typing import Protocol


class BaseDao(Protocol):
    @abstractmethod
    async def create(self, request):
        pass

    @abstractmethod
    async def get_by_id(self, id):
        pass

    @abstractmethod
    async def get_all(self):
        pass

    @abstractmethod
    async def delete_all(self):
        pass
