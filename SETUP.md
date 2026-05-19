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
5. Access to the repositories for chikooza-api


## Git Repository Operations

#### Step 1: Clone the Repository

```
git clone https://github.com/RadianceVA/chikooza-api.git
```
#### Step 2: Navigate to Repository

```
cd path/to/chikooza
```
#### Step 3: Check Repository Status

```
# Check current branch and status
git status
```
#### Step 4: Branch Operations


```
git checkout fix_flock_api
```
```
# Pull latest changes from current branch
git pull origin fix_flock_api
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
    2. Download Python 3.8 or higher (recommended: Python 3.9+)
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


 Add in settings.py:

```
DATABASES = {
    'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'chikooza_db',
    'USER': 'chikooza_user',
    'PASSWORD': 'your_password',
    'HOST': 'localhost',
    'PORT': '5432',
    }
}
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
```

#### 2. Delete the existing Database:

```
del db.sqlite
```
#### 3. Comment the contents of operations in the files:


1. sales/migrations/0004_auto_20221130_
2. sales/migrations/0006_auto_20221201_
3. sales/migrations/0007_sales_buyer_email


## Running the Development Server

#### Step 1: Apply Database Migrations after the changes

```
python manage.py makemigrations
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
Django version 4.1.3, using settings 'chikooza.settings'
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

