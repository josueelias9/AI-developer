from ...domain.entities.code_generation import CodeGenerationRequest, CodeGenerationResult
from ...domain.interfaces.llm_gateway import ILLMGateway


class GenerateBackendCodeUseCase:
    def __init__(self, llm_gateway: ILLMGateway) -> None:
        self._llm_gateway = llm_gateway

    def execute(self, prompt: str, output_dir: str = ".") -> CodeGenerationResult:
        request = CodeGenerationRequest(prompt=prompt, output_dir=output_dir)
        return self._llm_gateway.generate(request)
