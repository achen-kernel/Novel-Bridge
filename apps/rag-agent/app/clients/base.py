from abc import ABC, abstractmethod


class BaseClient(ABC):
    @abstractmethod
    async def health_check(self) -> dict:
        ...
