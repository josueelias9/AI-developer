from ...application.use_cases.generate_backend_code import GenerateBackendCodeUseCase


class CLIHandler:
    def __init__(self, use_case: GenerateBackendCodeUseCase, output_dir: str) -> None:
        self._use_case = use_case
        self._output_dir = output_dir

    def run(self) -> None:
        print("=" * 50)
        print("  AI Backend Code Generator")
        print(f"  Output directory: {self._output_dir}")
        print("  Type 'exit' to quit.")
        print("=" * 50)

        while True:
            print()
            try:
                prompt = input("Describe the backend to generate:\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not prompt:
                continue
            if prompt.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            print("\n[*] Generating code, please wait...\n")
            result = self._use_case.execute(prompt=prompt, output_dir=self._output_dir)

            if result.success:
                print(f"\n[OK] Done! {len(result.files)} file(s) generated:")
                for f in result.files:
                    print(f"  - {f.path}")
                if result.summary:
                    print(f"\nSummary:\n{result.summary}")
            else:
                print(f"\n[ERROR] Generation failed: {result.error}")

            print("\n" + "-" * 50)
