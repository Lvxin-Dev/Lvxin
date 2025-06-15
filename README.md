# Lvxin Contract Analysis

This is a web application built with FastAPI for uploading, analyzing, and managing contracts.

## Features

- User authentication (including Google and WeChat logins)
- File upload (PDF, DOC, DOCX)
- Contract analysis
- User dashboard to view analysis history and results

## Project Structure

- `main.py`: The main FastAPI application entry point.
- `routers/`: Contains API routers for different parts of the application (e.g., `auth.py`).
- `core/`: Core components like database connections (`database.py`) and security (`security.py`).
- `services/`: Business logic for user management, file processing, etc.
- `templates/`: Jinja2 templates for the frontend.
- `static/`: Static assets (CSS, JS, images).
- `users/`: Directory where user-specific files are stored.
- `uploads/`: Temporary directory for file uploads.

## Setup Instructions

### Backend

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Lvxin
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the database:**
    - Make sure you have PostgreSQL installed and running.
    - Create a database named `lvxin`.
    - The application expects the following credentials (loaded from environment variables, with defaults for local development):
      - **DB_HOST**: `localhost`
      - **DB_USER**: `postgres`
      - **DB_PASSWORD**: `1234`
      - **DB_NAME**: `lvxin`
      - **DB_PORT**: `5432`
    - To restore the database from the provided dump file, run:
      ```bash
      psql -U postgres -d lvxin < db_dump.sql
      ```

### Frontend

The frontend is built with Jinja2 templates and is served directly by the FastAPI application. No separate setup is required.

## How to run the app locally

Run the following command from the root of the project:

```bash
uvicorn main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

## Environment Variables

Create a `.env` file in the root of the project and add the following variables. A `.env.example` is not provided, but you can create one from the following:

```
access_id=your_access_id_here
sec_key=your_secret_key_here
work_id=your_workspace_id_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SESSION_SECRET_KEY=a_long_random_string
WECHAT_CLIENT_ID=your_wechat_app_id_here
WECHAT_CLIENT_SECRET=your_wechat_app_secret_here

# Database credentials
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=1234
DB_NAME=lvxin
DB_PORT=5432
``` 