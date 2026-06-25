# Chikooza Monorepo

U: OLD: this file was the default GitLab repository template.
U: NEW: this repo now documents the actual Chikooza backend + frontend setup.

Chikooza is a poultry farm operations MVP with:

- Django REST backend for auth, farms, flocks, purchases, daily data, sales, PDFs, admin, chatbot, and authenticated AI data queries.
- React/Vite frontend in `chikooza-ui/`.
- Local SQLite by default, with deployment database support through `DATABASE_URL`.
- Database-backed RAG chatbot at `/chat/` and authenticated tenant-safe AI endpoint at `/ai/`.

## Current Branch

Use `correct-version` for the current working branch:

```bash
git checkout correct-version
git pull origin correct-version
```

## Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# For chatbot parity with production, set DATABASE_URL to PostgreSQL with pgvector.
python manage.py migrate
python manage.py ingest_chatbot_knowledge
python manage.py runserver 8002
```

Local API URL: `http://127.0.0.1:8002/`

Admin URL: `http://127.0.0.1:8002/admin/`

For local MVP testing, `.env.example` keeps `CHIKOOZA_FIXED_OTP=123456`. Remove that variable outside local testing.

## Frontend

```bash
cd chikooza-ui
npm install
cp .env.example .env
npm run dev
```

Vite usually serves the UI at `http://localhost:5173/`.

## Verification

```bash
venv/bin/python manage.py check
venv/bin/python manage.py test
cd chikooza-ui && npm run build
cd chikooza-ui && npm audit --omit=dev
```

## Public Chatbot Pipeline

`/chat/` uses a production-style RAG pipeline:

1. Handle greetings, acknowledgements, unclear text, and nonsense with short fixed replies.
2. Reject clearly outside-topic questions before retrieval.
3. Retrieve matching `KnowledgeChunk` rows from PostgreSQL pgvector.
4. Ask Groq to judge whether the retrieved context directly answers the user question.
5. Ask Groq for the final answer only when the context is relevant enough.
6. Store `ChatSession` and `ChatMessage` rows so follow-up questions keep context.

## Notes

- Do not commit real secrets. Keep `GROQ_API_KEY`, `DJANGO_SECRET_KEY`, database credentials, and deployment keys in local `.env` or deployment secrets only.
- The public chatbot is database-backed RAG. For local/prod parity, point `DATABASE_URL` at PostgreSQL with pgvector available, set `CHIKOOZA_RAG_REQUIRE_PGVECTOR=True`, run migrations, then load reference docs with `venv/bin/python manage.py ingest_chatbot_knowledge`. SQLite remains only a lightweight fallback for backend tests and non-RAG local checks.
- New chatbot documents can also be uploaded in Django admin under `Knowledge documents` and processed with the admin action.
- The old code is preserved where replaced, using `U:` comments to mark old/new behavior.
- The PDF template content still needs a product-specific update; the renderer dependency stack is modernized.
