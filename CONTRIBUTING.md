# Contributing

Thanks for your interest in contributing to this project.

## How to contribute

1. Fork the repository.
2. Create a feature branch.
3. Make your changes with clear commit messages.
4. Run validation locally.
5. Open a pull request with a concise summary.

## Local validation

```bash
python -m py_compile main.py
python -c "import fastapi, pydantic, requests; print('deps-ok')"
```

## Coding guidelines

- Keep code clean and readable.
- Add comments only where necessary.
- Avoid committing sensitive secrets or local environment values.
- Prefer small, focused pull requests.
