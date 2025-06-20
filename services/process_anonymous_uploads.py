import os
import shutil
import logging
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException
import psycopg2.extras
from core.database import get_db_connection, release_db_connection
from services.user_management import create_user_folder

logger = logging.getLogger(__name__)

async def process_anonymous_uploads_after_login(user_id: UUID, username: str, temp_file_id: str = None):
    """
    Process any anonymous uploads after a user logs in.
    If temp_file_id is provided, only process that specific file.
    Otherwise, process all anonymous uploads for the user's session.
    """
    db = None
    try:
        db = get_db_connection()
        
        # Create user directory if it doesn't exist
        user_dir = create_user_folder(user_id, username)
        
        # Find all anonymous uploads for this user's session
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if temp_file_id:
                # Process specific file
                cur.execute(
                    """
                    SELECT id, file_name, storage_path, is_anonymous
                    FROM file_upload_sessions
                    WHERE id = %s AND is_anonymous = TRUE
                    FOR UPDATE
                    """,
                    (temp_file_id,)
                )
            else:
                # Process all anonymous uploads for this session
                cur.execute(
                    """
                    SELECT id, file_name, storage_path, is_anonymous
                    FROM file_upload_sessions
                    WHERE is_anonymous = TRUE
                    AND created_at > NOW() - INTERVAL '1 day'
                    FOR UPDATE
                    """
                )
            
            uploads = cur.fetchall()
            
            if not uploads:
                logger.info("No anonymous uploads found to process")
                return []
            
            processed_files = []
            
            for upload in uploads:
                try:
                    # Move the file to the user's directory
                    original_path = upload['storage_path']
                    if not os.path.exists(original_path):
                        logger.warning(f"File not found: {original_path}")
                        continue
                    
                    # Generate a new filename to avoid collisions
                    new_filename = f"{UUID(int=uuid4().int)}_{upload['file_name']}"
                    new_path = os.path.join(user_dir, new_filename)
                    
                    # Move the file
                    shutil.move(original_path, new_path)
                    
                    # Create a record in the files table
                    cur.execute(
                        """
                        INSERT INTO files (user_id, file_name, uploaded_at, analyzed_at)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (user_id, upload['file_name'], datetime.utcnow(), datetime.utcnow())
                    )
                    file_id = cur.fetchone()['id']
                    
                    # Update the upload session
                    cur.execute(
                        """
                        UPDATE file_upload_sessions
                        SET user_id = %s, 
                            is_anonymous = FALSE,
                            storage_path = %s,
                            final_file_id = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (user_id, new_path, file_id, upload['id'])
                    )
                    
                    processed_files.append({
                        'id': str(file_id),
                        'filename': upload['file_name'],
                        'path': new_path
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing anonymous upload {upload.get('id')}: {e}")
                    # Continue with other files even if one fails
                    db.rollback()
                    continue
            
            db.commit()
            return processed_files
            
    except Exception as e:
        logger.error(f"Error in process_anonymous_uploads_after_login: {e}")
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail="Error processing anonymous uploads")
    finally:
        if db:
            release_db_connection(db)
