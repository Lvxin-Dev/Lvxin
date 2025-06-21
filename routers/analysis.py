import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from uuid import UUID

from core.security import cookie, verifier, SessionData
from core.database import get_db_connection, release_db_connection

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)

@router.get("/analysis/report/{file_name}", tags=["Analysis"])
async def get_analysis_report(
    request: Request,
    file_name: str,
    session_id: UUID = Depends(cookie),
    db=Depends(get_db)
):
    """
    Retrieves the analysis report for a given file.
    Handles both with and without .json extension in the request.
    """
    session_data: SessionData = await verifier(request)
    if not session_data:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_id = session_data.user_id
    username = session_data.username
    
    # Create the user folder path with the format "userid_username"
    user_folder_name = f"{user_id}_{username}" if username else str(user_id)
    user_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "users", user_folder_name)
    user_folder = os.path.abspath(user_folder)
    
    # Remove .json extension if present to get the base name
    if file_name.lower().endswith('.json'):
        file_name = file_name[:-5]  # Remove .json extension
    
    basename = os.path.splitext(file_name)[0]  # In case there are other extensions
    report_name = f"{basename}.json"
    report_path = os.path.join(user_folder, report_name)
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Looking for report at path: {report_path}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Absolute report path: {os.path.abspath(report_path)}")
    
    # Check if the directory exists
    if not os.path.exists(user_folder):
        logger.error(f"User folder does not exist: {user_folder}")
        raise HTTPException(status_code=404, detail=f"User folder not found: {user_folder}")
        
    # List files in the directory for debugging
    try:
        files = os.listdir(user_folder)
        logger.info(f"Files in {user_folder}: {files}")
    except Exception as e:
        logger.error(f"Error listing directory {user_folder}: {e}")

    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")

    with open(report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Ensure the data is in the expected format
    if not isinstance(report_data, list):
        # If it's a single result, wrap it in a list
        if isinstance(report_data, dict):
            report_data = [{"Output": {"result": report_data}}]
        else:
            # If it's already in the correct format, use as is
            report_data = report_data
    
    logger.info(f"Returning report data with {len(report_data)} items")
    return JSONResponse(content=report_data)
