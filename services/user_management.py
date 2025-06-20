import os
import json
import shutil
import logging
from datetime import datetime
from typing import Optional
from core.security import SessionData
from core.database import get_db_connection, release_db_connection
import psycopg2 as pg
from uuid import uuid4

logger = logging.getLogger(__name__)

USERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users")
if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR)

def create_user_in_db(
    fullname: str,
    email: Optional[str],
    password: str,
    phone: Optional[str],
    username: str,
    account_type: str = 'individual',
    company_id: Optional[str] = None
) -> Optional[dict]:
    """Create a new user in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Build the query dynamically to handle optional phone numbers
        query = "SELECT email FROM users WHERE email = %s OR username = %s"
        params = [email, username]
        if phone:
            query += " OR phone = %s"
            params.append(phone)
            
        cur.execute(query, tuple(params))
        if cur.fetchone():
            return None  # User already exists

        user_id = str(uuid4())
        
        cur.execute(
            "INSERT INTO users (user_id, full_name, email, password, phone, username, account_type, company_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING user_id, username, email, full_name, account_type, company_id",
            (user_id, fullname, email, password, phone, username, account_type, company_id),
        )
        new_user = cur.fetchone()
        conn.commit()

        if new_user:
            return {
                "user_id": new_user[0],
                "username": new_user[1],
                "email": new_user[2],
                "full_name": new_user[3],
                "account_type": new_user[4],
                "company_id": new_user[5]
            }
        return None
    except pg.Error as e:
        conn.rollback()
        logger.error(f"Database error during user creation: {e}")
        raise
    finally:
        cur.close()
        release_db_connection(conn)

def create_company_in_db(name: str, license_num: Optional[str]) -> Optional[dict]:
    """Create a new company in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM companies WHERE name = %s", (name,))
        if cur.fetchone():
            return None # Company already exists
        
        comp_id = str(uuid4())
        cur.execute(
            "INSERT INTO companies (comp_id, name, license) VALUES (%s, %s, %s) RETURNING comp_id, name",
            (comp_id, name, license_num)
        )
        new_company = cur.fetchone()
        conn.commit()
        if new_company:
            return {
                "comp_id": new_company[0],
                "name": new_company[1]
            }
        return None
    except pg.Error as e:
        conn.rollback()
        logger.error(f"Database error during company creation: {e}")
        raise
    finally:
        cur.close()
        release_db_connection(conn)

def create_user_folder(user_id: str, username: str) -> str:
    """Create a folder for the user with their ID and username"""
    folder_name = f"{user_id}_{username}"
    user_folder = os.path.join(USERS_DIR, folder_name)
    
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    return user_folder

def delete_user_folder(user_id: str, username: str) -> bool:
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

def save_user_data(user_id: str, username: str, full_name: str, email: Optional[str], file_url: Optional[str] = None, filename: Optional[str] = None, api_url: Optional[str] = None):
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

def reach_json(session_data: SessionData):
    user_id = session_data.user_id
    username = session_data.username
    
    user_folder = os.path.join(USERS_DIR, f"{user_id}_{username}")
    file_name = f"{user_id}_{username}.json"
    file_path = os.path.join(user_folder, file_name)
    
    if not os.path.exists(file_path):
        logger.warning(f"User data file not found for user {user_id}. Recreating it.")
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT full_name, email FROM users WHERE user_id = %s", (user_id,))
            user_db_data = cur.fetchone()
            if user_db_data:
                full_name, email = user_db_data
                return save_user_data(user_id, username, full_name, email)
            else:
                logger.error(f"Could not find user {user_id} in database to recreate data file.")
                return { "user_id": user_id, "username": username, "full_name": "Unknown", "email": session_data.email }
        except Exception as e:
            logger.error(f"Database error while recreating user file for {user_id}: {e}")
            return { "user_id": user_id, "username": username, "full_name": "Unknown", "email": session_data.email }
        finally:
            if conn:
                release_db_connection(conn)

    with open(file_path, 'r') as f:
        user_data = json.load(f)
        # Ensure email key exists to prevent errors in other parts of the app
        user_data.setdefault('email', None)
    return user_data

def update_user_login_time(user_id: str, username: str):
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