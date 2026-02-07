# 🏗️ Architecture Guide: API to Database Connection

## Overview of the Flow

```
Frontend (React)
    ↓ fetch() call
FastAPI Routes (Python)
    ↓ Depends(get_db)
Database Session (SQLAlchemy)
    ↓ SQL queries
PostgreSQL Database
    ↓ Results
Back to Frontend
```

Let me explain each layer in detail!

---

## 📁 File Structure

```
backend/
├── app/
│   ├── config.py              # Database URL and config
│   ├── database/
│   │   ├── connection.py      # Database engine & session setup
│   │   └── models.py          # SQLAlchemy models (User, etc.)
│   ├── routers/
│   │   ├── auth.py            # Authentication endpoints
│   │   └── settings.py        # Settings endpoints
│   └── web.py                 # Main FastAPI app
└── run.py                     # Server entry point

frontend/
└── src/
    ├── components/
    │   └── LoginModal.jsx     # Makes API calls
    └── pages/
        └── Settings.jsx       # Makes API calls
```

---

## 🔹 1. DATABASE CONFIGURATION

### File: `backend/app/config.py`

**Purpose**: Stores database connection settings.

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL - tells SQLAlchemy how to connect
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:pukan2001@localhost:1234/weather_cloth_rec"
)
#              ^^^^^^^^^^   ^^^^^^^^    ^^^^^^^^^  ^^^^  ^^^^^^^^^^^^^^^^
#              protocol     username    password   host  database name
```

**What it does**:
- Loads environment variables from `.env` file
- Defines `DATABASE_URL` - the connection string for PostgreSQL
- Format: `postgresql://username:password@host:port/database_name`

---

## 🔹 2. DATABASE CONNECTION SETUP

### File: `backend/app/database/connection.py`

**Purpose**: Creates the database engine and session factory.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

# Step 1: Create Base class for models
Base = declarative_base()

# Step 2: Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check if connection is alive
    echo=False           # Set True to see SQL queries in logs
)

# Step 3: Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Step 4: Dependency function for FastAPI
def get_db():
    """
    Provides a database session to route handlers.
    Automatically closes session when done.
    """
    db = SessionLocal()  # Create new session
    try:
        yield db         # Give session to route handler
    finally:
        db.close()       # Always close session
```

**Key Components**:

1. **`Base`** - Base class all models inherit from
2. **`engine`** - Manages connections to PostgreSQL
3. **`SessionLocal`** - Factory that creates database sessions
4. **`get_db()`** - Dependency function that FastAPI uses

**How `get_db()` works**:
```python
# When FastAPI calls get_db():
db = SessionLocal()    # 1. Create new session
yield db               # 2. Give it to the route handler
                       # 3. Route handler uses it
db.close()             # 4. Close when done (even if error)
```

---

## 🔹 3. DATABASE MODELS

### File: `backend/app/database/models.py`

**Purpose**: Defines database table structure using SQLAlchemy ORM.

```python
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database.connection import Base

class User(Base):
    """
    Represents the 'users' table in PostgreSQL.
    Each attribute = a column in the table.
    """
    __tablename__ = "users"
    
    # Columns
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    comfort_temperature = Column(Float, default=70.0)
    
    # New columns for settings
    saved_latitude = Column(Float, nullable=True)
    saved_longitude = Column(Float, nullable=True)
    location_name = Column(String, nullable=True)
    clothing_list = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**What SQLAlchemy does**:
- Converts Python class → SQL table definition
- Converts Python operations → SQL queries
- Converts SQL results → Python objects

**Example**:
```python
# Python code:
user = db.query(User).filter(User.email == "test@example.com").first()

# SQLAlchemy generates SQL:
SELECT * FROM users WHERE email = 'test@example.com' LIMIT 1;

# Returns Python object:
user.email  # → "test@example.com"
user.comfort_temperature  # → 70.0
```

---

## 🔹 4. API ROUTES (ENDPOINTS)

### File: `backend/app/routers/settings.py`

**Purpose**: Defines API endpoints that handle HTTP requests.

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import User

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/{user_id}")
def get_user_settings(
    user_id: int,                    # From URL path
    db: Session = Depends(get_db)    # Injected by FastAPI
):
    """
    GET /settings/3
    
    Flow:
    1. FastAPI calls get_db() to get database session
    2. Passes session to this function as 'db'
    3. Function uses db to query database
    4. Returns data to frontend
    """
    
    # Query database using SQLAlchemy ORM
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # FastAPI automatically converts to JSON
    return user
```

**How `Depends(get_db)` works**:

```python
# When request comes in:
@router.get("/{user_id}")
def get_user_settings(
    user_id: int,
    db: Session = Depends(get_db)  # ← FastAPI magic happens here
):
    # FastAPI does this automatically:
    # 1. Call get_db()
    # 2. Get database session
    # 3. Pass as 'db' parameter
    # 4. When function ends, close session
```

**Another Example - Update Settings**:

```python
@router.put("/{user_id}")
def update_user_settings(
    user_id: int,
    settings: UserSettingsUpdate,    # Request body
    db: Session = Depends(get_db)    # Database session
):
    """
    PUT /settings/3
    Body: {"comfort_temperature": 72.0, "location_name": "Home"}
    
    Flow:
    1. Get database session
    2. Find user in database
    3. Update user attributes
    4. Commit changes to database
    5. Return updated user
    """
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if settings.comfort_temperature is not None:
        user.comfort_temperature = settings.comfort_temperature
    
    if settings.location_name is not None:
        user.location_name = settings.location_name
    
    # Save to database
    db.commit()        # Execute UPDATE query
    db.refresh(user)   # Reload from database
    
    return user
```

---

## 🔹 5. MAIN FASTAPI APP

### File: `backend/app/web.py`

**Purpose**: Creates FastAPI app and registers routes.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, settings

# Create FastAPI application
app = FastAPI(
    title="Weather Clothing Recommendation API",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Frontend can call API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)       # /auth/* endpoints
app.include_router(settings.router)   # /settings/* endpoints

# Now you can call:
# - POST /auth/login
# - GET /settings/3
# - PUT /settings/3
# etc.
```

**What `include_router` does**:
```python
# Before:
app.include_router(settings.router)

# After, these endpoints exist:
# GET    /settings/{user_id}
# PUT    /settings/{user_id}
# POST   /settings/{user_id}/clothing
# DELETE /settings/{user_id}/clothing/{item_index}
```

---

## 🔹 6. FRONTEND API CALLS

### File: `frontend/src/pages/Settings.jsx`

**Purpose**: Makes HTTP requests to backend API.

```javascript
const BASE_URL = 'http://127.0.0.1:8000';

// Function to fetch user settings
const fetchSettings = async (userId) => {
  try {
    // Step 1: Make HTTP GET request
    const response = await fetch(`${BASE_URL}/settings/${userId}`);
    //                              ↓
    //                    http://127.0.0.1:8000/settings/3
    
    // Step 2: Check if request succeeded
    if (!response.ok) {
      throw new Error('Failed to fetch settings');
    }
    
    // Step 3: Parse JSON response
    const data = await response.json();
    //    ↓
    // {
    //   id: 3,
    //   email: "test@example.com",
    //   comfort_temperature: 70.0,
    //   clothing_list: [...]
    // }
    
    // Step 4: Update React state
    setSettings(data);
    
  } catch (err) {
    console.error('Error:', err);
  }
};
```

**Example - Update Settings**:

```javascript
const handleSaveSettings = async () => {
  try {
    // Step 1: Prepare data
    const body = {
      comfort_temperature: 72.0,
      location_name: "Home",
      saved_latitude: 40.7128,
      saved_longitude: -74.006
    };
    
    // Step 2: Make HTTP PUT request
    const response = await fetch(`${BASE_URL}/settings/${user.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    
    // Step 3: Handle response
    if (!response.ok) {
      throw new Error('Failed to save');
    }
    
    const data = await response.json();
    setSettings(data);  // Update UI
    
  } catch (err) {
    console.error('Error:', err);
  }
};
```

---

## 🔄 COMPLETE FLOW EXAMPLE

### Scenario: User updates comfort temperature

#### 1️⃣ **Frontend (Settings.jsx)**

```javascript
// User changes temperature to 72°F and clicks "Save"
const handleSaveSettings = async () => {
  const response = await fetch('http://127.0.0.1:8000/settings/3', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ comfort_temperature: 72.0 })
  });
  
  const data = await response.json();
  console.log(data);  // Updated user object
};
```

#### 2️⃣ **HTTP Request**

```http
PUT /settings/3 HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{"comfort_temperature": 72.0}
```

#### 3️⃣ **Backend Route (settings.py)**

```python
@router.put("/{user_id}")
def update_user_settings(
    user_id: int,                      # user_id = 3
    settings: UserSettingsUpdate,      # {"comfort_temperature": 72.0}
    db: Session = Depends(get_db)      # Database session injected
):
    # FastAPI calls: db = get_db()
    # Now we have database session
    
    # Find user in database
    user = db.query(User).filter(User.id == user_id).first()
    # SQL: SELECT * FROM users WHERE id = 3 LIMIT 1;
    
    # Update attribute
    user.comfort_temperature = 72.0
    
    # Save to database
    db.commit()
    # SQL: UPDATE users SET comfort_temperature = 72.0 WHERE id = 3;
    
    # Reload from database
    db.refresh(user)
    # SQL: SELECT * FROM users WHERE id = 3;
    
    # Return to frontend (FastAPI converts to JSON)
    return user
```

#### 4️⃣ **Database (PostgreSQL)**

```sql
-- SQLAlchemy generates and executes:
UPDATE users 
SET comfort_temperature = 72.0, 
    updated_at = NOW() 
WHERE id = 3;

-- Then fetches result:
SELECT * FROM users WHERE id = 3;
```

#### 5️⃣ **Response to Frontend**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 3,
  "username": "testuser",
  "email": "test@example.com",
  "comfort_temperature": 72.0,
  "saved_latitude": 40.7128,
  "saved_longitude": -74.006,
  "location_name": "New York, NY",
  "clothing_list": [...]
}
```

#### 6️⃣ **Frontend Updates UI**

```javascript
const data = await response.json();
setSettings(data);  // React re-renders with new data
// User sees: "Comfort Temperature: 72°F"
```

---

## 📊 Key Concepts Explained

### 1. **Dependency Injection** (`Depends(get_db)`)

**What it is**: FastAPI automatically provides the database session.

```python
# Without dependency injection (manual):
def get_user(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user
    finally:
        db.close()

# With dependency injection (automatic):
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user
    # FastAPI closes db automatically!
```

**Benefits**:
- ✅ Automatic session management
- ✅ Session always closed (even on error)
- ✅ Cleaner code
- ✅ Easy to test

### 2. **ORM (Object-Relational Mapping)**

**What it is**: SQLAlchemy converts Python code ↔ SQL queries.

```python
# Python ORM code:
user = db.query(User).filter(User.email == "test@example.com").first()

# Is converted to SQL:
SELECT * FROM users WHERE email = 'test@example.com' LIMIT 1;

# Result is converted back to Python object:
print(user.email)  # "test@example.com"
print(user.comfort_temperature)  # 70.0
```

**Why use ORM?**
- ✅ Write Python instead of SQL
- ✅ Type-safe (IDE autocomplete)
- ✅ Database-agnostic (switch PostgreSQL → MySQL easily)
- ✅ Automatic SQL injection prevention

### 3. **Session Management**

**What is a session?**
A session is a workspace for database operations.

```python
# Create session
db = SessionLocal()

# Make changes (in memory only)
user.comfort_temperature = 72.0

# Save to database (execute SQL)
db.commit()

# Discard changes (rollback)
db.rollback()

# Close session (release connection)
db.close()
```

**Session lifecycle**:
```
1. Create  → db = SessionLocal()
2. Query   → db.query(User)...
3. Modify  → user.temperature = 72
4. Save    → db.commit()
5. Close   → db.close()
```

---

## 🔍 Debugging Tips

### See SQL Queries

In `connection.py`, set `echo=True`:

```python
engine = create_engine(
    DATABASE_URL,
    echo=True  # Print all SQL queries
)
```

Output:
```
INFO:sqlalchemy.engine.Engine:SELECT users.id, users.email...
INFO:sqlalchemy.engine.Engine:UPDATE users SET comfort_temperature = 72.0
```

### Check Database Session

Add logging in routes:

```python
@router.get("/{user_id}")
def get_user_settings(user_id: int, db: Session = Depends(get_db)):
    print(f"Database session: {db}")
    print(f"Querying user_id: {user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    print(f"Found user: {user.email if user else None}")
    return user
```

### Test API Directly

Use PowerShell:

```powershell
# GET request
Invoke-WebRequest -Uri http://localhost:8000/settings/3 -UseBasicParsing

# PUT request
$body = @{comfort_temperature=72.0} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/settings/3 `
  -Method PUT -Body $body -ContentType "application/json"
```

---

## 📚 Summary

**The Complete Stack**:

```
┌─────────────────────────────────────────────────┐
│ Frontend (React/JavaScript)                     │
│ - Settings.jsx: fetch()                        │
│ - LoginModal.jsx: fetch()                      │
└────────────────┬────────────────────────────────┘
                 │ HTTP Request
                 ↓
┌─────────────────────────────────────────────────┐
│ FastAPI (Python)                                │
│ - web.py: Main app                             │
│ - routers/settings.py: Endpoints               │
│ - routers/auth.py: Authentication              │
└────────────────┬────────────────────────────────┘
                 │ Depends(get_db)
                 ↓
┌─────────────────────────────────────────────────┐
│ SQLAlchemy ORM (Python)                         │
│ - connection.py: get_db(), engine, SessionLocal│
│ - models.py: User class                        │
└────────────────┬────────────────────────────────┘
                 │ SQL Queries
                 ↓
┌─────────────────────────────────────────────────┐
│ PostgreSQL Database                             │
│ - users table                                  │
│ - weather_cache table                          │
│ - recommendations table                        │
└─────────────────────────────────────────────────┘
```

**Key Files**:
1. **config.py** - Database URL
2. **connection.py** - Engine, SessionLocal, get_db()
3. **models.py** - User, table definitions
4. **routers/*.py** - API endpoints
5. **web.py** - Main app, registers routes
6. **Frontend** - fetch() calls to API

**Key Functions**:
- `get_db()` - Provides database session
- `db.query()` - Query database
- `db.commit()` - Save changes
- `db.close()` - Close session
- `Depends(get_db)` - Dependency injection

That's the complete flow from frontend API call to database and back! 🎉

