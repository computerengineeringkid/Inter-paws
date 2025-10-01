# Self-Hosting Deployment Guide

This guide walks you through deploying Inter-Paws on your own infrastructure using Docker Compose. The stack consists of a Flask web application and a PostgreSQL database.

## Prerequisites

Before you begin, ensure the following are installed on your server:

- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- `git`

## 1. Clone the Repository

```bash
git clone <repository-url> interpaws
cd interpaws
```

Replace `<repository-url>` with the HTTPS or SSH URL of your fork or the official repository.

## 2. Create the `.env` File

All sensitive configuration (database credentials, JWT secret, etc.) is provided through environment variables. Create a new `.env` file in the repository root with the following contents:

```bash
cat <<'ENV' > .env
# PostgreSQL configuration
POSTGRES_DB=interpaws
POSTGRES_USER=interpaws
POSTGRES_PASSWORD=change-me

# SQLAlchemy connection string for the Flask app
DATABASE_URL=postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

# Flask / security secrets
JWT_SECRET_KEY=replace-with-a-strong-secret
FLASK_ENV=production
ENV
```

Update the placeholder values (`change-me`, `replace-with-a-strong-secret`, etc.) with secure secrets that match your deployment requirements.

## 3. Build the Docker Images

Docker Compose will build the web service using the provided `infra/Dockerfile` and pull the official PostgreSQL image.

```bash
docker compose build
```

## 4. Run Database Migrations

After the images are built, apply the latest database schema using Flask-Migrate. This command creates a one-off container, runs the migrations, and then removes the container when it is finished.

```bash
docker compose run --rm web flask db upgrade
```

## 5. Start the Application Stack

Bring up the entire stack in the background. The Flask app will be exposed on port 5000 by default.

```bash
docker compose up -d
```

You can inspect the logs at any time using `docker compose logs -f` and stop the services with `docker compose down`.

## 6. Verify the Deployment

Open a browser and navigate to `http://<server-ip>:5000` (replace `<server-ip>` with your server's address) to confirm the application is running. API endpoints are available under the `/api/` path.

## 7. Maintenance Tips

- Back up the persistent PostgreSQL volume (`postgres_data`) regularly to preserve your data.
- When updating the application, pull the latest changes, rebuild the images, rerun migrations, and restart the stack:
  ```bash
  git pull
  docker compose build
  docker compose run --rm web flask db upgrade
  docker compose up -d
  ```
- Monitor container health with `docker compose ps` and logs with `docker compose logs -f`.

With these steps, your Inter-Paws deployment should be live on your self-hosted infrastructure.
