-- Add is_anonymous column to file_upload_sessions table
ALTER TABLE file_upload_sessions 
ADD COLUMN is_anonymous BOOLEAN NOT NULL DEFAULT FALSE;

-- Add index for better query performance on anonymous uploads
CREATE INDEX idx_file_upload_sessions_anonymous 
ON file_upload_sessions (is_anonymous) 
WHERE is_anonymous = TRUE;
