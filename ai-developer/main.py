import os

from src.frameworks.repositories.file_code_repository import FileCodeRepository
from src.frameworks.llm.ollama_agent import OllamaAgentGateway
from src.application.use_cases.generate_backend_code import GenerateBackendCodeUseCase
from src.frameworks.cli.cli_handler import CLIHandler


def main() -> None:

    os.makedirs(os.getenv("OUTPUT_DIR"), exist_ok=True)

    llm_gateway = OllamaAgentGateway(
        base_url=os.getenv("OLLAMA_HOST"),
        model=os.getenv("OLLAMA_MODEL"),
        coder_model=os.getenv("OLLAMA_CODER"),
        code_repository=FileCodeRepository(),
    )
    use_case = GenerateBackendCodeUseCase(llm_gateway=llm_gateway)
    cli = CLIHandler(use_case=use_case, output_dir=os.getenv("OUTPUT_DIR"))

    cli.run()


if __name__ == "__main__":
    main()
