# Backend FastAPI Template

Production-ready backend API template with FastAPI, PostgreSQL, and Docker Compose.

## What's Included

- ⚡ FastAPI backend API
- 🧰 SQLModel (ORM) + Pydantic settings
- 💾 PostgreSQL database
- 🔑 JWT authentication
- 📫 Email-based password recovery (token-based, API-only)
- 📬 Mailcatcher for local email testing
- 🗄️ Adminer for database administration
- 🐋 Docker Compose for local dev and deployments
- 📞 Traefik integration via Docker labels (optional)

## Quickstart (Docker)

```bash
docker compose up -d --build
```

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Adminer: http://localhost:8080
- Mailcatcher: http://localhost:1080

## Docs

- Backend docs: `backend/README.md`
- Development: `development.md`
- Deployment: `deployment.md`

