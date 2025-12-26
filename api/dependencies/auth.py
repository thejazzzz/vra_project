from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database.db import SessionLocal
from database.models.auth_models import User
import os

# TODO: Retrieve these from a well-known endpoint or environment variables
ALGORITHM = "HS256" # Or RS256 for OIDC
SECRET_KEY = os.getenv("NEXTAUTH_SECRET")
EXPECTED_AUD = os.getenv("EXPECTED_AUD") # Optional: Set this in environment to enforce Audience check

# Auth Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

if not SECRET_KEY:
    raise ValueError("CRITICAL: NEXTAUTH_SECRET is not set in environment variables. Authentication cannot proceed.")

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Deprecated for cookie auth

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = request.cookies.get("vra_auth_token")
    if not token:
        # Fallback to Authorization header for API testing tools if needed, or just fail
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            raise credentials_exception

    try:
        # In production with OIDC, we would use the public key from the IdP (JWKS)
        # For this phase, we assume symmetric key or just decoding if we want to skip verification (not responsible)
        # We will use the NEXTAUTH_SECRET as the shared secret if using HS256, 
        # or we could skip verification for dev if needed, but let's try to be secure-ish.
        
        # NOTE: If using Auth0/Google directly on client, the token will be RS256 signed by them.
        # If using NextAuth, the session token is JWE (encrypted) by default, or JWT.
        # We configure NextAuth to use JWT.
        
        # For simplicity in this plan phase:
        # 1. We assume the token IS a JWT.
        # 2. We verify it.
        
        opts = {}
        audience = None
        if EXPECTED_AUD:
            audience = EXPECTED_AUD
            opts["verify_aud"] = True
        else:
            opts["verify_aud"] = False

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=audience, options=opts)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
        
    return user