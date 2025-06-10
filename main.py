from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
import pandas as pd
import json
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import base64
import aiofiles
from pathlib import Path

from database import get_db, engine
from models import Base, User, Story
from schemas import UserCreate, User as UserSchema, Story as StorySchema, StoryCreate, StoryUpdate, BulkUploadResponse

# Create media directory if it doesn't exist
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Mount static files
app.mount("/", StaticFiles(directory=".", html=True), name="static")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("startup")
async def startup_event():
    await init_db()

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
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
    
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# User endpoints
@app.post("/users/", response_model=UserSchema)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Story endpoints
@app.post("/stories/", response_model=StorySchema)
async def create_story(story: StoryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Save photo
    photo_data = base64.b64decode(story.photo_data.split(',')[1])
    photo_filename = f"{datetime.now().timestamp()}.jpg"
    photo_path = MEDIA_DIR / photo_filename
    
    async with aiofiles.open(photo_path, 'wb') as f:
        await f.write(photo_data)
    
    # Get coordinates from location using an external geocoding service
    # For now, using dummy coordinates
    longitude, latitude = -74.5, 40  # Replace with actual geocoding
    
    db_story = Story(
        **story.dict(exclude={'photo_data'}),
        photo_url=str(photo_path),
        longitude=longitude,
        latitude=latitude,
        author_id=current_user.id,
        is_approved=current_user.is_admin
    )
    
    db.add(db_story)
    await db.commit()
    await db.refresh(db_story)
    return db_story

@app.get("/stories/", response_model=List[StorySchema])
async def get_stories(
    skip: int = 0,
    limit: int = 100,
    approved_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    query = select(Story).filter(Story.is_active == True)
    if approved_only:
        query = query.filter(Story.is_approved == True)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.put("/stories/{story_id}", response_model=StorySchema)
async def update_story(
    story_id: int,
    story: StoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Story).filter(Story.id == story_id))
    db_story = result.scalar_one_or_none()
    
    if not db_story:
        raise HTTPException(status_code=404, detail="Story not found")
    if db_story.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this story")
    
    for key, value in story.dict(exclude_unset=True).items():
        setattr(db_story, key, value)
    
    await db.commit()
    await db.refresh(db_story)
    return db_story

@app.delete("/stories/{story_id}")
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Story).filter(Story.id == story_id))
    db_story = result.scalar_one_or_none()
    
    if not db_story:
        raise HTTPException(status_code=404, detail="Story not found")
    if db_story.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this story")
    
    # Soft delete
    db_story.is_active = False
    await db.commit()
    return {"message": "Story deleted successfully"}

# Bulk upload endpoint
@app.post("/stories/bulk", response_model=BulkUploadResponse)
async def bulk_upload_stories(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can perform bulk uploads")
    
    # Read Excel file
    df = pd.read_excel(file.file)
    total_records = len(df)
    successful_uploads = 0
    failed_uploads = []
    
    for _, row in df.iterrows():
        try:
            # Create story from row data
            story_data = {
                "name": row["name"],
                "location": row["location"],
                "story_text": row["story_text"],
                "industry": row["industry"],
                "ethnicity": row["ethnicity"],
                "organization": row["organization"],
                "is_leader": bool(row.get("is_leader", False)),
                "help_needed": row.get("help_needed"),
                "longitude": float(row.get("longitude", -74.5)),  # Default coordinates
                "latitude": float(row.get("latitude", 40)),
                "photo_url": row.get("photo_url", "default.jpg"),
                "author_id": current_user.id,
                "is_approved": True
            }
            
            db_story = Story(**story_data)
            db.add(db_story)
            await db.commit()
            successful_uploads += 1
            
        except Exception as e:
            failed_uploads.append({
                "row": _,
                "error": str(e)
            })
    
    return BulkUploadResponse(
        total_records=total_records,
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads
    )

@app.get("/")
async def read_root():
    return FileResponse("stories.html")

if __name__ == "__main__":
    import uvicorn
    print("Starting server...")
    print("Server will be available at: http://localhost:8000")
    print("Admin interface will be at: http://localhost:8000/admin.html")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 