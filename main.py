import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Book, Chapter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId string")
        return v

class ChapterCreate(BaseModel):
    book_id: str
    title: str
    source_language: str
    target_language: str
    source_text: str

class ChapterUpdate(BaseModel):
    translation_text: str

class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    description: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Translation platform backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# Backend API endpoints

@app.post("/api/books", response_model=dict)
def create_book(book: BookCreate):
    try:
        book_id = create_document("book", Book(**book.model_dump()))
        return {"id": book_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/books", response_model=List[dict])
def list_books():
    try:
        books = get_documents("book")
        # Convert ObjectId to string
        for b in books:
            b["id"] = str(b.pop("_id"))
        return books
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chapters", response_model=dict)
def create_chapter(payload: ChapterCreate):
    try:
        if not ObjectId.is_valid(payload.book_id):
            raise HTTPException(status_code=400, detail="Invalid book_id")
        chapter = Chapter(**payload.model_dump())
        chapter_id = create_document("chapter", chapter)
        return {"id": chapter_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chapters", response_model=List[dict])
def list_chapters(book_id: Optional[str] = None):
    try:
        filter_q = {"book_id": book_id} if book_id else {}
        chapters = get_documents("chapter", filter_q)
        for c in chapters:
            c["id"] = str(c.pop("_id"))
        return chapters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chapters/{chapter_id}", response_model=dict)
def get_chapter(chapter_id: str):
    try:
        if not ObjectId.is_valid(chapter_id):
            raise HTTPException(status_code=400, detail="Invalid chapter id")
        doc = db["chapter"].find_one({"_id": ObjectId(chapter_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Chapter not found")
        doc["id"] = str(doc.pop("_id"))
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/chapters/{chapter_id}")
def update_chapter(chapter_id: str, payload: ChapterUpdate):
    try:
        if not ObjectId.is_valid(chapter_id):
            raise HTTPException(status_code=400, detail="Invalid chapter id")
        res = db["chapter"].update_one(
            {"_id": ObjectId(chapter_id)},
            {"$set": {"translation_text": payload.translation_text, "updated_at": __import__('datetime').datetime.utcnow()}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Chapter not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str

class TranslateResponse(BaseModel):
    translated_text: str

# Mock translation endpoint (replace with real provider later)
@app.post("/api/translate", response_model=TranslateResponse)
def translate_text(req: TranslateRequest):
    # Simple placeholder that reverses text and tags language codes
    pseudo = f"[{req.source_language}->{req.target_language}] " + req.text[::-1]
    return TranslateResponse(translated_text=pseudo)

# Real-time collaboration via Server-Sent Events (simple broadcast demo)
subscribers = set()

@app.get("/api/collab/stream")
async def collab_stream():
    from fastapi.responses import StreamingResponse
    import asyncio

    async def event_generator(queue: asyncio.Queue):
        try:
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            pass

    queue = asyncio.Queue()
    subscribers.add(queue)

    async def cleanup():
        subscribers.discard(queue)

    return StreamingResponse(event_generator(queue), media_type="text/event-stream")

class CollabEvent(BaseModel):
    chapter_id: str
    user: str
    content: str

@app.post("/api/collab/publish")
async def collab_publish(event: CollabEvent):
    import asyncio
    # Fan out to all subscriber queues
    for q in list(subscribers):
        try:
            await q.put(event.model_dump_json())
        except Exception:
            subscribers.discard(q)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
