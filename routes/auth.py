"""Auth routes — register, login, current user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, User, new_id
from auth_core import hash_password, verify_password, create_access_token, get_current_user
from api_schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        id=new_id(),
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        name=req.name.strip(),
    )
    db.add(user)
    db.commit()
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, name=user.name, created_at=user.created_at)