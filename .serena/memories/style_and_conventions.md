## Code Style and Conventions
- Python code follows PEP 8 formatting with 4-space indentation, descriptive snake_case for functions/variables, and uppercase constants (e.g., `MODEL_PATH`).
- Heavy use of type hints and Pydantic models to validate API payloads; docstrings describe functions and endpoints.
- FastAPI endpoints return typed response models; prefer explicit error handling via `HTTPException`.
- Utility scripts use verbose console output and structured sections with ASCII separators for readability.
