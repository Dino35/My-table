from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import List, Optional

# --- 1. DATABASE SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./restaurant.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. SQL DATABASE MODELS ---
class DBMenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(String)
    image_url = Column(String)

# Create the tables in the database
Base.metadata.create_all(bind=engine)

# --- 3. PYDANTIC MODELS (Data Validation) ---
class MenuItemCreate(BaseModel):
    name: str
    price: float
    description: str
    image_url: Optional[str] = "https://placehold.co/100x100"

class OrderItem(BaseModel):
    item_id: int
    quantity: int

class Order(BaseModel):
    table_number: int
    items: List[OrderItem]

class OrderStatus(BaseModel):
    table_number: int
    status: str