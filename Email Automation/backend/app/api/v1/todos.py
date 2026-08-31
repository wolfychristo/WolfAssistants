from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.tenant_database import get_tenant_db_dependency
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate, TodoOut
from app.core.config import settings
from jose import jwt

router = APIRouter()


def _get_owner_from_request(request: Request) -> str:
    """Extract user email from JWT token in request headers."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/", response_model=List[TodoOut])
def list_todos(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Get all todos for the authenticated user."""
    owner = _get_owner_from_request(request)
    try:
        # Debug: Check if the table exists
        print(f"Fetching todos for {owner}")
        print(f"Database URL: {db.bind.url}")
        
        # Try to query the table
        todos = db.query(Todo).filter(Todo.owner_email == owner).order_by(Todo.created_at.desc()).all()
        print(f"Found {len(todos)} todos")
        return todos
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching todos for {owner}: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return []


@router.post("/", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoCreate, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Create a new todo for the authenticated user."""
    owner = _get_owner_from_request(request)
    
    # Validate priority
    if payload.priority not in ["low", "medium", "high"]:
        raise HTTPException(status_code=422, detail="Priority must be 'low', 'medium', or 'high'")
    
    try:
        print(f"Creating todo for {owner}")
        print(f"Database URL: {db.bind.url}")
        print(f"Payload: {payload}")
        
        todo = Todo(
            title=payload.title,
            description=payload.description,
            completed=payload.completed,
            due_date=payload.due_date,
            priority=payload.priority,
            owner_email=owner
        )
        
        db.add(todo)
        db.commit()
        db.refresh(todo)
        print(f"Successfully created todo with ID: {todo.id}")
        return todo
    except Exception as e:
        db.rollback()
        print(f"Error creating todo for {owner}: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create todo: {str(e)}")


@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Get a specific todo by ID."""
    owner = _get_owner_from_request(request)
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_email == owner).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoUpdate, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Update a specific todo."""
    owner = _get_owner_from_request(request)
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_email == owner).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # Validate priority if provided
    if payload.priority and payload.priority not in ["low", "medium", "high"]:
        raise HTTPException(status_code=422, detail="Priority must be 'low', 'medium', or 'high'")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(todo, field, value)
    
    todo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Delete a specific todo."""
    owner = _get_owner_from_request(request)
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_email == owner).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    db.delete(todo)
    db.commit()
    return None


@router.patch("/{todo_id}/toggle", response_model=TodoOut)
def toggle_todo(todo_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Toggle the completed status of a todo."""
    owner = _get_owner_from_request(request)
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_email == owner).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    todo.completed = not todo.completed
    todo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(todo)
    return todo
