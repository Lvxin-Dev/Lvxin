import os
import shutil
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the project root to the Python path to allow for absolute imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from core.database import get_db_connection, release_db_connection

# --- Test Setup ---

# Use a TestClient to make requests to the FastAPI app
client = TestClient(app)

# Define the temporary directory for test uploads
TEST_TEMP_DIR = "/tmp/test_uploads"

# --- Fixtures and Mocks ---

@patch('services.contract_analysis.oss_upload')
@patch('services.contract_analysis.api_dep')
def test_finish_upload_success(mock_api_dep, mock_oss_upload):
    """
    Tests the successful finalization of an upload.
    Mocks the external calls to OSS and the analysis API.
    """
    # --- 1. Setup Mock Responses ---
    # Mock the oss_upload function to return a fake URL
    mock_oss_upload.return_value = "http://mock-oss-bucket.com/testfile.pdf"
    
    # Mock the api_dep function to return a successful analysis result
    mock_api_dep.return_value = {"status": "success", "analysis_id": "mock-analysis-123"}

    # --- 2. Setup Test Data and Database State ---
    conn = get_db_connection()
    upload_id = uuid.uuid4()
    user_id = uuid.uuid4() # In a real scenario, this would come from a logged-in user
    file_name = "testfile.pdf"
    storage_path = os.path.join(TEST_TEMP_DIR, str(upload_id))
    final_path = os.path.join(os.path.dirname(__file__), '..', 'users', str(user_id), file_name)

    # Ensure directories exist
    os.makedirs(storage_path, exist_ok=True)
    os.makedirs(os.path.dirname(final_path), exist_ok=True)

    # Create a dummy chunk file to simulate a completed chunk upload
    with open(os.path.join(storage_path, "chunk_0"), "wb") as f:
        f.write(b"dummy content")

    # Insert a record into the database to simulate an in-progress upload session
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO file_upload_sessions (id, user_id, file_name, file_size, mime_type, status, storage_path, uploaded_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (str(upload_id), str(user_id), file_name, 13, 'application/pdf', 'in_progress', storage_path, 13)
        )
    conn.commit()

    # --- 3. Make the API Call ---
    # Simulate a session cookie for an authenticated user
    client.cookies["session_id"] = str(user_id)
    
    response = client.post(f"/uploads/{upload_id}/finish")

    # --- 4. Assertions ---
    # Check that the API call was successful
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "File uploaded and analysis started successfully."
    assert response_data["filename"] == file_name

    # Check that our mock functions were called correctly
    mock_oss_upload.assert_called_once()
    mock_api_dep.assert_called_once_with(
        "http://mock-oss-bucket.com/testfile.pdf", 
        file_name, 
        f"{os.path.splitext(final_path)[0]}.json"
    )

    # Check the database state
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM file_upload_sessions WHERE id = %s", (str(upload_id),))
        record = cur.fetchone()
        assert record[0] == 'completed'

    # --- 5. Cleanup ---
    with conn.cursor() as cur:
        cur.execute("DELETE FROM file_upload_sessions WHERE id = %s", (str(upload_id),))
    conn.commit()
    release_db_connection(conn)
    shutil.rmtree(TEST_TEMP_DIR)
    shutil.rmtree(os.path.dirname(final_path))
