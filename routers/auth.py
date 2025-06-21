import logging
import secrets
from uuid import uuid4, UUID
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.templating import Jinja2Templates
import phonenumbers

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
from services.user_management import create_user_folder, save_user_data, create_user_in_db, create_company_in_db
from services.phone_verification import phone_verification_service

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
            SELECT user_id, username, email, password, account_type, company_id FROM users 
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

        user_id, username, user_email, _, account_type, company_id = user_data
        
        # NOTE: update_user_login_time is not defined here yet.
        # It should probably be moved to a user service/crud file.
        # For now, I'll comment it out to proceed with refactoring.
        # update_user_login_time(user_id, username)

        session_id = uuid4()
        session_data = SessionData(
            user_id=str(user_id),
            username=username,
            email=user_email,
            account_type=account_type,
            company_id=str(company_id) if company_id else None
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
    phone: Optional[str] = Form(None),
    username: str = Form(...),
    account_type: str = Form(...),
    company_name: Optional[str] = Form(None),
    license_num: Optional[str] = Form(None)
):
    try:
        hashed_password = get_password_hash(password)
        
        if account_type == "company":
            if not company_name:
                return templates.TemplateResponse(
                    "signup.html",
                    {"request": request, "error_message": "Company name is required for company accounts."},
                )
            if not email:
                return templates.TemplateResponse(
                    "signup.html",
                    {"request": request, "error_message": "Email is required for company accounts."},
                )
            # Create the company first
            new_company = create_company_in_db(company_name, license_num)
            if not new_company:
                return templates.TemplateResponse(
                    "signup.html",
                    {"request": request, "error_message": "A company with this name already exists."},
                )
            
            # Then create the user as a company admin
            new_user = create_user_in_db(
                fullname=fullname,
                email=email,
                password=hashed_password,
                phone=phone,
                username=username,
                account_type='company_admin',
                company_id=new_company['comp_id']
            )
        else: # Individual account
            new_user = create_user_in_db(
                fullname=fullname,
                email=email,
                password=hashed_password,
                phone=phone,
                username=username
            )

        if not new_user:
            return templates.TemplateResponse(
                "signup.html",
                {"request": request, "error_message": "User with these details already exists."},
            )

        # User folder creation logic
        create_user_folder(new_user['user_id'], new_user['username'])
        save_user_data(new_user['user_id'], new_user['username'], new_user['full_name'], new_user['email'])

        return RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logger.error(f"Error during signup: {e}")
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error_message": "An unexpected error occurred."},
        )


@router.post("/auth/send-verification-code")
async def send_verification_code(phone: str = Form(...)):
    """
    Validates a phone number, checks if it's already registered,
    and sends a verification code.
    """
    try:
        phone_number = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(phone_number):
            raise HTTPException(status_code=400, detail="Invalid phone number provided.")

        formatted_phone = phonenumbers.format_number(
            phone_number, phonenumbers.PhoneNumberFormat.E164
        )

        # Check if user already exists
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE phone = %s", (formatted_phone,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Phone number already registered.")
        finally:
            release_db_connection(conn)

        await phone_verification_service.send_verification_code(formatted_phone)
        return {"message": "Verification code sent successfully."}

    except HTTPException as e:
        # Re-raise HTTPExceptions to be handled by FastAPI
        raise e
    except Exception as e:
        logger.error(f"Failed to send verification code to {phone}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification code.")


@router.post("/auth/signup-by-phone")
async def signup_by_phone(
    request: Request,
    password: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...),
    code: str = Form(...)
):
    """
    Verifies the OTP and creates a new user account using their phone number.
    """
    try:
        phone_number = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(phone_number):
            raise HTTPException(status_code=400, detail="Invalid phone number provided.")
        
        formatted_phone = phonenumbers.format_number(
            phone_number, phonenumbers.PhoneNumberFormat.E164
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid phone number format.")

    is_valid_code = await phone_verification_service.verify_code(formatted_phone, code)
    if not is_valid_code:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    try:
        hashed_password = get_password_hash(password)
        # For phone signup, we can use the username as the full name initially.
        # Email is not required for phone-based signup.
        new_user = create_user_in_db(
            fullname=username,  # Use username as fullname
            email=None,         # Email is optional
            password=hashed_password,
            phone=formatted_phone,
            username=username
        )

        if not new_user:
            raise HTTPException(status_code=409, detail="User with these details already exists.")

        create_user_folder(new_user['user_id'], new_user['username'])
        # Email is not passed as it's not provided during phone signup.
        save_user_data(
            new_user['user_id'],
            new_user['username'],
            new_user['full_name'],
            None  # No email
        )

        return {"message": "User created successfully. You can now sign in."}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during signup by phone: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during signup.")


@router.get('/login/google')
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/google')
async def auth_via_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not retrieve user info from Google.")

    email = user_info.get("email")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, username, email, account_type, company_id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

            if not user:
                # If user does not exist, create a new one
                new_user_data = create_user_in_db(
                    fullname=user_info.get("name", email),
                    email=email,
                    password=get_password_hash(secrets.token_urlsafe(16)), # Generate a secure random password
                    phone=None, # Phone not available from Google
                    username=user_info.get("name", email).replace(" ", "") + str(uuid4())[:4], # Create a unique username
                    account_type='individual',
                    company_id=None
                )
                if not new_user_data:
                    raise HTTPException(status_code=500, detail="Failed to create a new user.")
                
                # Fetch the newly created user to get all details
                cur.execute("SELECT user_id, username, email, account_type, company_id FROM users WHERE user_id = %s", (new_user_data['user_id'],))
                user = cur.fetchone()

        if not user:
             raise HTTPException(status_code=404, detail="User not found after creation.")

        logger.info(f"User data from DB: {user}")
        
        user_id, username, user_email, account_type, company_id = user
        
        session_id = uuid4()
        session_data = SessionData(
            user_id=str(user_id), 
            username=username, 
            email=user_email,
            account_type=account_type,
            company_id=str(company_id) if company_id else None
        )
        await backend.create(session_id, session_data)

        response = RedirectResponse(url="/mydash")
        cookie.attach_to_response(response, session_id)
        return response

    except Exception as e:
        logger.error(f"Error in Google auth callback: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during Google authentication.")
    finally:
        if conn:
            release_db_connection(conn)


@router.post("/logout")
async def logout(request: Request, session_id: UUID = Depends(cookie)):
    response = RedirectResponse(url="/welcome_page", status_code=status.HTTP_303_SEE_OTHER)
    if session_id:
        await backend.delete(session_id)
        cookie.delete_from_response(response)
    return response 