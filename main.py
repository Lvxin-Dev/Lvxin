import logging
import os
from fastapi import FastAPI, Request, File, UploadFile, Form, Depends
from typing import Optional
from uuid import UUID
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from uuid import UUID

from routers import auth
from core.security import cookie, SessionData, backend, optional_cookie
from utils import (
    root_page,
    welcome_page,
    analysis_page,
    nocontract_page,
    mydash_page,
    document_page,
    upload_contract_page,
    history_page,
    profile_page,
    subscriptions_page,
    helpcenter_page,
    aboutus_page,
    contactus_page,
    analysis_dashboard_page,
    admin_dashboard_page,
    whats_new_page,
    question_page,
    chat_page,
    analyze_upload_handler,
    profile_changes_handler,
    delete_file_handler,
    delete_account_handler,
    fill_form_handler,
    get_pdf_handler,
    ProfileUpdate,
    Feedback,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(title="Lvxin API")

# --- Middleware ---
# Important: The secret key should be loaded from a secure source, e.g., environment variables
app.add_middleware(SessionMiddleware, secret_key="your-super-secret-key")

# --- Routers ---
app.include_router(auth.router)

# --- Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- HTML Page Routes ---
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def handle_root(req: Request, session_id: Optional[UUID] = Depends(optional_cookie, use_cache=False)):
    return await root_page(req, session_id)

@app.get("/welcome_page", response_class=HTMLResponse, tags=["Pages"])
async def handle_welcome(req: Request, session_id: Optional[UUID] = Depends(optional_cookie, use_cache=False)):
    return await welcome_page(req, session_id)

@app.get("/analysis", response_class=HTMLResponse, tags=["Pages"])
async def handle_analysis(req: Request, filename: str = None, session_id: UUID = Depends(cookie)):
    return await analysis_page(req, filename, session_id)

@app.get("/nocontract", response_class=HTMLResponse, tags=["Pages"])
async def handle_nocontract(req: Request, session_id: UUID = Depends(cookie)):
    return await nocontract_page(req, session_id)

@app.get("/mydash", response_class=HTMLResponse, tags=["Pages"])
async def handle_mydash(req: Request, session_id: UUID = Depends(cookie)):
    return await mydash_page(req, session_id)

@app.get("/document", response_class=HTMLResponse, tags=["Pages"])
async def handle_document(req: Request, filename: str = None):
    return await document_page(req, filename)

@app.get("/upload_contract", response_class=HTMLResponse, tags=["Pages"])
async def handle_upload_contract(req: Request, session_id: UUID = Depends(cookie)):
    return await upload_contract_page(req, session_id)

@app.get("/history", response_class=HTMLResponse, tags=["Pages"])
async def handle_history(req: Request, session_id: UUID = Depends(cookie)):
    return await history_page(req, session_id)

@app.get("/profile", response_class=HTMLResponse, tags=["Pages"])
async def handle_profile(req: Request, session_id: UUID = Depends(cookie)):
    return await profile_page(req, session_id)

@app.get("/subscriptions", response_class=HTMLResponse, tags=["Pages"])
async def handle_subscriptions(req: Request, session_id: UUID = Depends(cookie)):
    return await subscriptions_page(req, session_id)

@app.get("/helpcenter", response_class=HTMLResponse, tags=["Pages"])
async def handle_helpcenter(req: Request, session_id: Optional[UUID] = Depends(optional_cookie, use_cache=False)):
    return await helpcenter_page(req, session_id)

@app.get("/aboutus", response_class=HTMLResponse, tags=["Pages"])
async def handle_aboutus(req: Request, session_id: Optional[UUID] = Depends(optional_cookie, use_cache=False)):
    return await aboutus_page(req, session_id)

@app.get("/contactus", response_class=HTMLResponse, tags=["Pages"])
async def handle_contactus(req: Request, session_id: Optional[UUID] = Depends(optional_cookie, use_cache=False)):
    return await contactus_page(req, session_id)

@app.get("/analysis_dashboard", response_class=HTMLResponse, tags=["Pages"])
async def handle_analysis_dashboard(req: Request, session_id: UUID = Depends(cookie)):
    return await analysis_dashboard_page(req, session_id)

@app.get("/admin_dashboard", response_class=HTMLResponse, tags=["Pages"])
async def handle_admin_dashboard(req: Request, session_id: UUID = Depends(cookie)):
    return await admin_dashboard_page(req, session_id)

@app.get("/whats-new", response_class=HTMLResponse, tags=["Pages"])
async def handle_whats_new(req: Request, session_id: UUID = Depends(cookie)):
    return await whats_new_page(req, session_id)

@app.get("/question", response_class=HTMLResponse, tags=["Pages"])
async def handle_question(req: Request, session_id: UUID = Depends(cookie)):
    return await question_page(req, session_id)

@app.get("/chat", response_class=HTMLResponse, tags=["Pages"])
async def handle_chat(req: Request, session_id: UUID = Depends(cookie)):
    return await chat_page(req, session_id)


# --- API Endpoint Routes ---
@app.post("/analyze_upload", tags=["Actions"])
async def handle_analyze_upload(request: Request, file: UploadFile = File(...), session_id: UUID = Depends(cookie)):
    return await analyze_upload_handler(request, file, session_id)

@app.post("/profile_changes", tags=["Actions"])
async def handle_profile_changes(req: Request, profile_data: ProfileUpdate, session_id: UUID = Depends(cookie)):
    return await profile_changes_handler(req, profile_data, session_id)

@app.post("/delete_file", tags=["Actions"])
async def handle_delete_file(req: Request, filename: str = Form(...)):
    return await delete_file_handler(req, filename)
    
@app.post("/delete_account", tags=["Actions"])
async def handle_delete_account(req: Request, session_id: UUID = Depends(cookie)):
    return await delete_account_handler(req, session_id)

@app.post("/fill_form", tags=["Actions"])
async def handle_fill_form(request: Request, feedback: Feedback, session_id: UUID = Depends(cookie)):
    return await fill_form_handler(request, feedback, session_id)

@app.get("/pdf/{foldername}/{filename}", tags=["Files"])
async def handle_get_pdf(foldername: str, filename: str):
    return get_pdf_handler(foldername, filename)


# --- Main Entry Point ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)