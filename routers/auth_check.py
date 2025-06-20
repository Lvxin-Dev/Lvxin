from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from uuid import UUID
from core.security import optional_cookie, verifier

router = APIRouter()

@router.get("/api/auth/check")
async def check_auth(request: Request, session_id: UUID = Depends(optional_cookie)):
    """
    Check if the current user is authenticated.
    Returns 200 OK if authenticated, 401 Unauthorized if not.
    """
    try:
        session_data = await verifier(request) if session_id else None
        if not session_data:
            return JSONResponse(
                status_code=401,
                content={"is_authenticated": False, "message": "Not authenticated"}
            )
        
        return {
            "is_authenticated": True,
            "user_id": session_data.user_id,
            "username": session_data.username,
            "email": session_data.email
        }
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"is_authenticated": False, "message": "Not authenticated"}
        )
