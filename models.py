from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    stories = relationship("Story", back_populates="author")

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String)
    longitude = Column(Float)
    latitude = Column(Float)
    story_text = Column(Text)
    photo_url = Column(String)  # Store the URL/path to the photo
    industry = Column(String)
    ethnicity = Column(String)
    organization = Column(String)
    is_leader = Column(Boolean, default=False)
    help_needed = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="stories")
    is_approved = Column(Boolean, default=False)  # For moderation
    is_active = Column(Boolean, default=True)  # For soft deletion 