"""
Utility functions for generating and parsing shareable links using public_id.
"""
from typing import Literal, Optional, Tuple
import os

EntityType = Literal["email", "contact", "meeting", "chat"]


def generate_entity_link(
    entity_type: EntityType, 
    public_id: str, 
    base_url: Optional[str] = None
) -> str:
    """
    Generate a shareable link for an entity.
    
    Args:
        entity_type: Type of entity (email, contact, meeting, chat)
        public_id: The unique UUID of the entity
        base_url: Base URL of the application (defaults to env variable)
    
    Returns:
        Full shareable URL
    
    Examples:
        >>> generate_entity_link("email", "550e8400-e29b-41d4-a716-446655440000")
        "http://localhost:3000/emails/550e8400-e29b-41d4-a716-446655440000"
    """
    if base_url is None:
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Remove trailing slash if present
    base_url = base_url.rstrip("/")
    
    # Map entity types to URL paths
    # Note: "chat" maps to "chat" (not "chats") for sessions
    path_map = {
        "email": "emails",
        "contact": "contacts",
        "meeting": "meetings",
        "chat": "chat"
    }
    
    path = path_map.get(entity_type, entity_type)
    return f"{base_url}/{path}/{public_id}"


def parse_entity_link(url: str) -> Optional[Tuple[EntityType, str]]:
    """
    Parse a shareable link to extract entity type and public_id.
    
    Args:
        url: The shareable URL
    
    Returns:
        Tuple of (entity_type, public_id) or None if invalid
    
    Examples:
        >>> parse_entity_link("http://localhost:3000/emails/550e8400-e29b-41d4-a716-446655440000")
        ("email", "550e8400-e29b-41d4-a716-446655440000")
    """
    try:
        # Extract path from URL
        if "://" in url:
            # Full URL - extract path after domain
            parts = url.split("/", 3)
            if len(parts) >= 4:
                path = parts[3]  # Get path after domain
            else:
                return None
        else:
            # Assume it's already a path
            path = url.lstrip("/")
        
        # Split path into components
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) < 2:
            return None
        
        # Get entity type (remove plural 's' if present)
        entity_path = path_parts[0]
        public_id = path_parts[1]
        
        # Map paths back to entity types
        entity_map = {
            "emails": "email",
            "contacts": "contact",
            "meetings": "meeting",
            "chat": "chat"
        }
        
        entity_type = entity_map.get(entity_path)
        
        if entity_type and public_id:
            # Basic UUID validation (36 chars with hyphens)
            if len(public_id) == 36 and public_id.count("-") == 4:
                return (entity_type, public_id)
        
        return None
        
    except Exception:
        return None


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID format.
    
    Args:
        uuid_string: String to validate
    
    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        # Basic format check: 36 characters with 4 hyphens
        if len(uuid_string) == 36 and uuid_string.count("-") == 4:
            # Try to parse it
            import uuid as uuid_lib
            uuid_lib.UUID(uuid_string)
            return True
        return False
    except (ValueError, AttributeError):
        return False
