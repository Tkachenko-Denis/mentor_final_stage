import string
import random
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import URLItem

Base.metadata.create_all(bind=engine)

app = FastAPI()

class URLCreate(BaseModel):
    url: HttpUrl

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_short_id(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.post("/shorten")
def shorten_url(item: URLCreate, db: Session = Depends(get_db)):
    # Генерируем уникальный short_id
    for _ in range(10):
        short_id = generate_short_id()
        existing = db.query(URLItem).filter(URLItem.short_id == short_id).first()
        if not existing:
            new_item = URLItem(short_id=short_id, full_url=str(item.url))
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            return {"short_url": f"http://localhost:8000/{short_id}"}
    raise HTTPException(status_code=500, detail="Не удалось сгенерировать короткую ссылку")

# Добавил функцию просмотра всех данных в таблице
@app.get("/items")
def get_all_items(db: Session = Depends(get_db)):
    items = db.query(URLItem).all()
    print(items)
    if not items:
        raise HTTPException(status_code=404, detail="Записи не найдены")
    return [
        {
            "id": item.id,
            "short_id": item.short_id,
            "full_url": item.full_url
        }
        for item in items
    ]

@app.get("/{short_id}")
def redirect_to_full(short_id: str, db: Session = Depends(get_db)):
    url_item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if not url_item:
        raise HTTPException(status_code=404, detail="Короткая ссылка не найдена")
    print(f"Redirecting to: {url_item.full_url}")
    return RedirectResponse(url=url_item.full_url, status_code=301)

@app.get("/stats/{short_id}")
def get_stats(short_id: str, db: Session = Depends(get_db)):
    url_item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if not url_item:
        raise HTTPException(status_code=404, detail="Короткая ссылка не найдена")
    return {
        "short_id": url_item.short_id,
        "full_url": url_item.full_url
    }

# Добавил способ просмотреть данные из бд по id, чтобы понимать какую короткую ссылку брать
@app.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(URLItem).filter(URLItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Элемент не найден")
    return {
        "id": item.id,
        "short_id": item.short_id,
        "full_url": item.full_url
    }

# Добавил возможность внести изменение в уже существующую запись в таблице по короткой ссылке
@app.put("/{short_id}")
def update_url(short_id: str, item: URLCreate, db: Session = Depends(get_db)):
    url_item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if not url_item:
        raise HTTPException(status_code=404, detail="Короткая ссылка не найдена")
    url_item.full_url = str(item.url)
    db.commit()
    db.refresh(url_item)
    return {
        "short_id": url_item.short_id,
        "updated_url": url_item.full_url
    }

# Добавил возможность удалить запись из таблицы по короткой ссылке
@app.delete("/{short_id}")
def delete_url(short_id: str, db: Session = Depends(get_db)):
    url_item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if not url_item:
        raise HTTPException(status_code=404, detail="Короткая ссылка не найдена")
    db.delete(url_item)
    db.commit()
    return {"message": f"Короткая ссылка с ID {short_id} удалена"}
