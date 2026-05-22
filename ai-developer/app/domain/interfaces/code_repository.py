from abc import ABC, abstractmethod
from typing import List

from ..entities.code_generation import GeneratedFile


class ICodeRepository(ABC):
    @abstractmethod
    def save(self, file: GeneratedFile, base_dir: str) -> str:
        ...

    @abstractmethod
    def read(self, path: str) -> str:
        ...

    @abstractmethod
    def list_files(self, directory: str) -> List[str]:
        ...
