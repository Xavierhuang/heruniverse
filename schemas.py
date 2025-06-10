from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class StoryBase(BaseModel):
    name: str
    location: str
    story_text: str
    industry: str
    ethnicity: str
    organization: str
    is_leader: bool = False
    help_needed: Optional[str] = None

class StoryCreate(StoryBase):
    photo_data: str  # Base64 encoded photo

class StoryUpdate(StoryBase):
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None

class Story(StoryBase):
    id: int
    longitude: float
    latitude: float
    photo_url: str
    created_at: datetime
    author_id: int
    is_approved: bool
    is_active: bool

    class Config:
        from_attributes = True

class BulkUploadResponse(BaseModel):
    total_records: int
    successful_uploads: int
    failed_uploads: List[dict] 