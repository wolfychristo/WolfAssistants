"""API endpoints for chat session management."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.chat_session import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionResponse, 
    ChatSessionCreate, 
    ChatSessionUpdate,
    ChatSessionWithMessages,
    ChatSessionListResponse,
    ChatMessageResponse
)

router = APIRouter()


def _get_owner_from_request(request: Request) -> str:
    """Extract owner email from JWT token in Authorization header."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        return email
    except Exception as e:
        # SECURITY FIX: Do not allow unverified JWT tokens
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/sessions", response_model=ChatSessionListResponse)
async def get_chat_sessions(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for the current user."""
    owner = _get_owner_from_request(request)
    query = db.query(ChatSession).filter(ChatSession.owner_email == owner)
    
    if not include_inactive:
        query = query.filter(ChatSession.is_active == True)
    
    # Get total count
    total = query.count()
    
    # Get sessions with message count, ordered by last message time (nulls last) then by creation time
    sessions = query.order_by(desc(ChatSession.last_message_at).nullslast(), desc(ChatSession.created_at)).offset(skip).limit(limit).all()
    
    # Add message count to each session
    session_responses = []
    for session in sessions:
        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
        session_data = ChatSessionResponse.from_orm(session)
        session_data.message_count = message_count
        session_responses.append(session_data)
    
    return ChatSessionListResponse(sessions=session_responses, total=total)


@router.get("/sessions/by-public-id/{public_id}", response_model=ChatSessionWithMessages)
async def get_chat_session_by_public_id(
    public_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get a specific chat session by public_id (UUID) with all messages."""
    owner = _get_owner_from_request(request)
    session = db.query(ChatSession).filter(
        ChatSession.public_id == public_id,
        ChatSession.owner_email == owner
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Get messages for this session
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    session_data = ChatSessionWithMessages.from_orm(session)
    session_data.messages = [ChatMessageResponse.from_orm(msg) for msg in messages]
    
    return session_data


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get a specific chat session with all messages."""
    owner = _get_owner_from_request(request)
    
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.owner_email == owner
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Get messages for this session
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        session_data = ChatSessionWithMessages.from_orm(session)
        session_data.messages = [ChatMessageResponse.from_orm(msg) for msg in messages]
        
        return session_data
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading chat session: {str(e)}")


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    owner = _get_owner_from_request(request)
    # Generate title if not provided
    title = session_data.title
    if not title:
        if session_data.contact_name:
            title = f"Chat with {session_data.contact_name}"
        else:
            title = f"New Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Deactivate other sessions if this is about a specific contact
    if session_data.contact_email:
        db.query(ChatSession).filter(
            ChatSession.owner_email == owner,
            ChatSession.contact_email == session_data.contact_email,
            ChatSession.is_active == True
        ).update({"is_active": False})
    
    # Create new session
    new_session = ChatSession(
        owner_email=owner,
        title=title,
        contact_name=session_data.contact_name,
        contact_email=session_data.contact_email,
        is_active=True
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return ChatSessionResponse.from_orm(new_session)


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: int,
    session_data: ChatSessionUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a chat session."""
    owner = _get_owner_from_request(request)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_email == owner
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Update fields
    update_data = {}
    if session_data.title is not None:
        update_data['title'] = session_data.title
    if session_data.is_active is not None:
        update_data['is_active'] = session_data.is_active
    
    if update_data:
        update_data['updated_at'] = datetime.now()
        db.query(ChatSession).filter(ChatSession.id == session_id).update(update_data)
    
    db.commit()
    db.refresh(session)
    
    return ChatSessionResponse.from_orm(session)


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a chat session and all its messages."""
    owner = _get_owner_from_request(request)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_email == owner
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Delete session (messages will be cascade deleted)
    db.delete(session)
    db.commit()
    
    return {"message": "Chat session deleted successfully"}


@router.post("/sessions/{session_id}/activate")
async def activate_chat_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Activate a chat session and deactivate others."""
    owner = _get_owner_from_request(request)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_email == owner
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Deactivate all other sessions for this user
    db.query(ChatSession).filter(
        ChatSession.owner_email == owner,
        ChatSession.id != session_id
    ).update({"is_active": False})
    
    # Activate this session
    db.query(ChatSession).filter(ChatSession.id == session_id).update({
        "is_active": True,
        "updated_at": datetime.now()
    })
    
    db.commit()
    
    return {"message": "Chat session activated successfully"}
