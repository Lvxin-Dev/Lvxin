from fastapi import APIRouter, Request, File, UploadFile, Form, Depends, HTTPException, Body, Response
from typing import Optional, Dict
from uuid import UUID, uuid4
import os
import aiofiles
import logging
from datetime import datetime, timedelta
import psycopg2.extras
import shutil
import urllib.parse

from core.database import get_db_connection, release_db_connection
from core.security import cookie, verifier, SessionData
from services.user_management import create_user_folder
from services.contract_analysis import oss_upload, api_dep
from services.file_processing import process_pdf, process_docx, process_doc, process_image

# --- Configuration ---
router = APIRouter()
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_DIR = os.path.join(BASE_DIR, "users")
TEMP_UPLOAD_DIR = os.path.join(USERS_DIR, "tmp_uploads")

# Ensure temporary upload directory exists
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# --- Helper Functions ---
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)

# --- API Endpoints for Resumable Upload ---

@router.post("/uploads/initiate", status_code=201, tags=["Uploads"])
async def initiate_upload(
    request: Request,
    file_name: str = Body(...),
    file_size: int = Body(...),
    mime_type: str = Body(...),
    session_id: UUID = Depends(cookie),
    db=Depends(get_db)
):
    """
    Initiates a new resumable upload.
    Creates a record in the database and returns a unique upload ID.
    """
    session_data: SessionData = await verifier(request)
    if not session_data:
        raise HTTPException(status_code=401, detail="User not authenticated")

    upload_id = uuid4()
    expires_at = datetime.utcnow() + timedelta(days=7)  # Uploads expire in 7 days
    upload_path = os.path.join(TEMP_UPLOAD_DIR, str(upload_id))

    try:
        with db.cursor() as cur:
            # Create a temporary directory for this upload's chunks
            try:
                os.makedirs(upload_path, exist_ok=True)
            except OSError as e:
                logger.error(f"Failed to create temporary directory {upload_path}: {e}")
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to create upload directory.")

            cur.execute(
                """
                INSERT INTO file_upload_sessions (id, user_id, file_name, file_size, mime_type, status, storage_path, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (str(upload_id), session_data.user_id, file_name, file_size, mime_type, 'in_progress', upload_path, expires_at)
            )
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create upload session for user {session_data.user_id}: {e}")
        # If we are here, it's likely a DB error, but we should ensure the directory is cleaned up if it was created.
        if os.path.exists(upload_path):
            try:
                os.rmdir(upload_path)
            except OSError as cleanup_e:
                logger.error(f"Failed to clean up directory {upload_path} after a failed transaction: {cleanup_e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not initiate upload session.")

    return {"upload_id": str(upload_id)}

@router.get("/uploads/status", tags=["Uploads"])
async def get_upload_status(
    request: Request,
    file_name: str,
    session_id: UUID = Depends(cookie),
    db=Depends(get_db)
):
    """
    Checks if a resumable upload exists for a given file name.
    """
    session_data: SessionData = await verifier(request)
    if not session_data:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT id, uploaded_size FROM file_upload_sessions
                WHERE user_id = %s AND file_name = %s AND status = 'in_progress'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_data.user_id, file_name)
            )
            record = cur.fetchone()
    except Exception as e:
        logger.error(f"Could not query upload status for user {session_data.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve upload status.")

    if record:
        return {"resumable": True, "upload_id": record["id"], "uploaded_size": record["uploaded_size"]}
    else:
        return {"resumable": False}

@router.patch("/uploads/{upload_id}", tags=["Uploads"])
async def upload_chunk(
    upload_id: UUID,
    request: Request,
    chunk: UploadFile = File(...),
    session_id: UUID = Depends(cookie),
    db=Depends(get_db)
):
    """
    Uploads a chunk of a file for an existing upload session.
    """
    session_data: SessionData = await verifier(request)
    if not session_data:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT storage_path, uploaded_size, file_size FROM file_upload_sessions WHERE id = %s AND user_id = %s AND status = 'in_progress' FOR UPDATE",
                (str(upload_id), session_data.user_id)
            )
            record = cur.fetchone()
            db.commit()
    except Exception as e:
        logger.error(f"Database error when fetching upload session {upload_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

    if not record:
        raise HTTPException(status_code=404, detail="Upload session not found or not in progress.")

    storage_path = record["storage_path"]
    current_size = record["uploaded_size"]
    total_size = record["file_size"]
    
    chunk_content = await chunk.read()
    chunk_size = len(chunk_content)

    if current_size + chunk_size > total_size:
        raise HTTPException(status_code=400, detail="Chunk exceeds total file size.")

    chunk_offset = request.headers.get("content-range")
    if not chunk_offset:
         raise HTTPException(status_code=400, detail="Content-Range header is required.")
    
    start_byte = int(float(chunk_offset.split(" ")[1].split("-")[0]))


    temp_chunk_path = os.path.join(storage_path, f"chunk_{start_byte}")
    async with aiofiles.open(temp_chunk_path, "wb") as f:
        await f.write(chunk_content)

    new_uploaded_size = current_size + chunk_size

    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE file_upload_sessions SET uploaded_size = %s WHERE id = %s",
                (new_uploaded_size, str(upload_id))
            )
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update uploaded size for session {upload_id}: {e}")
        # Clean up chunk?
        raise HTTPException(status_code=500, detail="Failed to update upload progress.")

    return {"uploaded_size": new_uploaded_size, "total_size": total_size}

@router.post("/uploads/{upload_id}/finish", tags=["Uploads"])
async def finish_upload(
    upload_id: UUID,
    request: Request,
    session_id: UUID = Depends(cookie),
    db=Depends(get_db)
):
    """
    Finalizes a resumable upload.
    Combines chunks, moves the file to its final location, and triggers analysis.
    """
    session_data: SessionData = await verifier(request)
    if not session_data:
        raise HTTPException(status_code=401, detail="User not authenticated")

    record = None
    chunk_dir = None
    chunk_files = []

    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Lock the row for the duration of the transaction
            cur.execute(
                "SELECT * FROM file_upload_sessions WHERE id = %s AND user_id = %s AND status = 'in_progress' FOR UPDATE",
                (str(upload_id), session_data.user_id)
            )
            record = cur.fetchone()

            if not record:
                # This rollback is for the case where the session is not found, to release any potential lock.
                db.rollback()
                raise HTTPException(status_code=404, detail="Upload session not found or already completed.")

            if record["uploaded_size"] != record["file_size"]:
                db.rollback()
                raise HTTPException(status_code=400, detail="File upload is not complete.")

            # --- File Combination ---
            user_folder = create_user_folder(session_data.user_id, session_data.username)
            final_file_path = os.path.join(user_folder, record["file_name"])
            chunk_dir = record["storage_path"]
            
            # Defensive check: if the chunk directory doesn't exist, create it.
            # This can happen if no chunks were sent (e.g. empty file).
            if not os.path.isdir(chunk_dir):
                logger.warning(f"Chunk directory {chunk_dir} was missing for upload {upload_id}. Recreating it.")
                os.makedirs(chunk_dir, exist_ok=True)

            try:
                chunk_files = sorted(os.listdir(chunk_dir), key=lambda x: int(x.split('_')[1]))
                
                async with aiofiles.open(final_file_path, "wb") as final_file:
                    for chunk_filename in chunk_files:
                        chunk_path = os.path.join(chunk_dir, chunk_filename)
                        async with aiofiles.open(chunk_path, "rb") as chunk_file:
                            await final_file.write(await chunk_file.read())

            except (IOError, FileNotFoundError) as e:
                logger.error(f"Error combining chunks for upload {upload_id}: {e}")
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to assemble file.")

            # --- Text Extraction from Assembled File ---
            extracted_text = ""
            try:
                file_ext = os.path.splitext(record["file_name"])[1].lower()
                logger.info(f"Processing file {record['file_name']} with extension {file_ext}")

                if file_ext == '.pdf':
                    _, extracted_text = process_pdf(final_file_path)
                elif file_ext == '.docx':
                    _, extracted_text = process_docx(final_file_path)
                elif file_ext == '.doc':
                    _, extracted_text = process_doc(final_file_path)
                elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff']:
                    _, extracted_text = process_image(final_file_path)
                else:
                    logger.warning(f"Unsupported file type for text extraction: {file_ext}")

                logger.info(f"Successfully extracted text from {record['file_name']}. Character count: {len(extracted_text)}")
                # Here, you would typically pass the `extracted_text` to the next step of your analysis pipeline.
                # For now, we're just logging it.
            
            except Exception as e:
                logger.error(f"Text extraction failed for {upload_id}: {e}")
                db.rollback()
                # Decide if this should be a fatal error. Maybe the analysis can proceed without text.
                # For now, we'll treat it as a failure.
                raise HTTPException(status_code=500, detail="File text extraction failed.")


            # --- Analysis Pipeline (External API) ---
            try:
                logger.info(f"File {record['file_name']} assembled. Starting analysis pipeline...")
                oss_url = oss_upload(final_file_path, record['file_name'])
                basename, _ = os.path.splitext(record['file_name'])
                report_name = f"{basename}.json"
                output_filename = os.path.join(user_folder, report_name)
                api_dep(oss_url, record['file_name'], output_filename)
                logger.info(f"Analysis pipeline triggered for {record['file_name']}.")
            except Exception as e:
                logger.error(f"Analysis pipeline failed for {upload_id}: {e}")
                db.rollback()
                raise HTTPException(status_code=500, detail="File analysis failed.")

            # --- Database Finalization ---
            # 1. Create a record in the main `files` table
            cur.execute(
                """
                INSERT INTO files (user_id, file_name, uploaded_at, analyzed_at, report_name)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (session_data.user_id, record["file_name"], datetime.utcnow(), datetime.utcnow(), report_name)
            )
            file_id = cur.fetchone()[0]

            # 2. Update the upload session
            cur.execute(
                "UPDATE file_upload_sessions SET status = 'completed', final_file_id = %s WHERE id = %s",
                (file_id, str(upload_id))
            )
            
            # If everything is successful, commit the entire transaction
            db.commit()

    except HTTPException:
        # Re-raise HTTPException to be handled by FastAPI
        if db:
            db.rollback()
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during upload finalization for {upload_id}: {e}")
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred during finalization.")
    finally:
        # --- Cleanup ---
        if chunk_dir and os.path.exists(chunk_dir):
            try:
                shutil.rmtree(chunk_dir)
                logger.info(f"Successfully cleaned up temporary directory {chunk_dir}.")
            except OSError as e:
                logger.warning(f"Failed to clean up temporary directory {chunk_dir} for upload {upload_id}: {e}")

    return {"message": "File uploaded and analysis started successfully.", "filename": record["file_name"]}

# --- Anonymous Upload for Login Flow ---
@router.post("/upload/anonymous", status_code=200, tags=["Uploads"])
async def anonymous_upload_for_login(response: Response, file: UploadFile = File(...)):
    """
    Handles anonymous file uploads for the 'upload-then-login' flow.
    Temporarily stores the file and sets a cookie to retrieve it after login.
    """
    try:
        # Generate a secure, unique filename for the temporary file
        temp_file_id = uuid4().hex
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"{temp_file_id}{file_extension}"
        temp_filepath = os.path.join(TEMP_UPLOAD_DIR, temp_filename)

        # Save the file asynchronously
        async with aiofiles.open(temp_filepath, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Set a secure cookie with the temporary file info
        cookie_max_age = 3600  # 1 hour
        response.set_cookie(
            key="temp_file_id",
            value=temp_file_id,
            max_age=cookie_max_age,
            httponly=True,
            samesite="lax"
        )
        safe_original_filename = urllib.parse.quote(file.filename)
        response.set_cookie(
            key="temp_file_original_name",
            value=safe_original_filename,
            max_age=cookie_max_age,
            httponly=True,
            samesite="lax"
        )

        return {"detail": "File uploaded successfully. Please log in to continue."}

    except Exception as e:
        logger.error(f"Anonymous upload failed: {e}")
        raise HTTPException(status_code=500, detail="File upload failed.")