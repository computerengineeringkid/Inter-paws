# Inter-Paws AI Coding Guidelines

## Architecture Overview

Inter-Paws is a full-stack veterinary clinic appointment scheduling platform with AI-powered slot optimization.

**Core Components:**

- **Backend**: Flask application factory with SQLAlchemy ORM, JWT authentication, and REST API
- **Frontend**: React + TypeScript with Vite, React Query for API state, React Router for navigation
- **AI Engine**: OR-Tools constraint solver + Ollama LLM for intelligent appointment ranking
- **Database**: PostgreSQL with Alembic migrations
- **Deployment**: Docker Compose (dev) + Vercel serverless (prod)

**Key Data Flow:**

1. Client submits appointment request via React frontend
2. Backend validates request and fetches clinic constraints from PostgreSQL
3. OR-Tools generates feasible time slots based on doctor/room availability
4. Ollama LLM ranks slots using historical booking insights (RAG)
5. Ranked recommendations returned to client

## Critical Developer Workflows

### Local Development Setup

```bash
# One-command setup: creates venv, installs deps, runs migrations, starts dev server
./run_dev.sh

# Manual setup if needed:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export FLASK_APP="backend.app.serverless:app"
flask db upgrade
flask run --port 5000
```

### Testing

```bash
# Backend unit tests (pytest)
python -m pytest tests/

# Frontend E2E tests (Playwright)
cd frontend && npm run test:e2e

# Frontend development
cd frontend && npm run dev
```

### Database Operations

```bash
# Create new migration after model changes
flask db migrate -m "description"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## Project-Specific Patterns

### Backend Architecture

- **Application Factory**: Use `create_app()` in `backend/app/__init__.py` for Flask app initialization
- **Service Layer**: Business logic in `backend/app/services/` (e.g., `scheduler_service.py`)
- **Dataclasses**: Structured data models in `ai/models/constraint_model.py` using Python dataclasses
- **Type Hints**: Extensive use throughout codebase - always include return types and parameter types

### Frontend Patterns

- **Protected Routes**: Use `ProtectedRoute` component with `requireAdmin` prop for clinic staff routes
- **API Integration**: React Query hooks in `frontend/src/utils/api.ts` for all backend communication
- **Auth Context**: Centralized authentication state in `AuthContext.tsx`

### AI Integration

- **Constraint Solving**: OR-Tools CP-SAT solver for generating feasible appointment slots
- **LLM Ranking**: Ollama integration for intelligent slot prioritization using historical insights
- **RAG System**: Booking insights stored in `ai/scripts/insights.json` for improved recommendations

### Database Patterns

- **Multi-tenant**: All entities scoped to `clinic_id` for clinic isolation
- **Audit Logging**: All API requests logged to `audit_logs` table with request/response hashes
- **Soft Deletes**: Use `is_active` boolean instead of hard deletes where applicable

## Code Organization

### File Structure Conventions

```
backend/app/
├── api/           # REST API endpoints (auth.py, clinic.py, scheduler.py)
├── services/      # Business logic (scheduler_service.py, llm_client.py)
├── models.py      # SQLAlchemy models
└── __init__.py    # Flask app factory

frontend/src/
├── components/    # Reusable React components
├── pages/         # Route-level page components
├── context/       # React context providers (AuthContext.tsx)
└── utils/         # Utilities (api.ts)

ai/
├── models/        # Constraint solving models
└── scripts/       # Data processing scripts (rag_update.py)
```

### Naming Conventions

- **Models**: PascalCase classes (e.g., `AppointmentRequest`, `DoctorAvailability`)
- **API Endpoints**: RESTful with resource names (`/api/clinic/{id}/schedule`)
- **Database**: snake_case columns, PascalCase table names
- **React**: PascalCase components, camelCase hooks/functions

## Common Gotchas

### Backend

- **Datetime Handling**: Always use timezone-aware datetimes; parse with `datetime.fromisoformat()`
- **Clinic Scoping**: Never forget to filter by `clinic_id` in multi-tenant queries
- **LLM Fallback**: Always implement heuristic fallbacks when LLM calls fail

### Frontend

- **Route Protection**: Use `ProtectedRoute` with correct `requireAdmin` prop for clinic routes
- **API Error Handling**: React Query handles loading/error states automatically

### Deployment

- **Environment Variables**: Critical vars: `DATABASE_URL`, `JWT_SECRET_KEY`, `OLLAMA_BASE_URL`
- **Serverless**: Vercel deployment routes all `/api/*` to `serverless.py`
- **Docker**: Use `docker-compose.yml` for local PostgreSQL + app development

## Key Files to Reference

- `backend/app/services/scheduler_service.py` - Main scheduling orchestration
- `ai/models/constraint_model.py` - OR-Tools constraint solving
- `docs/llm_integration.md` - LLM prompt engineering and API
- `frontend/src/utils/api.ts` - Frontend API integration patterns
- `backend/config.py` - Configuration management
- `docker-compose.yml` - Local development environment
