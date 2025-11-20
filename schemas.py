"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Core app schemas for the Translation Platform

class Book(BaseModel):
    """
    Books collection schema
    Collection name: "book"
    """
    title: str = Field(..., description="Book title")
    author: Optional[str] = Field(None, description="Author name")
    description: Optional[str] = Field(None, description="Short description")

class Chapter(BaseModel):
    """
    Chapters collection schema
    Collection name: "chapter"
    """
    book_id: str = Field(..., description="Related book id (string of ObjectId)")
    title: str = Field(..., description="Chapter title")
    source_language: str = Field(..., description="Source language code, e.g., en")
    target_language: str = Field(..., description="Target language code, e.g., es")
    source_text: str = Field(..., description="Original text content")
    translation_text: str = Field("", description="Translated text content")

# Keep example schemas for reference (not used by the app directly)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    in_stock: bool = True
