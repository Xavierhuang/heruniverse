import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, SessionLocal
from models import Base, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as session:
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@heruniverse.com",
            hashed_password=pwd_context.hash("admin123"),  # You should change this password
            is_admin=True
        )
        
        session.add(admin_user)
        await session.commit()
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("\nIMPORTANT: Please change this password after first login!")

if __name__ == "__main__":
    asyncio.run(create_admin()) 