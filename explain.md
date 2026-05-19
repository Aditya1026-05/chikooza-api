# Chikooza Project Explanation

This file explains the project in simple English so you can discuss it in a meeting.

## Big Picture

Chikooza is a poultry farm management project.

The backend is a Django API. It stores users, farms, flocks, purchases, daily flock data, sales, and AI/chatbot logs.

The frontend is a React app. It gives screens for registration, login, farm management, flock management, purchases, daily data, sales, reports, and chatbot UI.

The project has two Git repositories:

- Backend repository: the main folder.
- Frontend repository: `chikooza-ui/`.

## How To Read The Backend

Read backend folders in this order:

1. `manage.py` and `chikooza/`
2. `common/`
3. `users/`
4. `farm/`
5. `flocks/`
6. `purchase/`
7. `dailydata/`
8. `sales/`
9. `chatbot/`
10. `aibot/`
11. `templates/` and `data/`
12. `*/migrations/`

Inside each backend app, read files in this order:

1. `models.py`
2. `serializers.py`
3. `services.py`
4. `views.py`
5. `urls.py`

That order is useful because models show the database tables, serializers show API input/output shape, services show business logic, views show API request handling, and URLs show the endpoint names.

## Backend Folders

### `manage.py`

This is the command file for Django.

You use it to run commands like:

- Start the backend server.
- Run database migrations.
- Run tests.
- Create admin users.

Example:

```bash
venv/bin/python manage.py runserver 127.0.0.1:8002
```

### `chikooza/`

This is the main Django project configuration.

Important files:

- `settings.py`: installed apps, database settings, CORS settings, OAuth settings, static/media settings, local API base URL.
- `urls.py`: root URL file. It connects routes like `/users/`, `/chat/`, `/ai/`, `/farm/`, `/flocks/`, `/purchase/`, `/dailyData/`, and `/sales/`.
- `wsgi.py` and `asgi.py`: deployment entry files.

Start here because this folder tells you which apps exist and how they are connected.

### `common/`

This folder contains shared code used by many backend apps.

It has:

- Base models like `BaseModel`, `PublicId`, `Users`, and OTP models.
- Common response helpers.
- Token creation helpers.
- Middleware for API error handling.
- Pagination helpers.
- Validation helpers.

Many business apps depend on `common/`, so read it before reading the business modules.

### `users/`

This folder handles user authentication and profile flows.

It includes:

- Send OTP.
- Verify OTP.
- Signup.
- Login.
- Logout.
- Profile view/update.
- Reset password.
- Forget password.
- Change password.
- Update mobile number.

Important local detail:

- The OTP is currently fixed at `123456` in `common/utils.py`.

Other modules depend on logged-in users, so this app is important.

### `farm/`

This folder handles farm master data.

It includes:

- Country.
- State.
- Farm.

A user can create farms. Flocks are later attached to farms.

Typical flow:

1. Get country/state list.
2. Create farm.
3. List or update farms for the logged-in user.

### `flocks/`

This is one of the core business modules.

It handles flock lifecycle data:

- Breed.
- Integrator.
- Hatchery.
- Flock.
- Flock details.
- Flock summary.

A flock belongs to:

- A user.
- A farm.
- A breed.
- Optionally an integrator or hatchery.

Most later modules depend on flock data.

### `purchase/`

This folder stores purchases/costs for a flock.

Purchase types include:

- Feed.
- Medicine.
- Vaccination.
- Equipment.
- Labour.
- Other.

Feed purchase is important because daily data uses feed quantity to calculate feed stock and feed consumption.

### `dailydata/`

This folder stores day-by-day flock operations.

It handles:

- Daily mortality.
- Feed intake.
- Average bird weight.
- Current bird count.
- FCR calculations.
- Cooling/heating/sick/medicine flags.
- Vaccination records.
- Darkness time.
- Feed availability.
- Daily data PDF export.

This is a central module because it tracks flock performance over time.

### `sales/`

This folder handles flock sales/lifting.

It includes:

- Partial lifting.
- Final lifting.
- Sale amount.
- Buyer details.
- Weight/rate calculations.
- Graph endpoints.
- Flock age endpoint.

Sales affect bird counts and profit/loss summaries.

### `chatbot/`

This is the existing basic RAG chatbot API.

Endpoint:

- `/chat/`

What it does:

- Loads a FAISS vector index from `data/`.
- Uses sentence transformer embeddings.
- Tries to call local Ollama model `llama3.2:3b`.
- Stores chat logs.

Current local behavior:

- If Ollama is not installed/running, `/chat/` now returns a retrieval-only fallback instead of crashing.
- For full generated answers, Ollama must be running locally.

### `aibot/`

This is the existing authenticated AI SQL API.

Endpoint:

- `/ai/`

What it does:

- Uses an SQL-style agent.
- Reads from `ai_farm_data_view`.
- Tries to answer questions about farm/flock/sales/purchase data.

This is related to Text-to-SQL work, but it should be reviewed carefully before production use.

### `templates/`

This contains Django HTML templates.

Currently the important template is:

- `dailydata.html`

It is used for PDF generation.

### `data/`

This contains AI/RAG data.

It includes:

- Source poultry documents.
- FAISS index files.

The chatbot uses this folder for document retrieval.

### `*/migrations/`

These folders contain database migration history.

Read migrations last.

Reason:

- Migrations are not the best way to learn business logic.
- They mainly show how database tables changed over time.
- Some sales migrations had setup issues and were made no-op for local setup.

## How To Read The Frontend

Read frontend files in this order:

1. `chikooza-ui/package.json` and `.env.example`
2. `chikooza-ui/src/index.js`
3. `chikooza-ui/src/App.js`
4. `chikooza-ui/src/routes/Router.js`
5. `chikooza-ui/src/layouts/`
6. `chikooza-ui/src/Constants.js`
7. `chikooza-ui/src/views/ui/`
8. `chikooza-ui/src/components/`
9. `chikooza-ui/src/assets/`
10. `chikooza-ui/public/` and `docs/`

### `chikooza-ui/package.json`

This tells you:

- The app is a React app.
- Which dependencies are installed.
- Which scripts are available.

Important scripts:

```bash
npm start
npm run build
```

`npm start` runs the Vite development server. `npm run build` writes the
production bundle to `chikooza-ui/build/`.

### `chikooza-ui/.env.example`

This shows which environment variables are needed.

Important values:

- `VITE_API_BASE_URL`
- `VITE_TEMPLATE_BASE_URL`
- `REACT_APP_API_BASE_URL`
- `REACT_APP_TEMPLATE_BASE_URL`

The `REACT_APP_*` names are kept temporarily for old local `.env` files, but
new setup should use the `VITE_*` names.

For local setup these point to:

```bash
http://127.0.0.1:8002/
```

### `chikooza-ui/src/index.js`

This is the frontend entry file.

It mounts the React app into the browser and wraps it with `BrowserRouter`.

### `chikooza-ui/src/App.js`

This loads the route configuration and renders the matching page.

### `chikooza-ui/src/routes/Router.js`

This is the frontend route map.

It connects browser URLs to pages.

Examples:

- `/` opens the home page.
- `/login` opens login.
- `/register` opens signup.
- `/member` opens member dashboard.
- `/addfarm` opens add farm.
- `/addflock` opens add flock.
- `/dailydata...` opens daily data pages.
- `/chatbot` opens chatbot page.

### `chikooza-ui/src/layouts/`

This contains page shells.

It controls:

- Header.
- Footer.
- Public layout.
- Logged-in member layout.
- Loader.
- Logo.

Think of layouts as the frame around the pages.

### `chikooza-ui/src/Constants.js`

This is important because API calls use values from here.

It exports:

- `apiPath`
- `templatePath`
- shared request config
- common CSS class values

Most frontend API calls build URLs using `apiPath`.

### `chikooza-ui/src/views/ui/`

This contains the main business screens.

Important pages:

- `Register.js`: signup and OTP flow.
- `Login.js`: login flow.
- `Member.js`: member dashboard.
- `AddFarm.js`: create farm.
- `ManageFarm.js`: list/update farm.
- `Addflock.js`: create flock.
- `ManageFlock.js`: list/update flock.
- `AddPurchase.js`: add purchase.
- `ListPurchase.js`: list purchase.
- `ViewPurchase.js`: view/update purchase.
- `DayData.js`: add/update daily data.
- `DailyDataSheet.js`: daily data sheet.
- `FlockDailyData.js`: flock daily data list.
- `FlockSummary.js`: flock summary.
- `FlockSale.js`: add sale.
- `ViewSale.js`: list sales.
- `EditSale.js`: edit sale.
- `Profile.js`: user profile.
- `ChangePassword.js`: change password.
- `ForgetPassword.js`: reset/forget password.
- `Chatbot.js`: chatbot page.

This is the main folder to understand user-facing behavior.

### `chikooza-ui/src/components/`

This contains reusable UI pieces.

Important folders:

- `dashboard/`: dashboard charts, tables, feeds, blog widgets.
- `ChikoozaChatbot/`: chatbot widget, chatbot config, message parser, action provider, styles.

### `chikooza-ui/src/assets/`

This contains frontend styling and images.

It includes:

- CSS.
- SCSS.
- Logos.
- Background images.
- User images.
- Front page images.

### `chikooza-ui/public/`

This contains static files served by React.

Examples:

- `index.html`
- favicon files
- robots file

### `chikooza-ui/docs/`

This contains frontend setup documentation.

Read it after understanding the code structure.

## Folders To Skip Initially

Skip these while learning:

- `venv/`
- `chikooza-ui/node_modules/`
- `chikooza-ui/build/`
- `staticfiles/`
- `__pycache__/`

These are generated or dependency folders, not the main source code.

## Simple End-To-End Flow

The normal app flow is:

1. User registers with OTP.
2. User logs in.
3. User creates a farm.
4. User creates a flock inside that farm.
5. User adds purchases for that flock.
6. User enters daily flock data.
7. User records sales/lifting.
8. User views summaries, charts, and reports.
9. User can use chatbot/AI features if local AI setup is available.

## What Is Working Locally Now

- Backend server runs at `http://127.0.0.1:8002/`.
- Frontend server runs at `http://127.0.0.1:3000/`.
- Registration API works with fixed OTP `123456`.
- Login API works.
- Main API flow works for farm, flock, purchase, daily data, sale, sales list, and flock summary.
- Existing chatbot endpoint responds with fallback context if Ollama is not running.

## One-Sentence Supervisor Summary

The project is a Django plus React poultry management system where users manage farms, flocks, purchases, daily performance data, and sales, with separate existing chatbot and AI SQL modules that can later be replaced or upgraded without deleting the old implementation.
