# Lvxin Contract Analysis

This is a web-based platform for uploading and analyzing legal contracts. It features a robust, resumable file upload system built with FastAPI on the backend and modern JavaScript on the frontend.

## Features

- **Resumable File Uploads**: Pause and resume large file uploads, even after a network interruption or browser crash.
- **Chunked Uploading**: Files are uploaded in small, manageable chunks to improve reliability.
- **Backend Analysis Pipeline**: Once a file is uploaded, it is sent to a (mocked) third-party service for analysis.
- **User-Specific Storage**: Uploaded files are stored securely in user-specific directories.
- **Database Tracking**: Upload sessions are tracked in a PostgreSQL database for persistence.
- **Automated Cleanup**: A cleanup script is provided to remove stale or failed uploads.

## Tech-Stack

- **Backend**: FastAPI, Python 3.12
- **Database**: PostgreSQL
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3
- **Testing**: Pytest, unittest.mock

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- `pip` for package management

### OCR Dependencies

This project uses Tesseract for OCR and Poppler for PDF processing. You will need to install them on your system.

**For macOS (using Homebrew):**
```bash
brew install tesseract
brew install poppler
```

**For Debian/Ubuntu (using apt-get):**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
sudo apt-get install -y poppler-utils
```

You will also need to install the language data for Tesseract. For Simplified Chinese, you can do the following:

**For macOS:**
The `tesseract` formula installs all language packs by default.

**For Debian/Ubuntu:**
```bash
sudo apt-get install -y tesseract-ocr-chi-sim
```

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Lvxin
    ```

2.  **Create and activate a virtual environment:**

    We recommend using `virtualenv` as it is more robust. The standard `venv` module may fail in some environments.

    ```bash
    # Install virtualenv if you don't have it
    pip install virtualenv

    # Create and activate the environment
    virtualenv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
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
export PYTHONPATH=$(pwd)/venv/lib/python3.12/site-packages; uvicorn main:app --host 127.0.0.1 --port 8000
```

**Note**: You will need to provide valid API credentials as environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, `work_id`) for the analysis service to work.

#### Development (Mock) Mode

For frontend development and testing without making real API calls, you can run the application in mock mode. This mode simulates the API responses, allowing you to test the full upload flow without credentials or cost.

```bash
export APP_MODE=development; uvicorn main:app --host 127.0.0.1 --port 8000
```
*Note: Adjust the python version in the path if you are using a different one.*


## Environment Variables

Create a `.env` file in the root of the project and add the following variables.

```
ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_id_here
ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_secret_key_here
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

# Redis credentials for session storage
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
SESSION_EXPIRE_MINUTES=10080 # 7 days
```

## Running Redis locally

For local development, you can use Docker to easily run a Redis instance:

```bash
docker run -d -p 6379:6379 --name lvxin-redis redis
``` 