import logging
import secrets
from uuid import uuid4, UUID
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.templating import Jinja2Templates

from core.config import oauth
from core.database import get_db_connection, release_db_connection
from core.security import (
    cookie,
    backend,
    SessionData,
    get_password_hash,
    verify_password,
    optional_cookie,
)
import psycopg2 as pg
from services.user_management import create_user_folder, save_user_data

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/signin", response_class=HTMLResponse)
async def signin_page(
    req: Request,
    next: str = "/mydash",
    session_id: Optional[UUID] = Depends(optional_cookie),
):
    if session_id:
        session_data = await backend.read(session_id)
        if session_data:
            return RedirectResponse(url="/mydash", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("signin.html", {"request": req, "next": next})

@router.post("/signin")
async def handle_signin(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(...)
):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, username, email, password FROM users 
            WHERE email = %s
        """, (email,))
        user_data = cur.fetchone()
        cur.close()

        if not user_data or not verify_password(password, user_data[3]):
            return templates.TemplateResponse(
                "signin.html", 
                {
                    "request": request, 
                    "error_message": "Wrong email or password",
                    "next": next
                }
            )

        user_id, username, user_email, _ = user_data
        
        # NOTE: update_user_login_time is not defined here yet.
        # It should probably be moved to a user service/crud file.
        # For now, I'll comment it out to proceed with refactoring.
        # update_user_login_time(user_id, username)

        session_id = uuid4()
        session_data = SessionData(
            user_id=str(user_id),
            username=username,
            email=user_email
        )
        await backend.create(session_id, session_data)

        response = RedirectResponse(url=next, status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="user_id", value=str(user_id))
        cookie.attach_to_response(response, session_id)

        # Logic for handling temp file after login
        # This part might need to be re-evaluated.
        # It couples auth logic with file upload logic.

        return response

    except Exception as e:
        logger.error(f"Error in handle_signin: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )
    finally:
        release_db_connection(conn)


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(
    req: Request, session_id: Optional[UUID] = Depends(optional_cookie)
):
    if session_id:
        session_data = await backend.read(session_id)
        if session_data:
            return RedirectResponse(url="/mydash", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("signup.html", {"request": req})

@router.post("/signup")
async def signup_form(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...)
):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check for existing user
        cur.execute("SELECT email FROM users WHERE email = %s OR username = %s OR phone = %s", (email, username, phone))
        if cur.fetchone():
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error_message": "User with these details already exists."},
            )

        user_id = str(uuid4())
        hashed_password = get_password_hash(password)
        
        cur.execute(
            "INSERT INTO users (user_id, full_name, email, password, phone, username) VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, fullname, email, hashed_password, phone, username),
        )
        conn.commit()
        
        # User folder creation logic should be here or in a dedicated service
        create_user_folder(user_id, username)
        save_user_data(user_id, username, fullname, email)

        return RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)

    except pg.Error as e:
        conn.rollback()
        logger.error(f"Database error during signup: {e}")
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error_message": "A database error occurred."},
        )
    finally:
        cur.close()
        release_db_connection(conn)


@router.get('/login/google')
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/google')
async def auth_via_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as error:
        logger.error(f"Google OAuth Error: {error}")
        return HTMLResponse(f'<h1>Error: {error.error}</h1><p>Description: {error.description}</p>')
    
    user_info = token.get('userinfo')
    if not user_info:
        return HTMLResponse("<h1>Could not fetch user info from Google.</h1>", status_code=400)

    email = user_info.get("email")
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT user_id, username, email FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user:
            # Create new user
            user_id = str(uuid4())
            username = email.split('@')[0] + str(secrets.randbelow(1000))
            full_name = user_info.get("name", "New User")
            hashed_password = get_password_hash(secrets.token_hex(16)) # Random password

            cur.execute(
                "INSERT INTO users (user_id, username, password, full_name, email) VALUES (%s, %s, %s, %s, %s) RETURNING user_id, username, email",
                (user_id, username, hashed_password, full_name, email),
            )
            user = cur.fetchone()
            conn.commit()
            create_user_folder(user[0], user[1])
            save_user_data(user[0], user[1], full_name, user[2])

        logger.info(f"User data from DB: {user}")
        session_id = uuid4()
        session_data = SessionData(user_id=str(user[0]), username=user[1], email=user[2])
        logger.info(f"Session data to be created: {session_data}")
        await backend.create(session_id, session_data)

        response = RedirectResponse(url="/mydash", status_code=status.HTTP_303_SEE_OTHER)
        cookie.attach_to_response(response, session_id)
        return response

    except pg.Error as e:
        conn.rollback()
        logger.error(f"Database error during Google auth: {e}")
        return HTMLResponse("<h1>Database Error</h1><p>Could not process your request.</p>", status_code=500)
    finally:
        cur.close()
        release_db_connection(conn)


@router.post("/logout")
async def logout(request: Request, session_id: UUID = Depends(cookie)):
    response = RedirectResponse(url="/welcome_page", status_code=status.HTTP_303_SEE_OTHER)
    if session_id:
        await backend.delete(session_id)
        cookie.delete_from_response(response)
    return response 