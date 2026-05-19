# Chikooza-UI Setup Guide

## Table of Contents

1. Prerequisites
2. Node.js and npm Installation
3. Git Installation
4. Project Setup Steps
    1. Clone the Repository
    2. Navigate to Repository
    3. Check Repository Status
    4. Branch Operations
    5. Verify Branch Switch
    6. Check Project Structure
    7. Install Dependencies
5. Running the Project
    1. Development Mode
    2. Build for Production
    3. Run Tests
6. Success Indicators
7. Summary


## Prerequisites

Before starting, ensure you have:
1. Administrative privileges on your system
2. Internet connection for downloading packages
3. Basic command line knowledge
4. Git connection with your system
5. Access to the repositories for chikooza-ui

Before setting up your project, ensure you have the following installed on your system:

### 1. Node.js and npm Installation

**Windows:**
1. Download Node.js from nodejs.org
2. Choose the LTS (Long Term Support) version
3. Run the installer and follow the setup wizard
4. Node.js installation includes npm automatically


**macOS:**
1. Using Homebrew:
```
brew install node
```
2. Or download from nodejs.org


**Linux (Ubuntu/Debian):**
```
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo
-E bash -
sudo apt-get install -y nodejs
```


Verify Installation:
```
node --version
npm --version
```

### 2. Git (if not already installed)

1. Download from git-scm.com
2. Verify:
```
git --version
```
________________________________________________________________________

## Project Setup Steps

### Step 1: Clone the Repository

```bash
# U: OLD: git clone https://github.com/RadianceVA/chikooza-ui.git
# U: NEW: frontend source is kept inside the backend monorepo.
git clone https://github.com/RadianceVA/chikooza-api.git
```
### Step 2: Navigate to Repository

```bash
cd chikooza-api/chikooza-ui
```
### Step 3: Check Repository Status

```
# Check current branch and status
git status
```

### Step 4: Branch Operations

```bash
# U: OLD: git checkout fixing-frontend
# U: NEW: current frontend source is on the monorepo branch.
git checkout correct-version
git pull origin correct-version
```
### Step 5: Verify Branch Switch

```
# Confirm you're on the correct branch
git branch
```
### Step 6: Check Project Structure

Verify the project contains these key files:
1. package.json - Contains project dependencies and scripts
2. package-lock.json or yarn.lock - Lock file for dependencies
3. src/ folder - Source code directory
4. public/ folder - Static assets
5. README.md - Project documentation

### Step 7: Install Dependencies

Using npm:
```
npm install
```

This command will create a **node_modules** folder from package.json.
________________________________________________________________________

## Running the Project

### Development Mode

```
npm start
```
This will:
1. Start the Vite development server
2. Open your browser to the Vite URL shown in the terminal, usually [http://localhost:5173](http://localhost:5173)

### Build for Production

```
npm run build
```
### Run Tests

There is no frontend test runner configured yet after the Vite migration.
________________________________________________________________________

## Success Indicators


Your setup is complete when:
1. npm start runs without errors
2. Application opens in browser at the Vite URL, usually [http://localhost:5173](http://localhost:5173)
3. No console errors in browser developer tools
4. All features work as expected
________________________________________________________________________

## Summary

Following this guide, you should now have:

1. A working React.js development environment
2. All Node.js dependencies installed and configured
3. The project cloned and set up on the correct Git branch
4. Development server running successfully on the Vite URL, usually [http://localhost:5173](http://localhost:5173)
5. Access to a fully functional frontend interface
6. Confirmation that there are no console errors and all features are working as
    expected
________________________________________________________________________
