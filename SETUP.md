# Chikooza-Api Setup Guide

## Table of Contents

1. Prerequisites
2. Git Repository Operations
3. Python Installation
4. Virtual Environment Setup
5. Project Dependencies Installation
6. Database Setup
7. Changes Before Running the Development Server
8. Running the Development Server
9. Summary


## Prerequisites

Before starting, ensure you have:


1. Administrative privileges on your system
2. Internet connection for downloading packages
3. Basic command line knowledge
4. Git connection with your system
5. Access to the `chikooza-api` repository. The frontend now lives inside this same repo at `chikooza-ui/`.


## Git Repository Operations

#### Step 1: Clone the Repository

```
git clone https://github.com/RadianceVA/chikooza-api.git
```
#### Step 2: Navigate to Repository

```
cd chikooza-api
```
#### Step 3: Check Repository Status

```
# Check current branch and status
git status
```
#### Step 4: Branch Operations


```bash
# U: OLD: git checkout fix_flock_api
# U: NEW: current modernization branch used for local setup and review.
git checkout correct-version
git pull origin correct-version
```
#### Step 5: Verify Branch Switch

```
# Confirm you're on the correct branch
git branch
```

## Python Installation

### Windows

1. Download Python:
    1. Visit python.org
    2. Download Python 3.11 or higher
2. Install Python:
     1. Run the downloaded installer
     2. ✅ Check "Add Python to PATH"
     3. ✅ Check "Install pip"
     4. Choose "Install Now"
3. Verify Installation using commands:

    ```
    python --version
    pip --version
    ```

#### macOS

**1. Using Homebrew (Recommended):**

```
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
```
brew install python
```
**2. Verify Installation:**

```
python3 --version pip3 --version
```

#### Linux (Ubuntu/Debian)

```
sudo apt update
sudo apt install python3 python3-pip python3-venv
```
```
# Verify installation
python3 --version
pip3 --version
```

## Virtual Environment Setup

#### Create Virtual Environment

```
# Navigate to your project directory
cd /path/to/your/project

python -m venv chikooza_env
```
```
# Alternative for Linux/Mac
python3 -m venv chikooza_env
```
#### Activate Virtual Environment

**Windows:**

```
chikooza_env\Scripts\activate
```
**macOS/Linux:**

```
source chikooza_env/bin/activate
```
#### Verify Activation

```
which python
```

## Project Dependencies Installation

#### Upgrade pip

```
python -m pip install --upgrade pip
```
#### Install Dependencies from requirements.txt


```
pip install -r requirements.txt
```

## Database Setup

#### SQLite (Default - No Additional Setup Required)

Your project is configured to use SQLite by default. The database file will be created automatically.

#### PostgreSQL Setup (Optional)

**If you want to use PostgreSQL instead:**

1. Install PostgreSQL: 
    
    Windows:
    1. Download from postgresql.org
    2. Run installer and note the password

    macOS:

    ```
    brew install postgresql
    brew services start postgresql
    ```

    Linux:
    ```
    sudo apt install postgresql postgresql-contrib
    sudo systemctl start postgresql
    ```

**2. Create Database:**

```
sudo -u postgres psql
CREATE DATABASE chikooza_db;
CREATE USER chikooza_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE chikooza_db TO
chikooza_user;
\q
```
**3. Update settings.py:**


 U: OLD: the guide suggested editing `settings.py` manually.

 U: NEW: keep settings code unchanged and configure PostgreSQL through `.env`:

```bash
DATABASE_URL=postgres://chikooza_user:your_password@localhost:5432/chikooza_db
```



## Changes before Running Development Server

#### 1. Configure local environment variables

```bash
# U: OLD: backend settings were hardcoded directly inside chikooza/settings.py.
# U: NEW: copy the example file and adjust values only when your local ports/hosts differ.
cp .env.example .env
```

The important local defaults are:

```bash
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=django-insecure-local-dev-only-change-before-deploy
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,.herokuapp.com
CHIKOOZA_CORS_ALLOW_ALL=True
CHIKOOZA_API_BASE_URL=http://127.0.0.1:8002/
CHIKOOZA_FIXED_OTP=123456
CHIKOOZA_PUBLIC_CHAT_PROVIDER=auto
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
```

`GROQ_API_KEY` must stay in local `.env` or deployment secrets only. Do not commit
the real key; `.env.example` intentionally keeps it blank.

`CHIKOOZA_PUBLIC_CHAT_PROVIDER=auto` means the public website chatbot uses Groq
when `GROQ_API_KEY` is configured, otherwise it can fall back to Ollama or the
deterministic local product answer.

`CHIKOOZA_FIXED_OTP=123456` is only for local MVP testing. In production, remove
that variable so OTPs are generated randomly.

When `CHIKOOZA_FIXED_OTP` is not set, `common/utils.py::send_otp()` still returns
`123456` if `DJANGO_DEBUG=True`. With `DJANGO_DEBUG=False`, it generates a random
6 digit OTP and stores it in the SQL `otp` table through `users/services.py`.
This project currently stores OTPs but does not include a real SMS provider
integration, so production delivery still needs to be added/configured.

#### 2. Do not manually edit migrations for normal setup

U: OLD: the handoff guide asked developers to delete database files and comment
sales migration operations manually.

U: NEW: this branch already contains the migration/setup fixes. For normal local
setup, run migrations as-is:

```bash
python manage.py migrate
```

#### 3. Understand SQL data versus RAG data

Farmer/customer records are stored in SQL tables through Django models. The main
business tables are `farms`, `flocks_flock`, `purchase_purchase`,
`dailydata_dailydata`, and `sales_sales`.

By default, local setup uses SQLite at `db1.sqlite3`. If `DATABASE_URL` is set,
Django uses that database instead; use a PostgreSQL URL for a shared or
production-like setup.

The authenticated `/ai/` endpoint answers private farmer-data questions through
tenant-safe SQL views: `ai_purchase_data_view`, `ai_dailydata_data_view`, and
`ai_sale_data_view`. Those views expose `owner_id`, and the active AI service
must filter by the logged-in user before executing a query.

The public `/chat/` site assistant is not allowed to access private farmer data.
The legacy RAG mode uses general poultry PDF documents and FAISS files under
`chatbot/data/`, especially `index.faiss` and `index.pkl`, not per-farmer
records.

Frontend routing mirrors that separation:

- Public homepage widget: `/chat/` with `mode: "site"`.
- Logged-in farmer AI page: `/chatbot`, which calls authenticated `/ai/`.


## Running the Development Server

#### Step 1: Apply Database Migrations after the changes

```
python manage.py migrate
```
#### Step 2: Create Superuser (Optional but Recommended)

```
python manage.py createsuperuser
```
```
# Follow prompts to enter:
# - Username
# - Email address
# - Password
```
#### Step 3: Start Development Server


```
# U: OLD: python manage.py runserver 8001
# U: NEW: run the API on the same port used by CHIKOOZA_API_BASE_URL.
python manage.py runserver 8002
```
#### Step 4: Verify Installation Success

Once the server is running, you should see output like:

```
System check identified no issues (0 silenced).
June 10, 2025 - 10:30:
Django version 5.2.x, using settings 'chikooza.settings'
Starting development server at http://127.0.0.1:8002/
Quit the server with CTRL-C.
```
#### Step 5: Access Your Application

Open your web browser and navigate to:

1. Main Application: http://127.0.0.1:8002/
2. Admin Panel: http://127.0.0.1:8002/admin/
3. API Endpoints: http://127.0.0.1:8002/api/ (depending on your URL configuration)



## Summary

Following this guide, you should now have:

1. A working Django development environment
2. All dependencies installed and configured
3. Database set up and migrated
4. Development server running successfully
5. Access to admin panel and application
