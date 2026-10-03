# Front-End and Back-End Separation Calculator Backend

## Project Overview

This repository contains the backend API for a calculator system. The backend
validates expressions, parses and evaluates mathematical input, handles errors,
performs number base conversion, and persists calculation history in SQLite.

The front end communicates with this service only through HTTP JSON APIs.
Arithmetic evaluation is never performed by the front end.

## Technology Stack

- Python 3.10 or newer
- `http.server` for the HTTP API
- `sqlite3` for persistent storage
- `decimal` for precise arithmetic
- `unittest` for automated tests

No third-party packages or virtual environment are required.

## Features

- Addition, subtraction, multiplication, and division
- Operator precedence and parentheses
- Unary plus and minus
- Decimal arithmetic
- Invalid expression and division-by-zero handling
- Number base conversion for bases 2, 8, 10, and 16
- Persistent history in SQLite
- History search and pagination
- Delete a single history record
- Health check endpoint

## Runtime Environment

- Linux, macOS, or Windows
- Python 3.10 or newer
- Write access to the configured SQLite database directory

## Installation

No package installation is required.

```powershell
python --version
```

Expected version:

```text
Python 3.10 or newer
```

## Startup

Run the API from this repository directory:

```powershell
python -m app.server
```

The default address is:

```text
http://127.0.0.1:8000
```

The server creates the SQLite database table automatically when it starts.

## Configuration

The application reads configuration from process environment variables. It
does not automatically load a `.env` file. `.env.example` only documents the
available variables.

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_PATH` | `backend/data/calculator.db` | SQLite database file |
| `ALLOWED_ORIGINS` | Local front-end origins | Comma-separated allowed origins |
| `HOST` | `0.0.0.0` | HTTP listening address |
| `PORT` | `8000` | HTTP listening port |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Database Initialization

`Database.initialize()` creates `calculation_history` with these fields:

```text
id
expression
result
kind
created_at
```

The initialization routine also upgrades older databases by adding `kind`
when that column is missing.

The default database file is:

```text
backend/data/calculator.db
```

For a Linux server deployment, use an application-owned writable path such as:

```text
/opt/calculator/backend/data/calculator.db
```

## API Reference

### `POST /api/calculations`

Request:

```json
{"expression": "(1+2)*3"}
```

Successful response:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "expression": "(1+2)*3",
    "result": 9,
    "kind": "calculation",
    "createdAt": "2026-10-03T10:00:00Z"
  }
}
```

### `POST /api/conversions/base`

Request:

```json
{
  "value": "FF",
  "fromBase": 16,
  "toBase": 10
}
```

The result `"255"` is stored in history with `kind: "base"`.

### `GET /api/history`

Query parameters:

```text
page=1
pageSize=10
q=expression
```

The response contains `data` and `pagination`.

### `DELETE /api/history/{id}`

Returns `204 No Content` when the record is deleted.

### `GET /api/health`

Returns the backend and database health:

```json
{"success": true, "status": "ok"}
```

## Front-End Connection

The front end sends JSON requests to the API base URL. In the ECS deployment,
Nginx serves the static front end and proxies `/api/` to
`http://127.0.0.1:8000`.

## Testing

```powershell
python -m unittest discover -s tests -v
```

## ECS Deployment Notes

1. Install `git`, `nginx`, `sqlite3`, `curl`, and `ca-certificates`.
2. Run the backend as a `systemd` service.
3. Keep `HOST=127.0.0.1` and expose port `80` through Nginx.
4. Store SQLite at `/opt/calculator/backend/data/calculator.db`.
5. Use `ALLOWED_ORIGINS` for any front-end origin that uses a different host.
