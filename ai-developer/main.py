import os

from app.infrastructure.repositories.file_code_repository import FileCodeRepository
from app.infrastructure.llm.ollama_agent import OllamaAgentGateway
from app.application.use_cases.generate_backend_code import GenerateBackendCodeUseCase
from app.interfaces.cli.cli_handler import CLIHandler


def main() -> None:
    base_url = os.getenv("OLLAMA_HOST")
    model = os.getenv("OLLAMA_MODEL")
    output_dir = os.getenv("OUTPUT_DIR")

    os.makedirs(output_dir, exist_ok=True)

    code_repository = FileCodeRepository()
    llm_gateway = OllamaAgentGateway(
        base_url=base_url,
        model=model,
        code_repository=code_repository,
    )
    use_case = GenerateBackendCodeUseCase(llm_gateway=llm_gateway)
    cli = CLIHandler(use_case=use_case, output_dir=output_dir)

    cli.run()


if __name__ == "__main__":
    main()
