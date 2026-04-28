# ey-cohort-12

## Backend — WO-2 (Project scaffolding & core configuration)

Runnable FastAPI skeleton aligned with the **Backend** blueprint and WO-2:

| Area | Implementation |
|------|----------------|
| **Structure** | Versioned routes under `/api/v1/` (`health`, `common`, `integrations`), optional domain routers |
| **JWT (Entra ID)** | Bearer validation via JWKS (`ENTRA_TENANT_ID`, `ENTRA_AUDIENCE`, optional `ENTRA_ISSUER`); `get_current_user`; `require_roles(...)` |
| **Rate limiting** | `slowapi` + custom key (Bearer `sub` when present, else IP) |
| **CORS** | Configurable origins (Angular `:4200` included in defaults) |
| **Logging** | `structlog` JSON logs + `RequestIdMiddleware` (`X-Request-ID`) |
| **Redis** | Async client on `app.state.redis`; dependency `get_redis`; disable with `REDIS_URL=` |
| **Service Bus** | `ServiceBusPublisher` (no-op without connection string) |
| **WebSockets** | `/ws/agents/{agent_id}/queue?token=<jwt>` — closes **4001** if token missing/invalid; Redis pub/sub fan-out (`WebSocketHub`) |
| **Integration APIs** | `X-API-Key` + Key Vault (`KEY_VAULT_URL`) or `INTEGRATION_API_KEYS_JSON` locally |
| **Errors** | Standard `{ "error": { "code", "message", "details" } }` envelope + 429 for rate limits |
| **Database** | SQLModel metadata + Alembic baseline migration (`alembic/versions/001_baseline_empty.py`) |

### Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

### Run API

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Docs: `http://127.0.0.1:8000/docs`
- Health: `GET /api/v1/health`
- JWT samples: `GET /api/v1/common/me`, `GET /api/v1/common/admin/ping` (needs `Admin` role claim)
- Integrations: `POST /api/v1/integrations/ivr/webhook` with header `X-API-Key`

### Migrations

```powershell
cd backend
alembic upgrade head
```

### Tests

```powershell
cd backend
pytest
```

Work order **WO-2** status was set to **in_review** in Software Factory after implementation.
