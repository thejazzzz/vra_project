from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from jose import jwt
from database.db import SessionLocal
from database.models.auth_models import User, UserRole, RefreshToken, VerificationToken, VerificationTokenType
from api.dependencies.auth import get_db, SECRET_KEY, ALGORITHM, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from utils.security import get_password_hash, verify_password, generate_secure_token
import logging
import hashlib
import secrets
import uuid
import os
from utils.rate_limiter import limiter
from utils.redis_client import is_account_locked, record_failed_login, clear_failed_login
from fastapi import Request
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import pyotp
import qrcode
from io import BytesIO
import base64
from utils import email_service

IS_PRODUCTION = os.getenv("APP_ENV", "local") != "local"

# Configure logger
logger = logging.getLogger(__name__)

def _get_email_hash(email: str) -> str:
    """Returns SHA-256 hash of the email for secure logging."""
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str

@router.post("/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Phase 1 Auth: Register a new user with an email and password.
    """
    email = body.email.lower().strip()
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        # Prevent email enumeration: Log internally, but return the same success message
        logger.warning(f"Registration attempt for already existing email: {_get_email_hash(email)}")
        return {"message": "Registration successful. Please check your email to verify your account."}
        
    password_hash = get_password_hash(body.password)
    
    try:
        new_user_id = str(uuid.uuid4())
        user = User(
            id=new_user_id,
            email=email,
            password_hash=password_hash,
            role=UserRole.STUDENT, # Default role
            created_at=datetime.utcnow(),
            email_verified=True # Auto-verify on registration as requested
        )
        db.add(user)
        db.flush() # Get user.id without committing yet
        logger.info(f"Created new user via registration: {user.id}")
        
        # Email Verification Logic
        verification_token = generate_secure_token()
        db_token = VerificationToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hashlib.sha256(verification_token.encode()).hexdigest(),
            type=VerificationTokenType.EMAIL_VERIFY,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(db_token)
        db.commit()
        
        # Send verification email in the background (informational, not enforced)
        background_tasks.add_task(email_service.send_verification, email, verification_token)
        if IS_PRODUCTION == False:
             # Just for local testing convenience to grab it from logs
             logger.info(f"DEV_ONLY: Verification token for {email} is: {verification_token}")
        
        return {"message": "Registration successful. Please check your email to verify your account."}
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register account due to an internal error.")

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/auth/verify-email")
@limiter.limit("10/minute")
async def verify_email(request: Request, body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verifies a user's email address using the token sent to them."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    
    db_token = db.query(VerificationToken).filter(
        VerificationToken.token_hash == token_hash,
        VerificationToken.type == VerificationTokenType.EMAIL_VERIFY
    ).first()
    
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired verification token.")
        
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        db.delete(db_token)
        db.commit()
        raise HTTPException(status_code=404, detail="User associated with this token not found.")
        
    user.email_verified = True
        
    # Delete the token since it's used
    db.delete(db_token)
    db.commit()
    
    return {"message": "Email verified successfully. You can now log in."}

class PasswordResetRequest(BaseModel):
    email: EmailStr

@router.post("/auth/password-reset/request")
@limiter.limit("3/minute")
async def request_password_reset(request: Request, body: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Requests a password reset link. Prevents email enumeration."""
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Invalidate any existing password reset tokens
        db.query(VerificationToken).filter(
            VerificationToken.user_id == user.id,
            VerificationToken.type == VerificationTokenType.PASSWORD_RESET
        ).delete()

        
        reset_token = generate_secure_token()
        db_token = VerificationToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hashlib.sha256(reset_token.encode()).hexdigest(),
            type=VerificationTokenType.PASSWORD_RESET,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(db_token)
        db.commit()
        # Send password reset email in the background
        background_tasks.add_task(email_service.send_password_reset, email, reset_token)
        if not IS_PRODUCTION:
            logger.info(f"DEV_ONLY: Password reset token for {email} is: {reset_token}")
    else:
        logger.info(f"Password reset requested for non-existent email: {_get_email_hash(email)}")
        
    # Always return the same response
    return {"message": "If an account with that email exists, we have sent a password reset link."}

class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

@router.post("/auth/password-reset/confirm")
@limiter.limit("5/minute")
async def confirm_password_reset(request: Request, body: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """Verifies the password reset token and sets the new password."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    db_token = db.query(VerificationToken).filter(
        VerificationToken.token_hash == token_hash,
        VerificationToken.type == VerificationTokenType.PASSWORD_RESET,
    ).first()

    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        db.delete(db_token)
        db.commit()
        raise HTTPException(status_code=404, detail="User not found.")

    # Update the password
    user.password_hash = get_password_hash(body.new_password)

    # Mark token as used and delete it
    db.delete(db_token)
    db.commit()

    logger.info(f"Password reset completed for user {user.id}")
    return {"message": "Password has been reset successfully. You can now sign in with your new password."}

@router.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, response: Response, body: LoginRequest, db: Session = Depends(get_db)):
    """
    Phase 1 Auth: Login with email and password. 
    Issues Access Token (short) + Refresh Token (long).
    """
    email = body.email.lower().strip()
    
    logger.info(f"Attempting login for: {_get_email_hash(email)}")
    
    # Enforce Brute-Force Lockout
    if is_account_locked(email):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to too many failed login attempts. Please try again later.")
        
    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not user.password_hash:
        record_failed_login(email)
        # Avoid user enumeration by returning a generic error
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not verify_password(body.password, user.password_hash):
        if record_failed_login(email):
             raise HTTPException(status_code=429, detail="Account temporarily locked due to too many failed login attempts. Please try again later.")
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Email verification check disabled as requested (emails not being sent)
    # if not user.email_verified:
    #     raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
        
    # Clear lockout counters upon successful login
    clear_failed_login(email)
    
    # 1. Create Access Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    jti = str(uuid.uuid4())
    to_encode = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "exp": expire,
        "jti": jti
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
    response.set_cookie(
        key="vra_auth_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION, 
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    response.set_cookie(
        key="vra_refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh" 
    )

    return {"message": "Login successful", "user": {"id": user.id, "email": user.email}, "access_token": access_token} 

class OAuthGoogleRequest(BaseModel):
    credential: str

@router.post("/auth/oauth/google")
@limiter.limit("10/minute")
async def google_oauth_login(request: Request, response: Response, body: OAuthGoogleRequest, db: Session = Depends(get_db)):
    """
    Phase 4 Auth: Login via Google SSO.
    Verifies the Google ID token and creates an account if none exists,
    then issues a standard VRA session.
    """
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    if not GOOGLE_CLIENT_ID:
        # Avoid crashing completely if not set up, just return 501
        raise HTTPException(status_code=501, detail="Google OAuth is not configured on this server.")
        
    try:
        # Verify the token against the Google platform
        idinfo = id_token.verify_oauth2_token(
            body.credential, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo['email'].lower().strip()
        email_verified = idinfo.get('email_verified', False)
        
        if not email_verified:
            raise HTTPException(status_code=400, detail="Google account email must be verified.")
            
        # See if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Provision a new passwordless user
            new_user_id = str(uuid.uuid4())
            user = User(
                id=new_user_id,
                email=email,
                role=UserRole.STUDENT,
                email_verified=True, # Trusted from Google
                created_at=datetime.utcnow()
            )
            try:
                db.add(user)
                db.commit()
                logger.info(f"Provisioned new user via Google SSO: {user.id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to provision Google OAuth user: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to provision user")
            
        # At this point, `user` is guaranteed to exist.
        # Log them in exactly like the normal login route
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + access_token_expires
        jti = str(uuid.uuid4())
        to_encode = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "exp": expire,
            "jti": jti
        }
        access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        refresh_token_str = secrets.token_urlsafe(64)
        refresh_token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        refresh_expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_refresh = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=refresh_expires,
            family_id=str(uuid.uuid4())
        )
        db.add(db_refresh)
        db.commit()

        # Set Cookies
        response.set_cookie(
            key="vra_auth_token",
            value=access_token,
            httponly=True,
            secure=IS_PRODUCTION, 
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )
        
        response.set_cookie(
            key="vra_refresh_token",
            value=refresh_token_str,
            httponly=True,
            secure=IS_PRODUCTION,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/auth/refresh" 
        )

        return {"message": "Google Login successful", "user": {"id": user.id, "email": user.email}, "access_token": access_token}
        
    except ValueError as e:
        logger.warning(f"Invalid Google ID token attempt: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google authentication token.")

@router.post("/auth/mfa/setup")
@limiter.limit("5/minute")
async def setup_mfa(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Phase 5 Auth: Generates a TOTP secret and QR code for the user.
    """
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled.")
        
    # Generate new random base32 secret
    secret = pyotp.random_base32()
    
    # Temporarily store the secret in the user record, encrypting happens transparently
    current_user.mfa_secret = secret
    db.commit()
    
    # Generate Provisioning URI for Authenticator apps
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name="VRA System")
    
    # Create QR Code Image
    qr = qrcode.make(uri)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    return {
        "message": "Scan this QR code with your authenticator app, then verify using /auth/mfa/verify.",
        "qr_code_base64": f"data:image/png;base64,{qr_b64}",
        "manual_secret": secret
    }

class MFAVerifyRequest(BaseModel):
    code: str

@router.post("/auth/mfa/verify")
@limiter.limit("5/minute")
async def verify_mfa(request: Request, body: MFAVerifyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Phase 5 Auth: Verifies the setup code and permanently enables MFA for the user.
    """
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled. This endpoint is for initial setup.")
        
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA setup has not been initiated.")
        
    totp = pyotp.TOTP(current_user.mfa_secret)
    if totp.verify(body.code):
        current_user.mfa_enabled = True
        db.commit()
        return {"message": "MFA has been successfully enabled."}
    else:
        # Prevent brute force at the model level via slowapi limits
        raise HTTPException(status_code=400, detail="Invalid MFA code.")

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
        jti = str(uuid.uuid4())
        to_encode = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "exp": expire,
            "jti": jti
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

from utils.redis_client import blocklist_token
import time

@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Clear the auth cookies and blocklist the current JWT.
    Also revokes the corresponding refresh token.
    """
    # 1. Blocklist Access Token
    token = request.cookies.get("vra_auth_token")
    if token:
        try:
            # Decode without verification just to extract jti and exp
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                blocklist_token(jti, exp)
                logger.info(f"Blocklisted JWT {jti} upon logout.")
        except Exception as e:
            logger.warning(f"Could not parse token during logout: {e}")

    # 2. Revoke Refresh Token
    refresh_token_str = request.cookies.get("vra_refresh_token")
    if refresh_token_str:
        try:
            token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
            db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
            if db_token:
                db_token.revoked = True
                db.commit()
                logger.info(f"Revoked refresh token for user {db_token.user_id} upon logout.")
        except Exception as e:
            logger.error(f"Failed to revoke refresh token during logout: {e}")
            db.rollback()

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
