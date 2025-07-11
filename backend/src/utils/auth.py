# backend/app/auth.py

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from backend.src.schema.users import User
from backend.src.config.database import get_db
from .exceptions import AuthenticationError
import os
import secrets
import hashlib

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def generate_salt(length: int = 32) -> str:
    """Generate a random salt for password hashing."""
    return secrets.token_hex(length)

def hash_password_with_salt(password: str, salt: str) -> str:
    """Hash password with salt using bcrypt."""
    salted_password = f"{password}{salt}"
    return pwd_context.hash(salted_password)

def verify_password_with_salt(plain_password: str, salt: str, hashed_password: str) -> bool:
    """Verify password with salt."""
    salted_password = f"{plain_password}{salt}"
    return pwd_context.verify(salted_password, hashed_password)

def get_password_hash(password: str) -> tuple[str, str]:
    """
    Generate password hash with salt.
    Returns tuple of (hashed_password, salt).
    """
    salt = generate_salt()
    hashed_password = hash_password_with_salt(password, salt)
    return hashed_password, salt

def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """Verify password using salt."""
    return verify_password_with_salt(plain_password, salt, hashed_password)

def get_user(db: Session, username: str):
    """Get user by username."""
    return db.query(User).filter(User.user_name == username).first()

def get_user_by_email(db: Session, email: str):
    """Get user by email."""
    return db.query(User).filter(User.user_email == email).first()

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user with username and password."""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.user_password, user.salt):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

def create_user(db: Session, username: str, email: str, password: str) -> User:
    """Create a new user with salted password."""
    hashed_password, salt = get_password_hash(password)
    db_user = User(
        user_name=username,
        user_email=email,
        user_password=hashed_password,
        salt=salt
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_password(db: Session, user: User, new_password: str) -> bool:
    """Update user password with new salt."""
    try:
        hashed_password, salt = get_password_hash(new_password)
        user.user_password = hashed_password
        user.salt = salt
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns tuple of (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

print("auth.py is running")