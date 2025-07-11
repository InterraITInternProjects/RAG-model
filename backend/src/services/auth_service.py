from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from ..schema.models.users_model import UserCreate, UserLogin, UserResponse, TokenData, Token, User
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from utils.auth import create_access_token, verify_password, get_password_hash, verify_token, validate_password_strength, get_user_by_email, get_user, create_user, authenticate_user, get_current_user, update_user_password
from utils.exceptions import AuthenticationError, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..config.settings import ACCESS_TOKEN_EXPIRE_MINUTES
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthService:

    async def register(user: UserCreate, db: Session = Depends(get_db)):
        try:
            is_valid, error_message = validate_password_strength(user.password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)
        
            existing_user = get_user(db, user.username)
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already registered")
        
            existing_email = get_user_by_email(db, user.email)
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already registered")
        
            db_user = create_user(db, user.username, user.email, user.password)
        
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.username}, expires_delta=access_token_expires
        )
        
            logger.info(f"New user registered: {user.username}")
            return {"access_token": access_token, "token_type": "bearer"}
        
        except HTTPException:
            raise
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during registration: {str(e)}")
            raise HTTPException(status_code=400, detail="Registration failed due to data conflict")
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during registration: {str(e)}")
            raise HTTPException(status_code=500, detail="Registration failed")
        
    async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
        try:
            user = authenticate_user(db, form_data.username, form_data.password)
            if not user:
                logger.warning(f"Failed login attempt for username: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.user_name}, expires_delta=access_token_expires
            )
            
            logger.info(f"Successful login for user: {user.user_name}")
            return {"access_token": access_token, "token_type": "bearer"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
        
    async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
        try:
            if not verify_password(current_password, current_user.user_password, current_user.salt):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
            
            is_valid, error_message = validate_password_strength(new_password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)
            
            if update_user_password(db, current_user, new_password):
                logger.info(f"Password changed for user: {current_user.user_name}")
                return {"message": "Password changed successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to update password")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            raise HTTPException(status_code=500, detail="Password change failed")