from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt
from database.db import SessionLocal
from database.models.auth_models import User, UserRole, RefreshToken
from api.dependencies.auth import get_db, SECRET_KEY, ALGORITHM, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
import logging
import hashlib
import secrets
import uuid
import os

IS_PRODUCTION = os.getenv("APP_ENV", "local") != "local"

# Configure logger
logger = logging.getLogger(__name__)

def _get_email_hash(email: str) -> str:
    """Returns SHA-256 hash of the email for secure logging."""
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()

router = APIRouter()

# Schema for Login
class LoginRequest(BaseModel):
    email: EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str

@router.post("/auth/login")
async def login(response: Response, request: LoginRequest, db: Session = Depends(get_db)):
    """
    Phase 0 Demo Auth: Login with email only. 
    Issues Access Token (short) + Refresh Token (long).
    """
    email = request.email.lower().strip()
    
    logger.info(f"Attempting login for: {_get_email_hash(email)}")
    
    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # JIT Provisioning (Demo Mode)
        try:
            new_user_id = str(uuid.uuid4())
            user = User(
                id=new_user_id,
                email=email,
                role=UserRole.RESEARCHER, # Default role
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {user.id}")
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create user account")
    
    # 1. Create Access Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "exp": expire
    }
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # 2. Create Refresh Token (Opaque)
    refresh_token_str = secrets.token_urlsafe(64)
    refresh_token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
    refresh_expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=refresh_expires,
        family_id=str(uuid.uuid4()) # Start new family on login
    )
    db.add(db_refresh)
    db.commit()
    
    logger.info(f"USER_LOGIN user_id={user.id}")

    # 3. Set Cookies
    # Access Token (Short)
    response.set_cookie(
        key="vra_auth_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION, 
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    # Refresh Token (Long) - Path Restricted? 
    # For simplicity in Phase 0, using path="/" but ideally "/auth/refresh"
    # To allow seamless renewal without path issues in frontend middleware, we stick to / for now
    # or separate. Let's use path="/auth/refresh" and a general one?
    # Next.js middleware needs to know if user is logged in. access token does that.
    # Refresher needs refresh token.
    response.set_cookie(
        key="vra_refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh" # Restrict to refresh endpoint(without /api prefix since router is at root)
    )
    # Also set on root? No, security best practice is restrict. 
    # But wait, our API router prefix is blank in auth.py but included in main.py?
    # In main.py: app.include_router(auth.router, tags=["Authentication"]) -> No prefix!
    # So path is /auth/login, /auth/refresh.
    # So path="/auth/refresh" is correct.

    return {"message": "Login successful", "user": {"id": user.id, "email": user.email}} 

@router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Rotate Refresh Token and issue new Access Token.
    Enforces Family-Based Revocation on token reuse.
    """
    refresh_token_str = request.cookies.get("vra_refresh_token")
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    # Hash to find in DB
    token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
    
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).with_for_update().first()
    
    if not db_token:
        # Token simply doesn't exist (maybe extremely old and purged, or truly invalid)
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # Check for Reuse (Revoked)
    if db_token.revoked:
        # CRITICAL: Token reuse detected. Revoke entire family.
        logger.warning(f"SECURITY: Token reuse detected. User: {db_token.user_id}, Family: {db_token.family_id}")
        
        # Revoke all tokens in this family
        db.query(RefreshToken).filter(RefreshToken.family_id == db_token.family_id).update({"revoked": True})
        db.commit()
        
        # Logout / Clear Cookies to be safe via JSONResponse since HTTPException won't persist cookie deletion
        from fastapi.responses import JSONResponse
        content = {"detail": "Security Alert: Reuse detected. Session terminated."}
        error_response = JSONResponse(status_code=401, content=content)
        error_response.delete_cookie("vra_auth_token", path="/", httponly=True, secure=IS_PRODUCTION)
        error_response.delete_cookie("vra_refresh_token", path="/auth/refresh", httponly=True, secure=IS_PRODUCTION)
        
        return error_response
        
    # Check Expiry
    if db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    # Valid Token: Rotate
    try:
        # 1. Revoke current
        db_token.revoked = True
        
        # 2. Get User
        user = db.query(User).filter(User.id == db_token.user_id).first()
        if not user:
            raise HTTPException(401, "User not found")

        # 3. Issue new pair
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + access_token_expires
        to_encode = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "exp": expire
        }
        new_access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Rotate Refresh
        new_refresh_str = secrets.token_urlsafe(64)
        new_refresh_hash = hashlib.sha256(new_refresh_str.encode()).hexdigest()
        new_refresh_expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_db_token = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=new_refresh_expires,
            family_id=db_token.family_id # Maintain family
        )
        db.add(new_db_token)
        db.commit() # Atomic commit of revocation + new token
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Token refresh transaction failed: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed due to server error")
    
    # Set Cookies
    response.set_cookie(
        key="vra_auth_token",
        value=new_access_token,
        httponly=True,
        secure=IS_PRODUCTION, 
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="vra_refresh_token",
        value=new_refresh_str,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh" 
    )
    
    return {"message": "Token refreshed"}

@router.post("/auth/logout")
async def logout(response: Response):
    """
    Clear the auth cookies.
    """
    response.delete_cookie("vra_auth_token", path="/", httponly=True, secure=IS_PRODUCTION)
    response.delete_cookie("vra_refresh_token", path="/auth/refresh", httponly=True, secure=IS_PRODUCTION)
    return {"message": "Logged out successfully"}

@router.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    }
