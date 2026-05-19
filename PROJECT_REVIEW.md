# Chikooza Local Setup And Initial Review

This note captures the current understanding of the repo after first local setup.

## Local Status

- Backend: Django API runs locally on `http://127.0.0.1:8002/`.
- UI: React app runs locally on `http://127.0.0.1:3000/`.
- Database: local SQLite file is `db1.sqlite3`.
- Chatbot: basic existing chatbot wiring is preserved. Full generated answers require local Ollama plus `llama3.2:3b`; without Ollama, `/chat/` now returns a retrieval-only fallback instead of a 500 error.

## Verified

- `venv/bin/python manage.py check` passes.
- `venv/bin/python manage.py migrate --plan` reports no pending migrations.
- `venv/bin/python manage.py test` runs successfully, but there are zero backend tests.
- `npm run build` succeeds for the UI with warnings.
- `npm test -- --watchAll=false` finds zero UI tests and exits with code 1 because CRA treats "no tests" as failure.
- `/chat/` returns `200 OK` with retrieved context fallback when Ollama is not installed/running.
- API smoke test works for OTP creation, signup, and login.

## Backend Folder Map

- `chikooza/`: Django project settings, root URLs, WSGI/ASGI entrypoints.
- `common/`: shared base models, response helpers, token generation, middleware, pagination, and validation utilities.
- `users/`: OTP, signup, login, profile, password reset/change, mobile update, and logout API logic.
- `farm/`: country, state, and farm models/APIs.
- `flocks/`: breed, integrator, hatchery, flock creation/update/detail/summary APIs.
- `purchase/`: purchase/feed/medicine/vaccine/equipment/labour/other cost APIs and quantity calculations.
- `dailydata/`: daily flock metrics, vaccines, FCR/mortality/feed calculations, PDF export, darkness/feed-availability lookup APIs.
- `sales/`: bird sale/final lifting/partial lifting APIs plus age and graph calculations.
- `chatbot/`: existing basic RAG chatbot endpoint and chat logs.
- `aibot/`: existing Text-to-SQL style agent over `ai_farm_data_view`.
- `data/`: RAG PDFs/index files. Ignored by git.
- `templates/`: Django templates, currently used for `dailydata.html` PDF output.
- `staticfiles/`: collected/static output.
- `chatbot_logs/` and `aibot_logs/`: local interaction logs. Ignored by git.

## UI Folder Map

- `chikooza-ui/src/routes/Router.js`: main route definitions.
- `chikooza-ui/src/Constants.js`: API/template base URL config.
- `chikooza-ui/src/layouts/`: public/member layouts, headers, footer, loader, logo.
- `chikooza-ui/src/views/ui/`: main app screens for login, register, farm/flock/purchase/daily-data/sales/profile/chatbot.
- `chikooza-ui/src/components/ChikoozaChatbot/`: existing basic chatbot UI wrapper.
- `chikooza-ui/src/components/dashboard/`: dashboard widgets/charts/tables.
- `chikooza-ui/src/assets/`: images, CSS, SCSS, logos.
- `chikooza-ui/public/`: CRA public files.
- `chikooza-ui/build/`: generated production build output. It is tracked in this repo but should usually not be part of normal source commits unless deployment requires it.
- `chikooza-ui/docs/setup/SETUP.md`: UI setup guide.

## Added Files From Supervisor

- `Setup Guide - Chikooza-API.pdf`: backend setup guide; it says to use branch `fix_flock_api`, install requirements, comment problematic sales migrations, run migrations, and run server.
- `Setup Guide - Chikooza-UI.pdf`: UI setup guide; it says to use branch `fixing-frontend`, run `npm install`, and start on port `3000`.
- `Poultry_7_Weeks_Data.xlsx`: one-sheet, 52-row poultry daily data sample with columns like date, mortality, feed intake, bird weight, vaccination, heating, sick, cooling, meds, darkness time, and feed availability time.

## Fixes Applied

- Backend dependencies were pinned/updated enough to install on Python 3.11 and pass Django checks.
- OLD sales migrations that duplicated columns already present in `sales/migrations/0001_initial.py` were commented and replaced with no-op migration operations.
- OLD eager chatbot service startup was commented/replaced with lazy loading so Django can start without initializing local RAG/Ollama on import.
- OLD hardcoded backend `HOSTNAME = "http://127.0.0.1:8001/"` was commented/replaced with `CHIKOOZA_API_BASE_URL`, defaulting to `http://127.0.0.1:8002/`.
- U: OLD hardcoded `SECRET_KEY`, duplicated `DEBUG=True`, wildcard `ALLOWED_HOSTS`, and always-open CORS were replaced with environment-driven settings and safer local defaults.
- U: OLD `corsheaders.middleware.CorsMiddleware` order was replaced with the recommended high middleware position before `CommonMiddleware`.
- Added backend `.env.example`.
- Added UI `.env.example` so `REACT_APP_API_BASE_URL` and `REACT_APP_TEMPLATE_BASE_URL` are explicit.
- Added missing UI dependency `react-chatbot-kit`.
- OLD UI chatbot fetch URL `https://local.api.chuza.com:8001/chat/` was commented/replaced with `${apiPath}chat/`.
- OLD chatbot behavior returned a 500 when Ollama was unavailable; new behavior keeps the endpoint usable with a retrieval-only fallback and explicit Ollama setup guidance.

## Good Things

- Domain separation is understandable: users, farms, flocks, daily data, purchases, sales.
- API and UI can run locally after dependency/migration fixes.
- Existing endpoint coverage matches the main poultry management workflow.
- Public IDs are used for API URLs instead of direct database IDs.
- The new `aibot` and `chatbot` apps are separated from core CRUD apps, which makes later replacement easier.

## Risks And Bad Things

- Very little automated testing exists. Both backend and UI currently have zero tests.
- Many frontend warnings show unused imports, weak equality checks, missing hook dependencies, and array callback mistakes.
- UI still mutates a shared `config` object in many older files; new touched screens now use a fresh authenticated config helper.
- Backend settings are safer than before, but deployment still needs real `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, exact allowed hosts, exact CORS origins, HTTPS/security headers, and deployment testing.
- Migrations are inconsistent in `sales`; no-op migration patches make local setup work but should be cleaned properly later.
- The backend depends on local/slow AI services in `chatbot` and `aibot`; `chatbot` now has graceful failure, while `aibot` still needs the same level of review.
- `aibot/services.py` uses pattern matching plus LangChain SQL agent behavior and contains risky parsing/formatting logic that should be reviewed before production use.
- The UI is on older React/CRA/MUI-era dependencies. A major "latest everything" upgrade should be a separate branch/task, not mixed into local setup fixes.
- Generated UI `build/` artifacts are tracked; this creates noisy diffs after every build.

## Recommended Next Steps

1. Create a new branch before committing any setup fixes.
2. Commit backend setup fixes separately from UI setup fixes.
3. Add minimal smoke tests for signup/login and one authenticated farm/flock flow.
4. Centralize Axios API client/auth header handling in the UI.
5. Decide whether `build/` should stay tracked. If not, remove it from git in a dedicated cleanup commit.
6. Later, integrate the newer chatbot/RAG/Text-to-SQL code behind separate classes without deleting the existing apps.
