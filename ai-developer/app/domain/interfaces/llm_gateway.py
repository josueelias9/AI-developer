from abc import ABC, abstractmethod

from ..entities.code_generation import CodeGenerationRequest, CodeGenerationResult


class ILLMGateway(ABC):
    @abstractmethod
    def generate(self, request: CodeGenerationRequest) -> CodeGenerationResult: ...
