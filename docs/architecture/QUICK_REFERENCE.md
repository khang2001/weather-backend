# 🔖 Quick Reference: API to Database Connection

## 📋 File & Function Cheat Sheet

### 1. Configuration

```python
# backend/app/config.py
DATABASE_URL = "postgresql://user:pass@host:port/database"
```
**Purpose**: Connection string to PostgreSQL

---

### 2. Database Connection

```python
# backend/app/database/connection.py

# Create engine (connection manager)
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

# Dependency function
def get_db():
    db = SessionLocal()  # Create session
    try:
        yield db         # Give to route
    finally:
        db.close()       # Always close
```

**Purpose**: 
- `engine`: Manages database connections
- `SessionLocal`: Factory to create sessions
- `get_db()`: Provides sessions to API routes

---

### 3. Database Models

```python
# backend/app/database/models.py

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    comfort_temperature = Column(Float)
    clothing_list = Column(JSON)
```

**Purpose**: Defines table structure (Python class = SQL table)

---

### 4. API Routes

```python
# backend/app/routers/settings.py

@router.get("/{user_id}")
def get_user_settings(
    user_id: int,
    db: Session = Depends(get_db)  # ← Magic happens here!
):
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

**Purpose**: Handle HTTP requests, interact with database

---

### 5. Main App

```python
# backend/app/web.py

app = FastAPI()
app.include_router(settings.router)  # Register /settings routes
```

**Purpose**: Create FastAPI app, register all routes

---

### 6. Frontend

```javascript
// frontend/src/pages/Settings.jsx

const fetchSettings = async (userId) => {
  const response = await fetch(`http://127.0.0.1:8000/settings/${userId}`);
  const data = await response.json();
  setSettings(data);
};
```

**Purpose**: Make API calls from React

---

## 🎯 Key Concepts

### Dependency Injection

```python
# FastAPI automatically:
db: Session = Depends(get_db)

# 1. Calls get_db()
# 2. Gets database session
# 3. Passes to function as 'db'
# 4. Closes session when done
```

### ORM (Object-Relational Mapping)

```python
# Python code:
user = db.query(User).filter(User.id == 3).first()

# Becomes SQL:
SELECT * FROM users WHERE id = 3 LIMIT 1;

# Returns Python object:
user.email  # "test@example.com"
```

### Session Operations

```python
# Query
user = db.query(User).filter(User.id == 3).first()

# Create
db.add(new_user)
db.commit()

# Update
user.comfort_temperature = 72
db.commit()

# Delete
db.delete(user)
db.commit()

# Rollback (undo changes)
db.rollback()
```

---

## 🔍 Common Operations

### Get Single User

```python
# Route handler
@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    return user
```

```sql
-- Generated SQL
SELECT * FROM users WHERE id = ? LIMIT 1;
```

### Get All Users

```python
@router.get("/")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
```

```sql
-- Generated SQL
SELECT * FROM users;
```

### Create User

```python
@router.post("/")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    new_user = User(
        username=user_data.username,
        email=user_data.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Get ID and timestamps
    return new_user
```

```sql
-- Generated SQL
INSERT INTO users (username, email) VALUES (?, ?);
SELECT * FROM users WHERE id = ?;  -- refresh
```

### Update User

```python
@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    
    user.comfort_temperature = user_data.comfort_temperature
    db.commit()
    db.refresh(user)
    return user
```

```sql
-- Generated SQL
SELECT * FROM users WHERE id = ? LIMIT 1;
UPDATE users SET comfort_temperature = ? WHERE id = ?;
SELECT * FROM users WHERE id = ?;  -- refresh
```

### Delete User

```python
@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    
    db.delete(user)
    db.commit()
    return {"message": "Deleted"}
```

```sql
-- Generated SQL
SELECT * FROM users WHERE id = ? LIMIT 1;
DELETE FROM users WHERE id = ?;
```

---

## 🌐 Frontend API Calls

### GET Request

```javascript
const response = await fetch('http://127.0.0.1:8000/settings/3');
const data = await response.json();
// data = {id: 3, email: "...", ...}
```

### POST Request

```javascript
const response = await fetch('http://127.0.0.1:8000/settings/3/clothing', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "Jacket",
    warmth_rating: 7
  })
});
const data = await response.json();
```

### PUT Request

```javascript
const response = await fetch('http://127.0.0.1:8000/settings/3', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    comfort_temperature: 72
  })
});
const data = await response.json();
```

### DELETE Request

```javascript
const response = await fetch('http://127.0.0.1:8000/settings/3/clothing/0', {
  method: 'DELETE'
});
const data = await response.json();
```

---

## 🎨 SQLAlchemy Query Patterns

```python
# Get one
user = db.query(User).filter(User.id == 3).first()

# Get all
users = db.query(User).all()

# Filter by email
user = db.query(User).filter(User.email == "test@example.com").first()

# Filter with AND
users = db.query(User).filter(
    User.comfort_temperature > 70,
    User.email.contains("example")
).all()

# Filter with OR
from sqlalchemy import or_
users = db.query(User).filter(
    or_(
        User.email == "test@example.com",
        User.username == "testuser"
    )
).all()

# Order by
users = db.query(User).order_by(User.created_at.desc()).all()

# Limit
users = db.query(User).limit(10).all()

# Count
count = db.query(User).count()

# Check exists
exists = db.query(User).filter(User.email == "test@example.com").first() is not None
```

---

## 🐛 Debugging

### See SQL Queries

```python
# connection.py
engine = create_engine(DATABASE_URL, echo=True)  # Prints all SQL
```

### Add Logging

```python
@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    print(f"Querying user_id: {user_id}")
    user = db.query(User).filter(User.id == user_id).first()
    print(f"Found: {user.email if user else 'None'}")
    return user
```

### Test with PowerShell

```powershell
# GET
Invoke-WebRequest http://localhost:8000/settings/3

# POST
$body = @{comfort_temperature=72} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/settings/3 `
  -Method PUT -Body $body -ContentType "application/json"
```

---

## 📊 Complete Example Flow

```
User clicks "Save" button
        ↓
JavaScript: fetch('http://127.0.0.1:8000/settings/3', {method: 'PUT'})
        ↓
HTTP: PUT /settings/3
        ↓
FastAPI: Routes to settings.py
        ↓
FastAPI: Calls get_db() → Creates session
        ↓
Route Handler: def update_user_settings(user_id, data, db)
        ↓
SQLAlchemy: db.query(User).filter(User.id == user_id).first()
        ↓
SQL: SELECT * FROM users WHERE id = 3;
        ↓
PostgreSQL: Returns row
        ↓
SQLAlchemy: Converts row → Python User object
        ↓
Route Handler: user.comfort_temperature = 72
        ↓
Route Handler: db.commit()
        ↓
SQL: UPDATE users SET comfort_temperature = 72 WHERE id = 3;
        ↓
Route Handler: return user
        ↓
FastAPI: Converts User object → JSON
        ↓
HTTP: 200 OK, Body: {"id": 3, "comfort_temperature": 72, ...}
        ↓
JavaScript: data = await response.json()
        ↓
React: setSettings(data) → UI updates
        ↓
User sees: "Temperature: 72°F"
```

---

## 🎯 Quick Answers

**Q: Where is the database URL?**  
A: `backend/app/config.py` → `DATABASE_URL`

**Q: How does FastAPI get the database session?**  
A: `Depends(get_db)` → Calls `get_db()` → Returns session

**Q: Where are table structures defined?**  
A: `backend/app/database/models.py` → `class User(Base)`

**Q: How do I query the database?**  
A: `db.query(User).filter(User.id == 3).first()`

**Q: How do I save changes?**  
A: `db.commit()`

**Q: How do I undo changes?**  
A: `db.rollback()`

**Q: Where are API endpoints defined?**  
A: `backend/app/routers/*.py` files

**Q: How are routes registered?**  
A: `backend/app/web.py` → `app.include_router(settings.router)`

**Q: How does frontend call API?**  
A: `fetch('http://127.0.0.1:8000/settings/3')`

**Q: What converts Python ↔ SQL?**  
A: SQLAlchemy ORM (Object-Relational Mapping)

---

## 📚 Key Imports

```python
# FastAPI
from fastapi import FastAPI, Depends, HTTPException, APIRouter

# SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.sql import func

# Your modules
from app.config import DATABASE_URL
from app.database.connection import get_db, Base
from app.database.models import User
```

---

That's everything you need to know about the API → Database connection! 🎉

For detailed explanations, see: `ARCHITECTURE_GUIDE.md`  
For visual flow, see: `DATABASE_CONNECTION_FLOW.txt`

