#!/usr/bin/env python3
"""
Initialize admin user for the bot
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import async_session_maker, init_db
from database.models import User
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_admin_user(telegram_id: int, username: str = None, first_name: str = "Admin"):
    """Create or update admin user"""
    try:
        # Initialize database
        await init_db()
        
        async with async_session_maker() as session:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user to admin
                user.is_admin = True
                user.username = username
                user.first_name = first_name
                await session.commit()
                logger.info(f"Updated user {telegram_id} to admin")
            else:
                # Create new admin user
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    is_admin=True
                )
                session.add(user)
                await session.commit()
                logger.info(f"Created new admin user {telegram_id}")
            
            return user
    
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python init_admin.py <telegram_id> [username] [first_name]")
        print("Example: python init_admin.py 123456789 admin_user Admin")
        sys.exit(1)
    
    telegram_id = int(sys.argv[1])
    username = sys.argv[2] if len(sys.argv) > 2 else None
    first_name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    print(f"Creating admin user...")
    print(f"Telegram ID: {telegram_id}")
    print(f"Username: {username}")
    print(f"First Name: {first_name}")
    
    user = await create_admin_user(telegram_id, username, first_name)
    
    print("\n✅ Admin user created successfully!")
    print(f"User can now access admin panel with /admin command")


if __name__ == "__main__":
    asyncio.run(main())