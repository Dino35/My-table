import shutil
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# --- IMPORT DATABASE STUFF FROM OUR NEW FILE ---
from models import SessionLocal, DBMenuItem, MenuItemCreate, OrderItem, Order, OrderStatus

# --- 1. FASTAPI SETUP ---
app = FastAPI()

os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. DATABASE DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. WEBSOCKET MANAGERS ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    async def connect(self, websocket: WebSocket, key: str):
        await websocket.accept()
        if key not in self.active_connections: self.active_connections[key] = []
        self.active_connections[key].append(websocket)
    def disconnect(self, websocket: WebSocket, key: str):
        if key in self.active_connections: self.active_connections[key].remove(websocket)
    async def broadcast(self, message: dict, key: str):
        if key in self.active_connections:
            for connection in self.active_connections[key]:
                await connection.send_json(message)

kitchen_manager = ConnectionManager()
customer_manager = ConnectionManager()

# --- 4. STARTUP (Seed Data) ---
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if db.query(DBMenuItem).count() == 0:
        defaults = [
            DBMenuItem(restaurant_id=1, name="Latte", price=4.50, description="Oat milk base", image_url="https://images.unsplash.com/photo-1541167760496-1628856ab772?w=200"),
            DBMenuItem(restaurant_id=1, name="Croissant", price=3.00, description="Freshly baked", image_url="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=200"),
            DBMenuItem(restaurant_id=1, name="Espresso", price=2.50, description="Double shot", image_url="https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=200")
        ]
        db.add_all(defaults)
        db.commit()
    db.close()

# --- 5. API ENDPOINTS ---
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/images/{unique_filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/static/images/{unique_filename}"}

@app.get("/api/menu/{restaurant_id}")
async def get_menu(restaurant_id: int, db: Session = Depends(get_db)):
    items = db.query(DBMenuItem).filter(DBMenuItem.restaurant_id == restaurant_id).all()
    return {"id": restaurant_id, "menu": items}

@app.post("/api/menu/{restaurant_id}/add")
async def add_menu_item(restaurant_id: int, item: MenuItemCreate, db: Session = Depends(get_db)):
    new_db_item = DBMenuItem(
        restaurant_id=restaurant_id,
        name=item.name,
        price=item.price,
        description=item.description,
        image_url=item.image_url
    )
    db.add(new_db_item)
    db.commit()
    db.refresh(new_db_item)
    return new_db_item

@app.post("/api/order/{restaurant_id}")
async def place_order(restaurant_id: int, order: Order):
    await kitchen_manager.broadcast({
        "event": "NEW_ORDER",
        "table": order.table_number,
        "items": [item.dict() for item in order.items]
    }, str(restaurant_id))
    return {"status": "sent"}

@app.post("/api/kitchen/ready/{restaurant_id}")
async def mark_ready(restaurant_id: int, status: OrderStatus):
    await customer_manager.broadcast({
        "event": "ORDER_READY",
        "message": "Ready for pickup!"
    }, str(status.table_number))
    return {"status": "notified"}

# --- 6. WEBSOCKETS ---
@app.websocket("/ws/kitchen/{restaurant_id}")
async def kitchen_ws(websocket: WebSocket, restaurant_id: int):
    await kitchen_manager.connect(websocket, str(restaurant_id))
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        kitchen_manager.disconnect(websocket, str(restaurant_id))

@app.websocket("/ws/customer/{table_number}")
async def customer_ws(websocket: WebSocket, table_number: int):
    await customer_manager.connect(websocket, str(table_number))
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        customer_manager.disconnect(websocket, str(table_number))

# --- 7. HTML PAGES ---
@app.get("/kitchen/{restaurant_id}", response_class=HTMLResponse)
async def serve_kitchen(request: Request, restaurant_id: int):
    return templates.TemplateResponse("kitchen.html", {"request": request, "restaurant_id": restaurant_id})

@app.get("/admin/{restaurant_id}", response_class=HTMLResponse)
async def serve_admin(request: Request, restaurant_id: int):
    return templates.TemplateResponse("admin.html", {"request": request, "restaurant_id": restaurant_id})

@app.get("/{restaurant_name}/{table_number}", response_class=HTMLResponse)
async def serve_menu(request: Request, restaurant_name: str, table_number: int):
    return templates.TemplateResponse("menu.html", {"request": request, "restaurant_id": 1, "restaurant_name": restaurant_name, "table_number": table_number})