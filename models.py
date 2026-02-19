from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from typing import List, Optional

# --- 1. DATABASE SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./restaurant.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. SQL DATABASE MODELS ---

# NEW: The Restaurant Table!
class DBRestaurant(Base):
    __tablename__ = "restaurants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True) # E.g., "GeminiCoffee"
    passcode = Column(String) # For the owner to login later
    
    # This links the restaurant to its menu items
    menu_items = relationship("DBMenuItem", back_populates="restaurant")

class DBMenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True, index=True)
    
    # UPDATED: This now officially links to the DBRestaurant table
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(String)
    image_url = Column(String)

    # This links the item back to the restaurant
    restaurant = relationship("DBRestaurant", back_populates="menu_items")

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