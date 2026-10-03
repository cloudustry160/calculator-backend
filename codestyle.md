# Backend Code Style

## Standard Sources

This document follows [PEP 8](https://peps.python.org/pep-0008/) and the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

## General Rules

- Use four spaces per indentation level.
- Do not use tab characters.
- Keep each line at or below 88 characters where practical.
- Use `snake_case` for modules, functions, and variables.
- Use `PascalCase` for classes.
- Group imports in this order: standard library, then application modules.
- Add type annotations to public functions and complex logic.
- Keep user-facing error messages in one place for each API module.

## API and Data

- Build responses through `ApiResponse`.
- Keep response fields stable: `success`, `data`, `pagination`, and `message`.
- Use `dataclass` or explicit dictionaries for structured records.
- Validate request types before parsing values.
- Return an appropriate HTTP status code for success and failure.

## Database Rules

- Perform all database operations through the `Database` class.
- Use parameterized SQL statements.
- Open a separate SQLite connection for each operation.
- Keep schema migration logic idempotent.
- Never construct SQL with user input.

## Security Rules

- Do not use `eval`, `exec`, or equivalent arbitrary-code execution.
- Parse expressions with the project parser.
- Validate conversion bases, input lengths, digits, and numeric ranges.
- Do not trust values received from the front end.

## Testing

Run the full test suite before committing:

```powershell
python -m unittest discover -s tests -v
```

Add tests for new API behavior, validation failures, database migrations, and
persistence behavior.
