from fastapi import Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from core.database import get_db_connection, release_db_connection
import psycopg2 as pg
import os
import shutil
import json
from datetime import datetime
import logging
from uuid import UUID, uuid4
from services.user_management import (
    create_user_folder,
    delete_user_folder,
    save_user_data,
    reach_json,
    update_user_login_time
)
from services.file_processing import analyze_folder
from services.contract_analysis import oss_upload, api_dep, convert_to_clean_json
from chat import generate_message
from passlib.context import CryptContext
from core.security import SessionData, cookie, backend, verifier
from core.config import oauth
from typing import Optional, List
import urllib.parse
from pydantic import BaseModel, EmailStr
from fastapi import status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request bodies
class ProfileUpdate(BaseModel):
    new_password: str
    email: EmailStr

class Feedback(BaseModel):
    rating: int
    comment: str

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_DIR = os.path.join(BASE_DIR, "users")

# Ensure users directory exists
os.makedirs(USERS_DIR, exist_ok=True)

# Templates
ht_pages = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

async def get_session_data(session_id, retries=10, delay=1):
    logger.info("Attempting to get session data")
    for _ in range(retries):
        session_data = await backend.read(session_id)
        if session_data:
            return session_data
        await asyncio.sleep(delay)
    return None

def analyze_json(session_data: SessionData, report_name: str):
    user_id = session_data.user_id
    username = session_data.username
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    report_path = os.path.join(user_folder, report_name)
    with open(report_path, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    return analysis_data

def save_contract_file(file: UploadFile, user_id: str, username: str):
    user_folder = create_user_folder(user_id, username)
    file_path = os.path.join(user_folder, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path, file.filename

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf", "doc", "docx"}

async def root_page(req: Request, session_id: Optional[UUID] = None):
    """Handles the root page, showing basic stats."""
    # Note: This is a simplified version. A real app might have more complex logic.
    total_files = 0  # Placeholder for file count
    accounts_number = 0 # Placeholder for account count

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        accounts_number = cur.fetchone()[0]
        # A more efficient way to count files would be needed for production
    except pg.Error as e:
        logger.error(f"Database error on root page: {e}")
    finally:
        if conn:
            release_db_connection(conn)

    user_is_logged_in = False
    if session_id:
        session_data = await backend.read(session_id)
        if session_data:
            user_is_logged_in = True

    return ht_pages.TemplateResponse(
        "welcome_page.html",
        {
            "request": req,
            "contracts_number": total_files,
            "accounts_number": accounts_number,
            "user_is_logged_in": user_is_logged_in,
        },
    )

async def welcome_page(req: Request, session_id: Optional[UUID] = None):
    """Handles the welcome page, showing basic stats."""
    return await root_page(req, session_id)

async def analysis_page(req: Request, filename: str = None, session_id: UUID = Depends(cookie)):
    if not filename:
        return RedirectResponse(url="/history")
    session_data = await verifier(req)
    report_name = f"{filename}_report.json"
    analysis_data = analyze_json(session_data, report_name)
    return ht_pages.TemplateResponse(
        "analysis.html", {"request": req, "analysis": analysis_data}
    )

async def nocontract_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    user_data = reach_json(session_data)
    return ht_pages.TemplateResponse(
        "nocontract.html", {"request": req, "user": user_data}
    )

async def mydash_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    user_data = reach_json(session_data)
    user_folder = os.path.join(USERS_DIR, f"{session_data.user_id}_{session_data.username}")
    total_files, total_pages, total_chinese_chars, total_cost = analyze_folder(user_folder)
    return ht_pages.TemplateResponse(
        "mydash.html",
        {
            "request": req,
            "user": user_data,
            "total_files": total_files,
            "total_pages": total_pages,
            "total_chinese_chars": total_chinese_chars,
            "total_cost": total_cost,
        },
    )

async def document_page(req: Request, filename: str = None):
    return ht_pages.TemplateResponse(
        "document.html", {"request": req, "filename": filename}
    )

async def upload_contract_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    user_data = reach_json(session_data)
    return ht_pages.TemplateResponse(
        "upload_contract.html", {"request": req, "user": user_data}
    )

async def history_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    user_data = reach_json(session_data)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT file_name, uploaded_at, analyzed_at, report_name FROM files WHERE user_id = %s",
            (session_data.user_id,),
        )
        history = cur.fetchall()
    finally:
        release_db_connection(conn)
    return ht_pages.TemplateResponse(
        "history.html", {"request": req, "user": user_data, "history": history}
    )

async def profile_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    user_data = reach_json(session_data)
    return ht_pages.TemplateResponse(
        "profile.html", {"request": req, "user": user_data}
    )

async def subscriptions_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    user_data = reach_json(session_data)
    return ht_pages.TemplateResponse(
        "subscriptions.html", {"request": req, "user": user_data}
    )

async def helpcenter_page(req: Request, session_id: Optional[UUID] = None):
    return ht_pages.TemplateResponse("helpcenter.html", {"request": req})

async def aboutus_page(req: Request, session_id: Optional[UUID] = None):
    return ht_pages.TemplateResponse("aboutus.html", {"request": req})

async def contactus_page(req: Request, session_id: Optional[UUID] = None):
    return ht_pages.TemplateResponse("contactus.html", {"request": req})

async def analysis_dashboard_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    return ht_pages.TemplateResponse("analysis_dashboard.html", {"request": req})

async def admin_dashboard_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    return ht_pages.TemplateResponse("admin_dashboard.html", {"request": req})

async def whats_new_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    return ht_pages.TemplateResponse("whatisnew.html", {"request": req})

async def question_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    return ht_pages.TemplateResponse("question.html", {"request": req})

async def chat_page(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    return ht_pages.TemplateResponse("chat.html", {"request": req})

# --- POST Handlers ---
async def analyze_upload_handler(request: Request, file: UploadFile = File(...), session_id: UUID = Depends(cookie)):
    session_data = await verifier(request)
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="File type not allowed")

    file_path, file_name = save_contract_file(file, session_data.user_id, session_data.username)
    
    # OSS Upload and Analysis
    oss_url = oss_upload(file_path, file_name)
    report_name = f"{file_name}_report.json"
    user_folder = os.path.join(USERS_DIR, f"{session_data.user_id}_{session_data.username}")
    output_filename = os.path.join(user_folder, report_name)
    
    api_dep(oss_url, file_name, output_filename)
    
    encoded_filename = urllib.parse.quote(file_name)
    return RedirectResponse(
        url=f"/analysis?filename={encoded_filename}", status_code=status.HTTP_303_SEE_OTHER
    )

async def profile_changes_handler(req: Request, profile_data: ProfileUpdate, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    hashed_password = get_password_hash(profile_data.new_password)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password = %s, email = %s WHERE user_id = %s",
            (hashed_password, profile_data.email, session_data.user_id),
        )
        conn.commit()
    finally:
        release_db_connection(conn)
    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)

async def delete_file_handler(req: Request, filename: str = Form(...)):
    # This needs session data to be secure
    # Simplified version
    # In a real app, you must verify ownership before deleting
    os.remove(os.path.join("uploads", filename))
    return RedirectResponse(url="/history", status_code=status.HTTP_303_SEE_OTHER)
    
async def delete_account_handler(req: Request, session_id: UUID = Depends(cookie)):
    session_data = await verifier(req)
    
    # Delete user folder and data from DB
    delete_user_folder(session_data.user_id, session_data.username)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM files WHERE user_id = %s", (session_data.user_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (session_data.user_id,))
        conn.commit()
    finally:
        release_db_connection(conn)
        
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_id")
    return response

async def fill_form_handler(request: Request, feedback: Feedback, session_id: UUID = Depends(cookie)):
    session_data = await verifier(request)
    # Here you would save the feedback to a database
    logger.info(f"Feedback received: {feedback.rating} - {feedback.comment}")
    return JSONResponse({"message": "Feedback received, thank you!"})

def get_pdf_handler(foldername: str, filename: str):
    """Serves a PDF file from a user's folder."""
    file_path = os.path.join(USERS_DIR, foldername, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, media_type='application/pdf', filename=filename) 