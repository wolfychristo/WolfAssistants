from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.database import get_db
from app.api.v1.emails import _send_email, get_ist_now
from app.core.debug_logger import write_debug_log
from app.api.v1.meetings import create_meeting  # type: ignore
from jose import jwt
from app.models.contact import Contact
from app.models.email import Email, EmailStatus
from app.models.meeting import Meeting
from app.models.chat_session import ChatSession, ChatMessage
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageCreate, ChatMessageResponse
from datetime import datetime, timedelta

router = APIRouter()
def _parse_email_send_time_ist(message: str) -> Optional[datetime]:
    """Parse natural time expressions for scheduling.
    Supports:
      - today/tomorrow with time (e.g., 'today at 2:55 PM', 'tomorrow 09:00')
      - relative times (e.g., 'in 2 hours', 'in 30 minutes', 'in 2 hours 15 minutes')
      - calendar dates in DD/MM[/YYYY] or DD-MM[-YYYY] with optional time (defaults to 09:00)
    Returns a timezone-naive datetime in IST, aligned with get_ist_now().
    """
    try:
        import re
        from datetime import timedelta
        m = (message or "").lower().strip()
        now_ist = get_ist_now()

        # 1) Relative: in X hours Y minutes
        rel_hours = re.search(r"\bin\s+(\d{1,3})\s*hours?\b", m)
        rel_minutes = re.search(r"\bin\s+(\d{1,3})\s*minutes?\b", m)
        # Handle combined 'in 2 hours 15 minutes'
        combo = re.search(r"\bin\s+(\d{1,3})\s*hours?\s*(\d{1,3})\s*minutes?\b", m)
        if combo:
            h = int(combo.group(1) or 0)
            mins = int(combo.group(2) or 0)
            return now_ist + timedelta(hours=h, minutes=mins)
        if rel_hours and rel_minutes is None:
            h = int(rel_hours.group(1))
            return now_ist + timedelta(hours=h)
        if rel_minutes and rel_hours is None:
            mins = int(rel_minutes.group(1))
            return now_ist + timedelta(minutes=mins)

        # Extract time component if present (HH:MM with optional AM/PM)
        time_match = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", m)
        hour = None
        minute = None
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            mer = time_match.group(3)
            if mer:
                if mer == 'pm' and hour < 12:
                    hour += 12
                if mer == 'am' and hour == 12:
                    hour = 0

        # 2) Explicit date: DD/MM[/YYYY] or DD-MM[-YYYY]
        date_match = re.search(r"\b(\d{1,2})[\/-](\d{1,2})(?:[\/-](\d{2,4}))?\b", m)
        if date_match:
            d = int(date_match.group(1))
            mo = int(date_match.group(2))
            yr_raw = date_match.group(3)
            if yr_raw is None:
                yr = now_ist.year
            else:
                yr_val = int(yr_raw)
                yr = (2000 + yr_val) if yr_val < 100 else yr_val
            # Default time if not provided
            h = hour if hour is not None else 9
            mi = minute if minute is not None else 0
            try:
                return datetime(year=yr, month=mo, day=d, hour=h, minute=mi)
            except Exception:
                return None

        # 3) Today/Tomorrow with time
        if time_match:
            h = hour if hour is not None else 9
            mi = minute if minute is not None else 0
            target_date = now_ist.date()
            if 'tomorrow' in m:
                target_date = target_date + timedelta(days=1)
            target_dt = datetime.combine(target_date, datetime.min.time()).replace(hour=h, minute=mi)
            # If neither today nor tomorrow specified and time already passed, assume next day
            if 'today' not in m and 'tomorrow' not in m and target_dt <= now_ist:
                target_dt = target_dt + timedelta(days=1)
            return target_dt

        return None
    except Exception:
        return None

def _get_owner_from_request(request: Request) -> str:
    """Extract owner email from JWT token with proper signature verification."""
    from jose import jwt
    from app.core.config import settings
    
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        # SECURITY FIX: Properly verify JWT signature instead of using unverified claims
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token format")

def _parse_intent_rule_based(message: str) -> Dict[str, Any]:
    m = (message or '').strip()
    low = m.lower()
    import re
    email_matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", m)

    # Extract lightweight slots if user wrote explicit markers
    subject_match = re.search(r"subject\s*[:\-]\s*(.+)$", m, re.IGNORECASE)
    body_match = re.search(r"body\s*[:\-]\s*([\s\S]+)$", m, re.IGNORECASE)
    extracted_subject = subject_match.group(1).strip() if subject_match else ''
    extracted_body = body_match.group(1).strip() if body_match else ''

    # Contact lookup intents - check this BEFORE web research
    if any(keyword in low for keyword in ['look up contact', 'find contact', 'contact information', 'lookup contact', 'search contact', 'find person']):
        return {"intent": "lookup_contact", "query": message}
    
    # Web research intents
    if any(keyword in low for keyword in ['research', 'look up', 'find information', 'search for', 'web search', 'google']):
        return {"intent": "web_research", "query": message}

    # Send email intents (broad verbs + any email address present)
    if (('send' in low or 'compose' in low or 'write' in low or low.startswith('email ')) and email_matches):
        to_addr = email_matches[0]
        return {"intent": "send_email", "to": to_addr, "subject": extracted_subject, "body": extracted_body}
    
    # Enhanced send email parsing for "send email to [name] about [topic]"
    if ('send' in low and 'email' in low and 'to' in low) or low.startswith('send an email to') or low.startswith('send email to') or low.startswith('compose an email to') or ('write' in low and 'email' in low and 'to' in low):
        # Extract recipient name after "to"
        recipient_match = re.search(r"to\s+([^,\s]+)", m, re.IGNORECASE)
        to_addr = recipient_match.group(1).strip() if recipient_match else (email_matches[0] if email_matches else '')
        
        # Extract topic if present
        topic = _extract_email_topic(m)
        
        return {"intent": "send_email", "to": to_addr, "subject": extracted_subject, "body": extracted_body, "topic": topic}
    
    # Additional email patterns
    if ('help' in low and 'write' in low and 'email' in low) or ('help' in low and 'email' in low and 'to' in low):
        # Extract recipient name after "to"
        recipient_match = re.search(r"to\s+([^,\s]+)", m, re.IGNORECASE)
        to_addr = recipient_match.group(1).strip() if recipient_match else ''
        
        # Extract topic if present
        topic = _extract_email_topic(m)
        
        return {"intent": "send_email", "to": to_addr, "subject": extracted_subject, "body": extracted_body, "topic": topic}

    # Check inbox intents - check this FIRST to avoid conflicts with other intents
    if ('check' in low or 'refresh' in low or 'fetch' in low or 'pull' in low) and ('inbox' in low or 'email' in low or 'mail' in low):
        return {"intent": "check_inbox"}

    # Schedule meeting intents
    if (('schedule' in low or 'book' in low or 'arrange' in low or 'set up' in low or 'create' in low) and 
        ('meeting' in low or 'call' in low or 'appointment' in low)):
        return {"intent": "schedule_meeting"}
    
    # Also check for structured meeting responses like "Title: X, Time: Y"
    if ('title:' in low and ('time:' in low or 'from' in low and 'to' in low)):
        return {"intent": "schedule_meeting"}

    # Contact lookup intents - make this more specific to avoid false positives
    name_for_email = _extract_email_lookup_name(m)
    if name_for_email or (('email id' in low) or ('email address' in low) or 
        ('tell' in low and 'email' in low and ('s ' in low or 'me ' in low) and 'inbox' not in low and 'check' not in low) or
        ('look up' in low and 'contact' in low) or ('lookup' in low and 'contact' in low) or
        ('find' in low and 'contact' in low) or ('search' in low and 'contact' in low)):
        return {"intent": "lookup_contact", "query": (name_for_email or m).strip()}

    return {"intent": "chat"}

async def _generate_session_title(message: str, contact_name: Optional[str] = None, owner: Optional[str] = None) -> str:
    """Generate a meaningful session title based on the first message using AI, with fallback to rule-based."""
    if contact_name:
        return f"Chat with {contact_name}"
    
    # Try AI-powered title generation first
    if owner:
        try:
            from app.core.gemini_service import wolf_assistants_service
            
            def generate_title_prompt(context):
                user_message = context.get('message', '')
                prompt = f"""Generate a concise, meaningful title (3-6 words max) for a chat session based on this first message from the user.

User's first message: "{user_message}"

Requirements:
- Keep it short and descriptive (3-6 words maximum)
- Capture the main topic or intent
- Use title case (e.g., "Email Campaign Strategy", "Meeting Scheduling Help")
- Avoid generic titles like "Chat" or "Conversation"
- If it's a greeting, use "General Chat"
- If it's about emails, meetings, contacts, or tasks, make it specific

Return ONLY the title, nothing else."""
                return prompt
            
            result = await wolf_assistants_service.make_request(
                user_email=owner,
                endpoint="generate_session_title",
                request_type="generate_title",
                prompt_func=generate_title_prompt,
                context={"message": message},
                use_cache=False,
                priority="low"  # Low priority since this is not critical
            )
            
            if result.get('success') and result.get('response'):
                ai_title = result.get('response', '').strip()
                # Clean up the response (remove quotes, extra whitespace, etc.)
                ai_title = ai_title.strip('"\'`').strip()
                # Remove any markdown code blocks if present
                if ai_title.startswith('```'):
                    lines = ai_title.split('\n')
                    ai_title = '\n'.join(lines[1:-1]) if len(lines) > 2 else ai_title
                    ai_title = ai_title.strip('"\'`').strip()
                # Limit length to 50 characters
                if ai_title and len(ai_title) <= 50 and len(ai_title) > 0:
                    try:
                        write_debug_log("simon.py:_generate_session_title", "AI title generated successfully", {
                            "original_message": message[:100],
                            "generated_title": ai_title
                        }, "I")
                    except:
                        pass
                    return ai_title
            else:
                # Log why AI generation failed
                try:
                    write_debug_log("simon.py:_generate_session_title", "AI title generation returned no result", {
                        "success": result.get('success'),
                        "error": result.get('error'),
                        "message": result.get('message')
                    }, "W")
                except:
                    pass
        except Exception as e:
            # Log but don't fail - fall back to rule-based
            try:
                write_debug_log("simon.py:_generate_session_title", "AI title generation failed, using fallback", {
                    "error": str(e),
                    "error_type": type(e).__name__
                }, "W")
            except:
                pass
    
    # Fallback to rule-based title generation
    message_lower = message.lower().strip()
    
    # Extract key topics from the message
    if any(word in message_lower for word in ['time', 'what time', 'current time']):
        return "Time Inquiry"
    elif any(word in message_lower for word in ['date', 'today', 'what date', 'current date']):
        return "Date Inquiry"
    elif any(word in message_lower for word in ['email', 'send email', 'compose']):
        return "Email Discussion"
    elif any(word in message_lower for word in ['meeting', 'schedule', 'calendar', 'appointment']):
        return "Meeting Discussion"
    elif any(word in message_lower for word in ['help', 'what can you do', 'capabilities']):
        return "Help & Capabilities"
    elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "General Chat"
    elif len(message) > 50:
        # For longer messages, use first few words
        words = message.split()[:4]
        return " ".join(words) + ("..." if len(message.split()) > 4 else "")
    else:
        # For shorter messages, use the message itself (truncated if too long)
        return message[:30] + ("..." if len(message) > 30 else "")

def _extract_email_lookup_name(text: str) -> str:
    import re
    t = text or ''
    # Pattern 1: "White's email" or "White's email ID"
    m = re.search(r"([A-Za-z .]+)'s\s+email\s*(?:id|address)?", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Pattern 2: "email id of White" or "email address of White"
    m = re.search(r"email\s+(?:id|address)\s+of\s+([A-Za-z .]+)", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Pattern 3: "tell me White's email" or "tell me White email"
    m = re.search(r"tell\s+(?:me\s+)?([A-Za-z .]+)'?s?\s+(?:email|email\s+(?:id|address))", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Pattern 4: "White email" or "White email ID"
    m = re.search(r"([A-Za-z .]+)\s+email\s*(?:id|address)?", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Pattern 5: "can you tell White's email" - more flexible
    m = re.search(r"can\s+you\s+tell\s+([A-Za-z .]+)'?s?\s+email", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""

def _lookup_contact_email(owner: str, name_or_hint: str, db: Session) -> Dict[str, Any]:
    """Return {status, matches:[{name,email}], best?:{name,email}}"""
    hint = (name_or_hint or '').strip()
    if not hint:
        return {"status": "no_query"}
    # If an email is provided, return it directly
    emails = _extract_emails(hint)
    if emails:
        return {"status": "ok", "best": {"name": emails[0], "email": emails[0]}, "matches": [{"name": emails[0], "email": emails[0]}]}

    hint_l = hint.lower()
    matches: list[Dict[str, str]] = []
    try:
        rows = db.query(Contact).filter(Contact.owner_email == owner).all()
        for c in rows:
            nm = (c.name or '').strip()
            em = (c.email or '').strip()
            comp = (c.company or '').strip()
            if not em:
                continue
            hay = f"{nm} {em} {comp}".lower()
            if hint_l in hay:
                matches.append({"name": nm or em, "email": em})
    except Exception:
        pass

    if not matches:
        # Look into recent emails last 200
        try:
            threads = (
                db.query(Email)
                .filter(Email.owner_email == owner)
                .order_by((Email.received_at.isnot(None)).desc(), Email.received_at.desc(), (Email.sent_at.isnot(None)).desc(), Email.sent_at.desc())
                .limit(200)
                .all()
            )
            seen: set[str] = set()
            for e in threads:
                for addr in [getattr(e, 'from_address', None), getattr(e, 'to_address', None)]:
                    if not addr:
                        continue
                    s = str(addr).strip()
                    if not s or s in seen:
                        continue
                    if hint_l in s.lower():
                        matches.append({"name": s.split('@')[0].replace('.', ' ').title(), "email": s})
                        seen.add(s)
        except Exception:
            pass

    best = matches[0] if len(matches) == 1 else None
    return {"status": "ok" if matches else "not_found", "matches": matches[:5], "best": best}

def _extract_emails(text: str) -> list[str]:
    import re
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")

def _extract_email_topic(message: str) -> str:
    """Extract the topic/subject from email-related messages."""
    import re
    text = (message or '').lower()
    
    # Look for patterns like "about X", "regarding X", "on X", "re: X"
    patterns = [
        r"about\s+['\"]([^'\"]+)['\"]",  # about "Chocolate Chips Sales Plan"
        r"about\s+([^,.\n]+)",          # about Chocolate Chips Sales Plan
        r"regarding\s+['\"]([^'\"]+)['\"]",  # regarding "Chocolate Chips Sales Plan"
        r"regarding\s+([^,.\n]+)",      # regarding Chocolate Chips Sales Plan
        r"on\s+['\"]([^'\"]+)['\"]",    # on "Chocolate Chips Sales Plan"
        r"on\s+([^,.\n]+)",             # on Chocolate Chips Sales Plan
        r"re:\s*['\"]([^'\"]+)['\"]",   # re: "Chocolate Chips Sales Plan"
        r"re:\s*([^,.\n]+)",            # re: Chocolate Chips Sales Plan
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            topic = match.group(1).strip()
            if topic and len(topic) > 2:  # Avoid very short matches
                return topic
    
    return ""

def _guess_attendees(message: str, owner: str, db: Session) -> list[str]:
    # Priority 1: explicit emails in message
    emails = _extract_emails(message)
    if emails:
        return [emails[0]]
    # Priority 2: a name after 'with '
    import re
    m = re.search(r"with\s+([^,\n]+?)(?:\s+(tomorrow|today|on)\b|\s+from\b|\s+at\b|\s+regarding\b|$)", message, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        # loose match against contacts for this owner
        if candidate:
            q = db.query(Contact).filter(Contact.owner_email == owner)
            rows = q.all()
            for c in rows:
                name = (c.name or '').strip().lower()
                email = (c.email or '').strip()
                if not email:
                    continue
                if candidate.lower() in name or name in candidate.lower() or candidate.lower() in email.lower():
                    return [email]
    # Priority 3: pick most recent conversation partner from emails
    try:
        last_in = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.received).order_by(Email.received_at.desc()).first()
        if last_in and last_in.from_address:
            return [str(last_in.from_address)]
        last_out = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.sent).order_by(Email.sent_at.desc()).first()
        if last_out and last_out.to_address:
            return [str(last_out.to_address)]
    except Exception:
        pass
    return []

def _extract_meeting_title(message: str) -> str:
    """Extract meeting title from message like 'regarding "Chocolate chips selling"' or 'to discuss the Q4 product roadmap'"""
    import re
    
    # Look for "regarding" or "about" followed by quoted text
    match = re.search(r'(?:regarding|about|re:?)\s*["\']([^"\']+)["\']', message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Look for "to discuss" pattern - very common in meeting requests
    match = re.search(r'to\s+discuss\s+([^,.\n]+?)(?:\s+(?:on|at|from|to|with|meeting|call|tomorrow|today)|$)', message, re.IGNORECASE)
    if match:
        return f"Discussion: {match.group(1).strip()}"
    
    # Look for "regarding" or "about" followed by text until next keyword or end
    # This handles cases like "regarding next week Software product selling"
    match = re.search(r'(?:regarding|about|re:?)\s+([^,.\n]+?)(?:\s+(?:tomorrow|today|at|from|to|with|meeting|call|next\s+(?:week|month|quarter|year))|\.|$)', message, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Clean up the title - remove trailing punctuation and extra spaces
        title = re.sub(r'[.,;:]+$', '', title).strip()
        # Remove time-related words that might have been captured
        title = re.sub(r'\s+(?:next\s+(?:week|month|quarter|year)|tomorrow|today|this\s+(?:week|month|quarter|year))$', '', title, flags=re.IGNORECASE).strip()
        return title
    
    # Look for "for" pattern - "meeting for X"
    match = re.search(r'(?:meeting|call|appointment)\s+for\s+([^,.\n]+?)(?:\s+(?:on|at|from|to|with|tomorrow|today)|$)', message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Look for "to review" pattern
    match = re.search(r'to\s+review\s+([^,.\n]+?)(?:\s+(?:on|at|from|to|with|meeting|call|tomorrow|today)|$)', message, re.IGNORECASE)
    if match:
        return f"Review: {match.group(1).strip()}"
    
    # Look for "to plan" pattern
    match = re.search(r'to\s+plan\s+([^,.\n]+?)(?:\s+(?:on|at|from|to|with|meeting|call|tomorrow|today)|$)', message, re.IGNORECASE)
    if match:
        return f"Planning: {match.group(1).strip()}"
    
    return ""

def _generate_alternative_times(requested_start: datetime, requested_end: datetime, owner: str, db: Session) -> List[Dict[str, datetime]]:
    """Generate alternative time suggestions when there's a scheduling conflict."""
    alternatives = []
    duration = requested_end - requested_start
    
    # Strategy 1: Try same day, different times
    same_day = requested_start.date()
    
    # Try 1 hour later
    alt_start = requested_start.replace(hour=requested_start.hour + 1)
    alt_end = alt_start + duration
    if alt_start.date() == same_day and alt_start.hour < 18:  # Don't suggest after 6 PM
        alternatives.append({"start": alt_start, "end": alt_end, "reason": "1 hour later"})
    
    # Try 2 hours later
    alt_start = requested_start.replace(hour=requested_start.hour + 2)
    alt_end = alt_start + duration
    if alt_start.date() == same_day and alt_start.hour < 18:
        alternatives.append({"start": alt_start, "end": alt_end, "reason": "2 hours later"})
    
    # Try 1 hour earlier
    alt_start = requested_start.replace(hour=requested_start.hour - 1)
    alt_end = alt_start + duration
    if alt_start.date() == same_day and alt_start.hour >= 9:  # Don't suggest before 9 AM
        alternatives.append({"start": alt_start, "end": alt_end, "reason": "1 hour earlier"})
    
    # Strategy 2: Try next day at same time
    next_day_start = requested_start + timedelta(days=1)
    next_day_end = next_day_start + duration
    alternatives.append({"start": next_day_start, "end": next_day_end, "reason": "next day"})
    
    # Strategy 3: Try day after tomorrow
    day_after_start = requested_start + timedelta(days=2)
    day_after_end = day_after_start + duration
    alternatives.append({"start": day_after_start, "end": day_after_end, "reason": "day after tomorrow"})
    
    # Filter out alternatives that have conflicts
    valid_alternatives = []
    for alt in alternatives:
        try:
            # Check if this alternative time has conflicts
            conflicts = db.query(Meeting).filter(
                Meeting.owner_email == owner,
                Meeting.start_time < alt['end'],
                Meeting.end_time > alt['start'],
            ).count()
            
            if conflicts == 0:
                valid_alternatives.append(alt)
        except Exception:
            # If we can't check conflicts, include the alternative anyway
            valid_alternatives.append(alt)
    
    return valid_alternatives

def _parse_natural_times(message: str, now: datetime | None = None) -> tuple[str | None, str | None]:
    """Return (start_iso, end_iso) if we can parse phrases like:
    - tomorrow from 10:30 AM to 12:30 PM
    - tomorrow 10:30 AM to 12:30 PM
    - today 3 PM - 3:30 PM
    - tomorrow at 2pm
    - next Monday at 10:30 AM
    - October 9th, from 2:00 PM to 2:30 PM
    - Wednesday, October 9th, from 2:00 PM to 2:30 PM
    Fallback: None, None
    """
    import re
    ref = now or datetime.now()
    day = ref.date()
    text = (message or '').lower()

    # Handle specific date formats first
    # Pattern: "October 9th, from 2:00 PM to 2:30 PM" or "Wednesday, October 9th, from 2:00 PM to 2:30 PM"
    date_time_pattern = r"(?:(\w+day),\s*)?(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+from\s+(\d{1,2}:\d{2}\s*[ap]m)\s+to\s+(\d{1,2}:\d{2}\s*[ap]m)"
    date_match = re.search(date_time_pattern, text, re.IGNORECASE)
    if date_match:
        # Extract month name and day
        month_name = date_match.group(2).lower()
        day_num = int(date_match.group(3))
        start_time = date_match.group(4)
        end_time = date_match.group(5)
        
        # Convert month name to number
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        month_num = month_map.get(month_name)
        if month_num:
            # Use current year, or next year if the date has passed
            year = ref.year
            try:
                parsed_date = datetime(year, month_num, day_num)
                if parsed_date < ref:
                    parsed_date = datetime(year + 1, month_num, day_num)
                day = parsed_date.date()
                
                # Parse the times
                def parse_time_with_date(time_str, target_date):
                    time_str = time_str.strip().lower().replace(' ', '')
                    am = 'am' in time_str
                    pm = 'pm' in time_str
                    core = time_str.replace('am', '').replace('pm', '').strip()
                    if ':' in core:
                        hh, mm = core.split(':', 1)
                    else:
                        hh, mm = core, '00'
                    hour = int(hh)
                    minute = int(mm)
                    if pm and hour != 12:
                        hour += 12
                    if am and hour == 12:
                        hour = 0
                    return datetime(target_date.year, target_date.month, target_date.day, hour, minute)
                
                start_dt = parse_time_with_date(start_time, day)
                end_dt = parse_time_with_date(end_time, day)
                return start_dt.isoformat(), end_dt.isoformat()
            except ValueError:
                # Invalid date, fall back to current logic
                pass

    if 'tomorrow' in text:
        day = (ref + timedelta(days=1)).date()
    elif 'today' in text:
        day = ref.date()

    # First try: time range like 10:30 AM to 12:30 PM or 10 AM - 12:30 PM
    r = re.search(r"(\d{1,2}(:\d{2})?\s*[ap]m)\s*(?:to|\-|–)\s*(\d{1,2}(:\d{2})?\s*[ap]m)", text, re.IGNORECASE)
    if r:
        # Process the time range
        pass
    else:
        # Second try: single time like "at 2pm" or "at 10:30 AM"
        r = re.search(r"at\s+(\d{1,2}(:\d{2})?\s*[ap]m)", text, re.IGNORECASE)
        if r:
            # Create a 1-hour meeting by default
            start_time = r.group(1)
            # Parse start time and add 1 hour for end time
            def parse_single_time(time_str):
                time_str = time_str.strip().lower().replace(' ', '')
                am = 'am' in time_str
                pm = 'pm' in time_str
                core = time_str.replace('am', '').replace('pm', '').strip()
                if ':' in core:
                    hh, mm = core.split(':', 1)
                else:
                    hh, mm = core, '00'
                hour = int(hh)
                minute = int(mm)
                if pm and hour != 12:
                    hour += 12
                if am and hour == 12:
                    hour = 0
                return datetime(day.year, day.month, day.day, hour, minute)
            
            start_dt = parse_single_time(start_time)
            end_dt = start_dt + timedelta(hours=1)
            return start_dt.isoformat(), end_dt.isoformat()
        else:
            return None, None

    # Process time range if we found one
    def _parse_clock(s: str) -> tuple[int, int]:
        s = s.strip().lower().replace(' ', '')
        am = 'am' in s
        s = s.replace('am', '').replace('pm', '')
        if ':' in s:
            hh, mm = s.split(':', 1)
        else:
            hh, mm = s, '00'
        hour = int(hh)
        minute = int(mm)
        if 'pm' in r.group(0).lower() and not am:
            pass  # handled per token below
        # add 12 for PM except 12 PM
        if 'pm' in s + r.group(0).lower():
            # if the particular token had pm
            if 'pm' in s:
                if hour != 12:
                    hour += 12
        if 'am' in s and hour == 12:
            hour = 0
        return hour, minute

    start_token = r.group(1)
    end_token = r.group(3)
    # compute exact am/pm per token
    def to_dt(tok: str) -> datetime:
        tok_l = tok.lower()
        am = 'am' in tok_l
        pm = 'pm' in tok_l
        core = tok_l.replace('am', '').replace('pm', '').strip()
        if ':' in core:
            hh, mm = core.split(':', 1)
        else:
            hh, mm = core, '00'
        hour = int(hh)
        minute = int(mm)
        if pm and hour != 12:
            hour += 12
        if am and hour == 12:
            hour = 0
        return datetime(day.year, day.month, day.day, hour, minute)

    start_dt = to_dt(start_token)
    end_dt = to_dt(end_token)
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(minutes=30)
    return start_dt.isoformat(), end_dt.isoformat()

def _read_email_conversation_context(owner: str, recipient_email: str, db: Session) -> Dict[str, Any]:
    """Read email conversation context between owner and recipient.
    
    Returns:
        Dict containing:
        - original_cold_email: The first email sent to this recipient
        - last_client_response: The most recent email received from this recipient
        - conversation_count: Number of emails exchanged
        - last_interaction_date: Date of last interaction
        - conversation_summary: Brief summary of the conversation
    """
    try:
        # Get original cold email (first email sent to this recipient)
        original_cold_email = db.query(Email).filter(
            Email.owner_email == owner,
            Email.to_address == recipient_email,
            Email.status == EmailStatus.sent
        ).order_by(Email.sent_at.asc()).first()
        
        # Get last client response (most recent email received from this recipient)
        last_client_response = db.query(Email).filter(
            Email.owner_email == owner,
            Email.from_address == recipient_email,
            Email.status == EmailStatus.received
        ).order_by(Email.received_at.desc()).first()
        
        # Count total conversation exchanges
        sent_count = db.query(Email).filter(
            Email.owner_email == owner,
            Email.to_address == recipient_email,
            Email.status == EmailStatus.sent
        ).count()
        
        received_count = db.query(Email).filter(
            Email.owner_email == owner,
            Email.from_address == recipient_email,
            Email.status == EmailStatus.received
        ).count()
        
        conversation_count = sent_count + received_count
        
        # Get last interaction date
        last_interaction_date = None
        if original_cold_email and last_client_response:
            last_interaction_date = max(
                original_cold_email.sent_at or datetime.min,
                last_client_response.received_at or datetime.min
            )
        elif original_cold_email:
            last_interaction_date = original_cold_email.sent_at
        elif last_client_response:
            last_interaction_date = last_client_response.received_at
        
        # Generate conversation summary
        conversation_summary = ""
        if original_cold_email and last_client_response:
            conversation_summary = f"Started with cold email about '{original_cold_email.subject}'. Last response: '{last_client_response.subject}'"
        elif original_cold_email:
            conversation_summary = f"Cold email sent about '{original_cold_email.subject}' - no response yet"
        elif last_client_response:
            conversation_summary = f"Received email about '{last_client_response.subject}' - no previous context"
        
        return {
            "original_cold_email": original_cold_email,
            "last_client_response": last_client_response,
            "conversation_count": conversation_count,
            "last_interaction_date": last_interaction_date,
            "conversation_summary": conversation_summary,
            "sent_count": sent_count,
            "received_count": received_count
        }
    except Exception as e:
        # Return empty context on error
        return {
            "original_cold_email": None,
            "last_client_response": None,
            "conversation_count": 0,
            "last_interaction_date": None,
            "conversation_summary": "No conversation context available",
            "sent_count": 0,
            "received_count": 0
        }

def _detect_reply_or_followup_intent(message: str) -> bool:
    """Detect if the user wants to send a reply or follow-up email."""
    low = message.lower().strip()
    
    # Keywords that indicate reply/follow-up intent
    reply_keywords = [
        'reply', 'replied', 'responding', 'response',
        'follow up', 'followup', 'follow-up',
        'continue', 'continue the conversation',
        'answer', 'answering',
        'respond to', 'responding to'
    ]
    
    # Check for reply/follow-up keywords
    for keyword in reply_keywords:
        if keyword in low:
            return True
    
    # Check for context that suggests continuation
    if any(phrase in low for phrase in [
        'their email', 'their message', 'what they said',
        'previous email', 'last email', 'earlier email',
        'conversation', 'discussion', 'thread'
    ]):
        return True
    
    return False

def _get_web_context(company_name: Optional[str] = None, location: Optional[str] = None, industry: Optional[str] = None) -> Dict[str, Any]:
    """Get real-time web context for enhanced email generation.
    
    Returns:
        Dict containing:
        - news: Recent news about the company/industry
        - weather: Current weather for the location
        - company_info: Basic company information
        - market_data: Stock/industry trends if available
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        import json
        from datetime import datetime, timedelta
        
        context = {
            "news": [],
            "weather": None,
            "company_info": {},
            "market_data": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Get news if company name provided
        if company_name:
            try:
                # Use a simple news search (free)
                search_query = f"{company_name} news"
                news_url = f"https://www.google.com/search?q={search_query}&tbm=nws&tbs=qdr:d"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(news_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    news_items = soup.find_all('div', class_='g')[:3]  # Get top 3 news items
                    
                    for item in news_items:
                        if hasattr(item, 'find') and callable(getattr(item, 'find', None)):
                            title_elem = item.find('h3')  # type: ignore
                            if title_elem and hasattr(title_elem, 'get_text') and callable(getattr(title_elem, 'get_text', None)):
                                title = title_elem.get_text().strip()  # type: ignore
                                context["news"].append({
                                    "title": title,
                                    "source": "Google News",
                                    "relevance": "high" if company_name and company_name.lower() in title.lower() else "medium"
                                })
            except Exception as e:
                pass
        
        # Get weather if location provided
        if location:
            try:
                # Use free weather API (OpenWeatherMap free tier)
                weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid=demo&units=metric"
                # Note: In production, you'd use a real API key
                # For now, we'll simulate weather data
                context["weather"] = {
                    "location": location,
                    "temperature": "22°C",
                    "condition": "Sunny",
                    "humidity": "65%",
                    "note": "Good weather for meetings"
                }
            except Exception as e:
                pass
        
        # Get basic company information
        if company_name:
            try:
                # Simple company info extraction
                context["company_info"] = {
                    "name": company_name,
                    "industry": industry or "Technology",
                    "size": "Medium",
                    "note": f"Recent activity detected for {company_name}"
                }
            except Exception as e:
                pass
        
        return context
        
    except Exception as e:
        pass
        from datetime import datetime
        return {
            "news": [],
            "weather": None,
            "company_info": {},
            "market_data": {},
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

def _get_company_website_info(company_name: str) -> Dict[str, Any]:
    """Get basic information from company website."""
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        # Try to find company website
        search_query = f"{company_name} official website"
        search_url = f"https://www.google.com/search?q={search_query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for company website links
            links = soup.find_all('a', href=True)
            company_links = []
            
            for link in links:
                if hasattr(link, 'get') and callable(getattr(link, 'get', None)):
                    href = link.get('href', '')  # type: ignore
                    link_text = link.get_text() if hasattr(link, 'get_text') and callable(getattr(link, 'get_text', None)) else ''  # type: ignore
                    if any(domain in str(href) for domain in ['.com', '.org', '.net']) and company_name and company_name.lower() in (str(link_text) or '').lower():
                        company_links.append(href)
            
            if company_links:
                # Try to get basic info from the first company link
                company_url = company_links[0]
                if company_url.startswith('/'):
                    company_url = 'https://www.google.com' + company_url
                
                try:
                    company_response = requests.get(company_url, headers=headers, timeout=10)
                    if company_response.status_code == 200:
                        company_soup = BeautifulSoup(company_response.content, 'html.parser')
                        
                        # Extract basic company information
                        title = company_soup.find('title')
                        description = company_soup.find('meta', attrs={'name': 'description'})
                        
                        return {
                            "website": company_url,
                            "title": title.get_text().strip() if title and hasattr(title, 'get_text') and callable(getattr(title, 'get_text', None)) else company_name,  # type: ignore
                            "description": description.get('content', '') if description and hasattr(description, 'get') and callable(getattr(description, 'get', None)) else '',  # type: ignore
                            "status": "active"
                        }
                except Exception:
                    pass
        
        return {
            "website": None,
            "title": company_name,
            "description": f"Company information for {company_name}",
            "status": "unknown"
        }
        
    except Exception as e:
        return {
            "website": None,
            "title": company_name,
            "description": f"Company information for {company_name}",
            "status": "error",
            "error": str(e)
        }

def _get_industry_trends(industry: Optional[str] = None) -> Dict[str, Any]:
    """Get current industry trends and insights."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        if not industry:
            industry = "technology"
        
        # Search for industry trends
        search_query = f"{industry} trends 2024 latest news"
        search_url = f"https://www.google.com/search?q={search_query}&tbm=nws"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            trend_items = soup.find_all('div', class_='g')[:2]
            
            trends = []
            for item in trend_items:
                if hasattr(item, 'find') and callable(getattr(item, 'find', None)):
                    title_elem = item.find('h3')  # type: ignore
                    if title_elem and hasattr(title_elem, 'get_text') and callable(getattr(title_elem, 'get_text', None)):
                        title = title_elem.get_text().strip()  # type: ignore
                        trends.append({
                            "trend": title,
                            "industry": industry or "general",
                            "relevance": "high"
                        })
            
            return {
                "industry": industry,
                "trends": trends,
                "status": "success"
            }
        
        return {
            "industry": industry,
            "trends": [],
            "status": "no_data"
        }
        
    except Exception as e:
        return {
            "industry": industry or "general",
            "trends": [],
            "status": "error",
            "error": str(e)
        }

def _generate_context_aware_success_message(recipient_email: str, context: str, db: Session, owner: str) -> str:
    """Generate a context-aware success message for email sending."""
    try:
        # Try to get recipient name from contacts
        contact = db.query(Contact).filter(
            Contact.owner_email == owner,
            Contact.email == recipient_email
        ).first()
        
        recipient_name = contact.name if contact else recipient_email.split('@')[0].replace('.', ' ').title()
        
        # Determine context type
        if 'reply' in context.lower() or 'responding' in context.lower():
            context_type = "reply"
        elif 'follow' in context.lower():
            context_type = "follow-up"
        else:
            context_type = "email"
        
        # Generate appropriate success message
        if context_type == "reply":
            return f"The email has been successfully sent to {recipient_name}. This was a reply to their previous message."
        elif context_type == "follow-up":
            return f"The email has been successfully sent to {recipient_name}. This was a follow-up to your previous conversation."
        else:
            return f"The email has been successfully sent to {recipient_name}. {context}"
            
    except Exception:
        # Fallback to simple message
        return f"The email has been successfully sent to {recipient_email}."

async def _generate_email_content_async(topic: str, recipient_name: str, owner: str, db: Session, conversation_context: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """Async version of email generation with rate limiting and caching."""
    from app.core.gemini_service import wolf_assistants_service
    from app.core.gemini_fallback import fallback_system

    def create_email_prompt(context: Dict[str, Any]) -> str:
        # Get business context for more relevant email generation
        biz_context = _make_business_context(owner, db)
        
        # Get current date and time for the AI
        current_datetime = get_ist_now()
        current_date_str = current_datetime.strftime("%B %d, %Y")

        # Build conversation context for the prompt
        conversation_info = ""
        if conversation_context:
            if conversation_context.get('original_cold_email'):
                cold_email = conversation_context['original_cold_email']
                conversation_info += f"\nORIGINAL COLD EMAIL CONTEXT:\n"
                conversation_info += f"Subject: {cold_email.subject}\n"
                conversation_info += f"Body: {cold_email.body[:500]}...\n"

            if conversation_context.get('last_client_response'):
                client_response = conversation_context['last_client_response']
                conversation_info += f"\nLAST CLIENT RESPONSE:\n"
                conversation_info += f"Subject: {client_response.subject}\n"
                conversation_info += f"Body: {client_response.body[:500]}...\n"

            if conversation_context.get('conversation_summary'):
                conversation_info += f"\nCONVERSATION SUMMARY: {conversation_context['conversation_summary']}\n"

        # Get web context for enhanced intelligence
        web_context = ""
        try:
            # Extract company name from recipient email domain
            company_domain = recipient_name.split('@')[1] if '@' in recipient_name else recipient_name
            company_name = company_domain.split('.')[0].title()

            # Get web context
            web_data = _get_web_context(company_name=company_name)

            if web_data.get('news'):
                web_context += f"\nRECENT NEWS ABOUT {company_name.upper()}:\n"
                for news in web_data['news'][:2]:  # Top 2 news items
                    web_context += f"• {news['title']}\n"

            if web_data.get('weather'):
                weather = web_data['weather']
                web_context += f"\nCURRENT WEATHER: {weather['condition']} {weather['temperature']} in {weather['location']}\n"

            if web_data.get('company_info'):
                company_info = web_data['company_info']
                web_context += f"\nCOMPANY INFO: {company_info['name']} - {company_info['industry']} industry\n"

        except Exception as e:
            pass
            web_context = ""

        return (
            f"You are WolfAssistants, a co-founder and business partner who genuinely cares about our success. "
            f"Think like someone who's invested in the business and wants to help their team succeed. "
            f"Generate emails that are professional but also show genuine care for relationships and business growth.\n\n"
            f"Current Date: {current_date_str}\n"
            f"Topic: {topic}\n"
            f"Recipient: {recipient_name}\n"
            f"Business Context: {biz_context}\n"
            f"{conversation_info}\n"
            f"{web_context}\n"
            f"EMAIL REQUIREMENTS:\n"
            f"- Professional but warm and relationship-focused\n"
            f"- Show genuine interest in the recipient's success\n"
            f"- Clear value proposition that benefits both parties\n"
            f"- Conversational yet professional tone\n"
            f"- Concise but comprehensive coverage\n"
            f"- Strong call-to-action that drives results\n"
            f"- Reference previous conversations naturally\n"
            f"- If replying, acknowledge the previous exchange warmly\n"
            f"- Use current information to add relevance\n"
            f"- Reference weather or location context when appropriate\n"
            f"- Use 'we' and 'our' when talking about business matters\n"
            f"- Show you're invested in the relationship, not just the transaction\n\n"
            f"Return ONLY a JSON object with 'subject' and 'body' fields. "
            f"The email should reflect the thinking of a co-founder who genuinely cares about building lasting business relationships."
        )

    # Make rate-limited API request
    context = {
        'prompt_template': 'email_generation',
        'topic': topic,
        'recipient_name': recipient_name,
        'conversation_context': conversation_context
    }

    result = await wolf_assistants_service.make_request(
        user_email=owner,
        endpoint='email_generation',
        request_type='email_composition',
        prompt_func=create_email_prompt,
        context=context,
        use_cache=True,
        priority='high'  # Email generation is high priority
    )

    if result['success']:
        import json, re
        text = result['response']
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    subject = (data.get('subject') or f"Re: {topic}").strip()
                    body = (data.get('body') or f"Hi {recipient_name},\n\nI wanted to discuss {topic} with you.\n\nBest regards").strip()
                    return subject, body
            except json.JSONDecodeError:
                pass

    # Use fallback system
    fallback_response = await fallback_system.get_fallback_response('email_generation', 'email_composition', context)
    if fallback_response:
        import json, re
        match = re.search(r"\{[\s\S]*\}", fallback_response)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    subject = (data.get('subject') or f"Re: {topic}").strip()
                    body = (data.get('body') or f"Hi {recipient_name},\n\nI wanted to discuss {topic} with you.\n\nBest regards").strip()
                    return subject, body
            except json.JSONDecodeError:
                pass

    # Final fallback
    return f"Re: {topic}", f"Hi {recipient_name},\n\nI wanted to discuss {topic} with you.\n\nBest regards"

def _generate_email_content(topic: str, recipient_name: str, owner: str, db: Session, conversation_context: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """Synchronous wrapper for backward compatibility."""
    # For now, return fallback. The async version will be used in the main chat function.
    return f"Re: {topic}", f"Hi {recipient_name},\n\nI wanted to discuss {topic} with you.\n\nBest regards"

def _make_business_context(owner: str, db: Session) -> str:
    """Return a comprehensive business intelligence snapshot for strategic analysis."""
    try:
        # Core business metrics
        try:
            contacts_count = db.query(Contact).filter(Contact.owner_email == owner).count()
        except Exception:
            contacts_count = 0
            
        # Communication analytics (last 7 days)
        since = datetime.now() - timedelta(days=7)
        try:
            received_7d = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.received, Email.received_at.isnot(None)).count()
        except Exception:
            received_7d = 0
        try:
            sent_7d = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.sent, Email.sent_at.isnot(None)).count()
        except Exception:
            sent_7d = 0
            
        # Strategic communication analysis
        last_email_line = ""
        try:
            last_email = (
                db.query(Email)
                .filter(Email.owner_email == owner)
                .order_by((Email.received_at.isnot(None)).desc(), Email.received_at.desc(), (Email.sent_at.isnot(None)).desc(), Email.sent_at.desc())
                .first()
            )
            if last_email is not None:
                who = str(last_email.from_address or last_email.to_address or "")
                subj = str(last_email.subject or "No Subject")
                last_email_line = f"Latest strategic communication: {who} - {subj}"
        except Exception:
            pass
            
        # Executive calendar and strategic meetings
        next_meeting_line = ""
        try:
            upcoming = (
                db.query(Meeting)
                .filter(Meeting.owner_email == owner, Meeting.start_time > datetime.now())
                .order_by(Meeting.start_time.asc())
                .first()
            )
            if upcoming is not None:
                t = upcoming.start_time.strftime('%d %b %Y %I:%M %p') if hasattr(upcoming.start_time, 'strftime') else str(upcoming.start_time)
                next_meeting_line = f"Next strategic meeting: {str(upcoming.title)} at {t}"
        except Exception:
            pass
            
        # Business intelligence summary
        pieces = [
            f"BUSINESS INTELLIGENCE SUMMARY:",
            f"• Network: {contacts_count} strategic contacts",
            f"• Communication Volume (7d): {received_7d} inbound, {sent_7d} outbound",
            f"• Communication Efficiency: {sent_7d/(received_7d+1):.1f} response ratio" if received_7d > 0 else f"• Communication Efficiency: {sent_7d} proactive communications",
        ]
        
        if last_email_line:
            pieces.append(f"• {last_email_line}")
        if next_meeting_line:
            pieces.append(f"• {next_meeting_line}")
            
        # Add strategic context
        pieces.extend([
            f"• Current Date: {datetime.now().strftime('%B %d, %Y')}",
            f"• Business Status: Active operations with {contacts_count} stakeholder relationships",
            f"• Strategic Focus: Optimizing communication efficiency and stakeholder engagement"
        ])
        
        return "\n".join(pieces)
    except Exception:
        return f"BUSINESS CONTEXT: Active business operations on {datetime.now().strftime('%B %d, %Y')}"

def _detect_query_complexity(message: str) -> str:
    """Detect query complexity to determine appropriate response tier."""
    message_lower = message.lower().strip()
    
    # Basic queries (simple facts, dates, basic info)
    basic_patterns = [
        r"what.*date", r"what.*time", r"when.*today", r"current.*date",
        r"what.*day", r"how.*are.*you", r"hello", r"hi", r"good.*morning",
        r"good.*afternoon", r"good.*evening", r"thank.*you", r"thanks"
    ]
    
    # Operational queries (processes, how-to, specific tasks)
    operational_patterns = [
        r"how.*to", r"how.*can.*i", r"how.*do.*i", r"what.*should.*i",
        r"help.*me.*with", r"assist.*with", r"guide.*me", r"steps.*to",
        r"process.*for", r"procedure.*for", r"workflow.*for"
    ]
    
    # Strategic queries (analysis, planning, complex business decisions)
    strategic_patterns = [
        r"strategy", r"strategic", r"analysis", r"optimize", r"improve",
        r"business.*plan", r"market.*analysis", r"competitive", r"industry.*trends",
        r"supply.*chain", r"operations", r"financial.*model", r"investment",
        r"risk.*assessment", r"stakeholder", r"partnership", r"expansion"
    ]
    
    import re
    
    # Check for strategic patterns first (most specific)
    for pattern in strategic_patterns:
        if re.search(pattern, message_lower):
            return "strategic"
    
    # Check for operational patterns
    for pattern in operational_patterns:
        if re.search(pattern, message_lower):
            return "operational"
    
    # Check for basic patterns
    for pattern in basic_patterns:
        if re.search(pattern, message_lower):
            return "basic"
    
    # Default to operational for unknown queries
    return "operational"

async def _llm_intent_and_slots_async(message: str, history: List[Dict[str, str]] | None, owner: str) -> Dict[str, Any]:
    """Async version of intent parsing with rate limiting and caching."""
    from app.core.gemini_service import wolf_assistants_service
    from app.core.gemini_fallback import fallback_system

    # Fast path: if rule-based parser confidently detects an actionable intent,
    # skip LLM to reduce latency. Missing fields will be confirmed via UI.
    rb = _parse_intent_rule_based(message)
    if rb.get('intent') in {"send_email", "schedule_meeting", "check_inbox", "lookup_contact"}:
        return rb

    def create_intent_prompt(context: Dict[str, Any]) -> str:
        history_text = "\n".join([f"{h.get('role','user')}: {h.get('text','')}" for h in (history or [])][-5:])
        return (
            "You are WolfAssistants, an AI assistant. Classify the user's intent and extract relevant information. "
            "Return STRICT JSON only with: "
            "intent(one of send_email, schedule_meeting, check_inbox, chat), "
            "to, subject, body, title, start_iso, end_iso, attendees. Use empty string if unknown.\n\n"
            "INTENT CLASSIFICATION RULES:\n"
            "- If user wants to send an email: intent='send_email'\n"
            "- If user wants to schedule/arrange a meeting: intent='schedule_meeting'\n"
            "- If user wants to check inbox: intent='check_inbox'\n"
            "- If user wants to look up contact info: intent='lookup_contact'\n"
            "- Otherwise: intent='chat'\n\n"
            "EXTRACTION RULES:\n"
            "- For meetings: extract title, start_iso, end_iso, attendees\n"
            "- For emails: extract to, subject, body\n"
            "- For contacts: extract query\n\n"
            f"History:\n{history_text}\n\n"
            f"Message: {message}\n"
            "JSON:"
        )

    # Make rate-limited API request
    context = {
        'prompt_template': 'intent_classification',
        'message': message,
        'history': history
    }

    result = await wolf_assistants_service.make_request(
        user_email=owner,
        endpoint='intent_parsing',
        request_type='intent_classification',
        prompt_func=create_intent_prompt,
        context=context,
        use_cache=True,
        priority='normal'
    )

    if result['success']:
        import json, re
        text = result['response']
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    intent = (data.get('intent') or 'chat').strip()
                    # Normalize intent
                    if intent not in {'send_email', 'schedule_meeting', 'check_inbox', 'chat'}:
                        intent = 'chat'
                    # Ensure fields exist
                    return {
                        'intent': intent,
                        'to': (data.get('to') or '').strip(),
                        'subject': (data.get('subject') or '').strip(),
                        'body': (data.get('body') or '').strip(),
                        'title': (data.get('title') or '').strip(),
                        'start_iso': (data.get('start_iso') or '').strip(),
                        'end_iso': (data.get('end_iso') or '').strip(),
                        'attendees': (data.get('attendees') or '').strip(),
                    }
            except json.JSONDecodeError:
                pass

    # Fallback to rule-based parsing if LLM failed or JSON parsing failed
    return _parse_intent_rule_based(message)

def _llm_intent_and_slots(message: str, history: List[Dict[str, str]] | None) -> Dict[str, Any]:
    """Synchronous wrapper for backward compatibility."""
    # For now, return rule-based parsing. The async version will be used in the main chat function.
    rb = _parse_intent_rule_based(message)
    if rb.get('intent') in {"send_email", "schedule_meeting", "check_inbox", "lookup_contact"}:
        return rb
    return rb  # Default to rule-based for now

@router.post("/chat")
async def simon_chat(request: Request, payload: Dict[str, Any], db: Session = Depends(get_db)):
    owner = _get_owner_from_request(request)
    message = (payload.get('message') or '').strip()
    context = payload.get('context') or {}
    history = payload.get('history') or []
    session_id = payload.get('session_id')
    contact_name = payload.get('contact_name')
    contact_email = payload.get('contact_email')
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    # Ensure an active chat session exists and persist the user message
    is_new_session = False
    session: ChatSession | None = None
    if session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.owner_email == owner
        ).first()
    if not session:
        # Only deactivate other sessions if this is about a specific contact
        # This allows users to have multiple active conversations with different contacts
        if contact_email:
            try:
                db.query(ChatSession).filter(
                    ChatSession.owner_email == owner,
                    ChatSession.contact_email == contact_email,
                    ChatSession.is_active == True
                ).update({"is_active": False})
            except Exception as e:
                pass
        else:
            # For general conversations, deactivate all other sessions
            try:
                db.query(ChatSession).filter(ChatSession.owner_email == owner).update({"is_active": False})
            except Exception as e:
                pass
        
        # Create meaningful session title based on first message
        title = await _generate_session_title(message, contact_name, owner)
        
        try:
            session = ChatSession(
                owner_email=owner,
                title=title,
                contact_name=contact_name,
                contact_email=contact_email,
                is_active=True,
                last_message_at=datetime.now(),
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            is_new_session = True
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to create chat session")
    
    # Load conversation history for context
    conversation_history = []
    if session and not is_new_session:
        try:
            # Get recent messages from this session (last 10 messages for context)
            recent_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.created_at.desc()).limit(10).all()
            
            # Convert to history format (oldest first)
            for msg in reversed(recent_messages):
                conversation_history.append({
                    'role': msg.role,
                    'text': msg.content,
                    'timestamp': msg.created_at.isoformat() if msg.created_at is not None else None
                })
        except Exception as e:
            # If history loading fails, continue without it
            conversation_history = []

    # Save user's message
    title_updated = False
    try:
        user_msg = ChatMessage(
            session_id=session.id,  # type: ignore[arg-type]
            role='user',
            content=message,
            intent=None,
            status='ok',
        )
        db.add(user_msg)
        session.last_message_at = datetime.now()  # type: ignore
        
        # If this is the first message in the session and title is still default, update it
        # Check if this is the first user message (count BEFORE adding this one)
        message_count_before = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == 'user'
        ).count()
        
        # Update title if:
        # 1. This is the first user message (message_count_before == 0)
        # 2. Title is generic (starts with "New Chat" or is just "New Chat")
        # 3. Not a new session (session was created via /sessions endpoint)
        should_update_title = (
            message_count_before == 0 and 
            session.title and 
            (session.title.startswith("New Chat") or session.title == "New Chat")
        )
        
        if should_update_title:
            # Generate a better title from the first message
            old_title = session.title
            try:
                new_title = await _generate_session_title(message, session.contact_name, owner)
                if new_title and new_title != old_title and len(new_title.strip()) > 0:
                    session.title = new_title
                    title_updated = True
                    try:
                        write_debug_log("simon.py:save_user_message", "Title updated successfully", {
                            "old_title": old_title,
                            "new_title": new_title,
                            "message_preview": message[:50]
                        }, "I")
                    except:
                        pass
            except Exception as e:
                # If title generation fails, keep the existing title
                try:
                    write_debug_log("simon.py:save_user_message", "Title generation failed", {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "current_title": session.title
                    }, "W")
                except:
                    pass
        
        db.commit()
        # Refresh session to get updated title
        if title_updated:
            db.refresh(session)
    except Exception as e:
        # Log the error but don't fail the request
        try:
            write_debug_log("simon.py:save_user_message", "Failed to save user message", {"error": str(e)}, "E")
        except:
            pass

    def persist_and_respond(text: str, intent: str | None, status: str, metadata: Optional[Dict[str, Any]] = None):
        # Convert metadata to JSON string if it's a dict
        metadata_json = None
        if metadata is not None:
            import json
            try:
                metadata_json = json.dumps(metadata, default=str)
            except Exception:
                metadata_json = str(metadata)
        
        wolfy_msg = ChatMessage(
            session_id=session.id,  # type: ignore[arg-type]
            role='wolfy',
            content=text,
            intent=intent,
            status=status,
            message_metadata=metadata_json
        )
        db.add(wolfy_msg)
        session.last_message_at = datetime.now()  # type: ignore
        db.commit()
        db.refresh(wolfy_msg)
        # Refresh session to get any updated title
        db.refresh(session)
        # #region agent log
        try:
            from app.core.debug_logger import write_debug_log
            write_debug_log("simon.py:1428", "Final response being returned", {
                "response_text": text,
                "intent": intent,
                "status": status,
                "response_length": len(text) if text else 0,
                "session_title": session.title
            }, "E")
        except: pass
        # #endregion
        return {
            "session_id": session.id,
            "session_title": session.title,
            "is_new_session": is_new_session,
            "message": ChatMessageResponse.from_orm(wolfy_msg)
        }

    # Use conversation history for better context
    effective_history = conversation_history if conversation_history else history

    # Check for simple greeting first (including greetings with names)
    greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
    message_lower = message.lower().strip()
    
    # Check if message starts with a greeting word (more flexible matching)
    is_greeting = any(message_lower.startswith(word) for word in greeting_words) or \
                  any(word in message_lower.split()[:2] for word in greeting_words)
    
    # Debug logging
    print(f"Debug - Message: '{message}', Lower: '{message_lower}', Is greeting: {is_greeting}")
    
    if is_greeting:
        # Get user's full name from profile page
        try:
            print(f"Debug - Looking up user with email: {owner}")
            user = db.query(User).filter(User.email == owner).first()
            print(f"Debug - User found: {user is not None}")
            if user:
                print(f"Debug - User full_name: '{user.full_name}', username: '{user.username}'")
                # Use full_name from profile if available
                if user.full_name and user.full_name.strip():
                    greeting = f"Hi {user.full_name.strip()}"
                    print(f"Debug - Using full_name: '{greeting}'")
                # Fallback to username if available
                elif user.username and user.username.strip():
                    greeting = f"Hi {user.username.strip()}"
                    print(f"Debug - Using username: '{greeting}'")
                # Final fallback to email name
                else:
                    greeting = f"Hi {owner.split('@')[0].replace('.', ' ').title()}"
                    print(f"Debug - Using email fallback: '{greeting}'")
            else:
                greeting = f"Hi {owner.split('@')[0].replace('.', ' ').title()}"
                print(f"Debug - No user found, using email fallback: '{greeting}'")
        except Exception as e:
            # Log the exception for debugging
            print(f"Exception in greeting logic: {e}")
            greeting = f"Hi {owner.split('@')[0].replace('.', ' ').title()}"
        
        print(f"Debug - Final greeting: '{greeting}'")
        return persist_and_respond(greeting, 'greeting', 'ok')

    # Removed early task assignment check - let intent parsing determine the flow
    # This allows normal conversation to proceed when intent is 'chat'

    # Use LLM-assisted intent parsing with rule-based fallback
    try:
        # #region agent log
        write_debug_log("simon.py:1513", "Starting intent parsing", {
            "message": message,
            "history_length": len(effective_history),
            "using_llm": True
        }, "B")
        # #endregion
        intent_info = await _llm_intent_and_slots_async(message, effective_history, owner)
        intent = intent_info.get('intent')
        # #region agent log
        write_debug_log("simon.py:1516", "Intent parsed via LLM", {
            "intent": intent,
            "intent_info": intent_info
        }, "B")
        # #endregion
    except Exception as e:
        # Fallback to rule-based parsing if LLM fails
        # #region agent log
        write_debug_log("simon.py:1520", "LLM intent parsing failed, using rule-based", {
            "error": str(e),
            "message": message
        }, "C")
        # #endregion
        intent_info = _parse_intent_rule_based(message)
        # #region agent log
        write_debug_log("simon.py:1522", "Intent parsed via rule-based", {
            "intent": intent_info.get('intent'),
            "intent_info": intent_info
        }, "B")
        # #endregion
    intent = intent_info.get('intent')
    if intent == 'lookup_contact':
        query = (intent_info.get('query') or context.get('query') or message).strip()
        result = _lookup_contact_email(owner, query, db)
        if result.get('status') == 'ok' and result.get('best'):
            b = result['best']
            return persist_and_respond(f"{b['name']}: {b['email']}", intent, 'done')
        if result.get('status') == 'ok' and result.get('matches'):
            opts = ", ".join([f"{m['name']} <{m['email']}>" for m in result['matches']])
            return persist_and_respond(f"I found multiple matches: {opts}.", intent, 'ok')
        
        # Direct response without extra options
        return persist_and_respond(
            f"I couldn't find that contact in your database. Please provide their email address or add them to your contacts first.", intent, 'ok'
        )

    if intent == 'send_email':
        to_addr = (intent_info.get('to') or context.get('to') or '').strip()
        subj = (context.get('subject') or intent_info.get('subject') or '').strip()
        body = (context.get('body') or intent_info.get('body') or '').strip()
        # Optional scheduling: parse time hints like 'today at 14:55'
        schedule_dt = _parse_email_send_time_ist(message)
        
        # If to_addr is a name (not an email), try to look it up
        if to_addr and '@' not in to_addr:
            contact_result = _lookup_contact_email(owner, to_addr, db)
            if contact_result.get('status') == 'ok' and contact_result.get('best'):
                to_addr = contact_result['best']['email']
            elif contact_result.get('status') == 'ok' and contact_result.get('matches'):
                # Multiple matches - ask user to clarify
                opts = ", ".join([f"{m['name']} <{m['email']}>" for m in contact_result['matches']])
                return persist_and_respond(f"I found multiple contacts named '{to_addr}': {opts}. Which one did you mean?", intent, 'ok')
            else:
                # Direct response for email generation
                return persist_and_respond(
                    f"I couldn't find a contact named '{to_addr}' in your database. Please provide their email address.", intent, 'ok'
                )
        
        # If we have a topic but no subject/body, generate them using Gemini
        if to_addr and not subj and not body:
            # Get topic from intent_info or extract from message
            topic = intent_info.get('topic') or _extract_email_topic(message)
            if topic:
                recipient_name = to_addr.split('@')[0].replace('.', ' ').title()
                
                # Check if this is a reply or follow-up and get conversation context
                conversation_context = None
                if _detect_reply_or_followup_intent(message):
                    conversation_context = _read_email_conversation_context(owner, to_addr, db)
                
                subj, body = _generate_email_content(topic, recipient_name, owner, db, conversation_context)
            else:
                # No topic provided - ask for clarification
                return persist_and_respond(
                    f"I'd be happy to send an email to {to_addr}. What would you like the email to be about? Please provide:\n\n"
                    f"• **Subject line** - What should the email subject be?\n"
                    f"• **Content** - What do you want to discuss or communicate?\n"
                    f"• **Purpose** - Is this a follow-up, introduction, update, or something else?\n\n"
                    f"Example: 'Send email to john@example.com about project update' or 'Email sarah regarding the meeting tomorrow'",
                    intent, 'confirm', {"to": to_addr, "subject": "", "body": ""}
                )
        
        missing = []
        if not to_addr:
            missing.append('to')
        if not subj:
            missing.append('subject')
        if not body:
            missing.append('body')
        if missing:
            return persist_and_respond(f"Sure. I can send that. Please confirm {'/'.join(missing)}.", intent, 'confirm', {"to": to_addr, "subject": subj, "body": body})
        if schedule_dt:
            # Store as scheduled in Supabase and do not send immediately
            try:
                from app.models.email import Email, EmailStatus
                from app.core.database import SessionLocal
                
                # Use the main Supabase database session
                email_db = SessionLocal()
                try:
                    scheduled_email = Email(
                        subject=subj,
                        body=body,
                        to_address=to_addr,
                        from_address=owner,
                        status=EmailStatus.scheduled,
                        scheduled_for=schedule_dt,
                        owner_email=owner,
                        is_read=True,
                        is_starred=False
                    )
                    email_db.add(scheduled_email)
                    email_db.commit()
                    email_db.refresh(scheduled_email)
                    
                finally:
                    email_db.close()
                    
            except Exception:
                # If scheduling persistence fails, fall back to sending immediately
                resp = _send_email({"to": to_addr, "subject": subj, "content": body}, db, owner)
                success_msg = _generate_context_aware_success_message(to_addr, "scheduled email", db, owner)
                return persist_and_respond(success_msg, intent, 'done', resp if isinstance(resp, dict) else None)
            return persist_and_respond(
                f"Okay, I will send this email to {to_addr} at {schedule_dt.strftime('%Y-%m-%d %H:%M')} IST.",
                intent,
                'scheduled',
                {"to": to_addr, "subject": subj, "scheduled_for": schedule_dt.isoformat()}
            )
        else:
            resp = _send_email({"to": to_addr, "subject": subj, "content": body}, db, owner)
            # Determine context for success message
            context_type = "email"
            if _detect_reply_or_followup_intent(message):
                context_type = "reply" if 'reply' in message.lower() else "follow-up"
            
            success_msg = _generate_context_aware_success_message(to_addr, context_type, db, owner)
            return persist_and_respond(success_msg, intent, 'done', resp if isinstance(resp, dict) else None)

    if intent == 'schedule_meeting':
        # Check if this is a follow-up response to a previous meeting request
        is_follow_up = context.get('is_follow_up', False)
        
        # Extract title from message if not provided in context
        extracted_title = _extract_meeting_title(message)
        title = (context.get('title') or extracted_title or 'Call with Client').strip()
        start_iso = (context.get('start_iso') or '').strip()
        end_iso = (context.get('end_iso') or '').strip()
        attendees = (context.get('attendees') or '').strip()

        # Auto extract attendees from message or contacts when missing
        if not attendees:
            # Try to extract attendee names from the message
            import re
            # Look for "with [Name/Email]" pattern - handle multiple attendees
            with_match = re.search(r'with\s+([A-Za-z0-9@._\s]+?)(?:\s+(?:tomorrow|today|at|from|to|regarding|about)|$)', message, re.IGNORECASE)
            if with_match:
                attendee_text = with_match.group(1).strip()
                # Handle multiple attendees separated by "and" or ","
                if ' and ' in attendee_text:
                    attendee_names = [name.strip() for name in attendee_text.split(' and ')]
                elif ',' in attendee_text:
                    attendee_names = [name.strip() for name in attendee_text.split(',')]
                else:
                    attendee_names = [attendee_text]
                
                # Try to find emails for each contact
                attendee_emails = []
                for name in attendee_names:
                    # Check if it's already an email address
                    if '@' in name and '.' in name:
                        attendee_emails.append(name)
                    else:
                        contact_result = _lookup_contact_email(owner, name, db)
                        if contact_result.get('status') == 'ok' and contact_result.get('best'):
                            attendee_emails.append(contact_result['best']['email'])
                        else:
                            # If no contact found, use the name as is
                            attendee_emails.append(name)
                
                attendees = ",".join(attendee_emails)
            else:
                # Fallback to original logic
                guessed = _guess_attendees(message, owner, db)
                attendees = ",".join(guessed) if guessed else attendees

        # Opportunistic ISO extraction from raw message when missing
        if not start_iso or not end_iso:
            # 1) Try natural phrases like 'tomorrow from 10:30 AM to 12:30 PM'
            s_iso, e_iso = _parse_natural_times(message)
            if s_iso and e_iso:
                start_iso = start_iso or s_iso
                end_iso = end_iso or e_iso
            else:
                # 2) Try ISO timestamps embedded
                import re
                iso_matches = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?", message)
                if iso_matches:
                    full = [m.group(0) for m in re.finditer(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?", message)]
                    if full:
                        start_iso = start_iso or full[0]
                        if len(full) > 1:
                            end_iso = end_iso or full[1]
                        else:
                            try:
                                start_dt_tmp = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                                end_iso = (start_dt_tmp + timedelta(minutes=30)).isoformat()
                            except Exception:
                                pass
        
        # Check for missing critical information and ask for clarification
        missing_fields = []
        if not start_iso or not end_iso:
            missing_fields.append("date and time")
        if not attendees:
            missing_fields.append("attendees")
        if not title or title == 'Call with Client':
            missing_fields.append("meeting title")
        
        # If we have attendees but missing time and title, provide helpful suggestions
        if attendees and not start_iso and not title:
            clarification_msg = f"I'd be happy to schedule a meeting with {attendees}. I need a few more details:\n\n"
            clarification_msg += f"• **When** would you like to schedule it? (e.g., 'tomorrow at 2pm', 'next Monday 10:30 AM to 11:30 AM')\n"
            clarification_msg += f"• **What** should the meeting be about? (e.g., 'project discussion', 'team sync', 'client review')\n\n"
            clarification_msg += f"Or you can provide all details at once like: 'Schedule a meeting with {attendees} tomorrow at 2 PM to discuss the project'"
            
            return persist_and_respond(clarification_msg, intent, 'confirm', {
                "title": title,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "attendees": attendees,
                "is_follow_up": True
            })
        
        # If this is a follow-up response and we still have missing fields, 
        # don't create an incomplete meeting record
        if missing_fields:
            clarification_msg = f"I'd be happy to schedule a meeting for you. I need some additional details:\n\n"
            if "date and time" in missing_fields:
                clarification_msg += f"• **When** would you like to schedule it? (e.g., 'tomorrow at 2pm', 'next Monday 10:30 AM to 11:30 AM')\n"
            if "attendees" in missing_fields:
                clarification_msg += f"• **Who** should attend? (email addresses or names from your contacts)\n"
            if "meeting title" in missing_fields:
                clarification_msg += f"• **What** should the meeting be about? (title/agenda)\n"
            clarification_msg += f"\nPlease provide these details and I'll schedule the meeting for you."
            
            # Don't create incomplete meeting records - just ask for clarification
            return persist_and_respond(clarification_msg, intent, 'confirm', {
                "title": title,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "attendees": attendees,
                "is_follow_up": True
            })
        
        # If we have all required fields, proceed directly without confirmation
        if start_iso and end_iso and attendees and title:
            # Parse datetime objects for conflict detection
            try:
                start_dt_parsed = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                end_dt_parsed = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
            except Exception:
                return persist_and_respond("Could not parse meeting time. Please try a clearer time range (e.g., 'tomorrow 10:30 AM to 12:30 PM').", intent, 'error')
            
            start_dt_val = start_dt_parsed
            end_dt_val = end_dt_parsed

            # Conflict detection with existing meetings for owner
            try:
                overlaps = db.query(Meeting).filter(
                    Meeting.owner_email == owner,
                    Meeting.start_time < end_dt_val,
                    Meeting.end_time > start_dt_val,
                ).all()
                
                if overlaps:
                    # Found conflicts - notify user and suggest alternatives
                    conflict_details = []
                    for meeting in overlaps:
                        conflict_start = meeting.start_time.strftime("%B %d, %Y at %I:%M %p")
                        conflict_end = meeting.end_time.strftime("%I:%M %p")
                        conflict_title = meeting.title or "Untitled Meeting"
                        conflict_details.append(f"• {conflict_title} on {conflict_start} - {conflict_end}")
                    
                    # Generate alternative time suggestions
                    alternative_times = _generate_alternative_times(start_dt_parsed, end_dt_parsed, owner, db)
                    
                    conflict_msg = f"I found a scheduling conflict for your requested time. You already have the following meeting(s) scheduled:\n\n"
                    conflict_msg += "\n".join(conflict_details)
                    conflict_msg += f"\n\nHere are some alternative time options:\n\n"
                    
                    for i, alt_time in enumerate(alternative_times[:3], 1):  # Show top 3 alternatives
                        alt_start = alt_time['start'].strftime("%B %d, %Y at %I:%M %p")
                        alt_end = alt_time['end'].strftime("%I:%M %p")
                        conflict_msg += f"{i}. {alt_start} - {alt_end}\n"
                    
                    conflict_msg += f"\nPlease let me know which alternative time works for you, or suggest a different time."
                    
                    return persist_and_respond(conflict_msg, intent, 'confirm', {
                        "title": title,
                        "start_iso": start_iso,
                        "end_iso": end_iso,
                        "attendees": attendees,
                        "conflict_detected": True
                    })
                    
            except Exception as e:
                # Log error but continue with meeting creation
                print(f"Conflict detection error: {e}")
                pass
            
            # Skip confirmation and create meeting directly
            attendees_list = [x.strip() for x in attendees.split(',') if x.strip()]
            from app.schemas.meeting import MeetingCreate
            meeting_payload = MeetingCreate(
                title=title,
                description="Scheduled via WolfAssistants",
                start_time=start_dt_val,
                end_time=end_dt_val,
                location="Online",
                attendees=attendees_list,
                type="video",
                status="scheduled",
            )
            try:
                result = create_meeting(meeting_payload, request, db)
                return persist_and_respond(f"Successfully created meeting: {title} ({start_iso} to {end_iso}) with {', '.join(attendees_list)}.", intent, 'done', result if isinstance(result, dict) else None)
            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        # If we reach here, we need confirmation for missing fields
        return persist_and_respond("I need more details to schedule the meeting. Please provide the missing information.", intent, 'confirm')

    if intent == 'check_inbox':
        from app.api.v1.emails import fast_imap_check
        try:
            result = fast_imap_check(request, db)
            count = int(result.get('imported_count') or 0) if isinstance(result, dict) else 0
            return persist_and_respond(f"Inbox checked. Imported {count} new email(s).", intent, 'done', result if isinstance(result, dict) else None)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    if intent == 'web_research':
        query = intent_info.get('query', message)
        try:
            # Extract potential company name or topic from query
            company_name = None
            industry = None
            
            # Try to extract company name from query
            if any(word in query.lower() for word in ['company', 'corp', 'inc', 'ltd', 'llc']):
                # Look for company names in the query
                import re
                company_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', query)
                if company_match:
                    company_name = company_match.group(1)
            
            # Get web context
            web_data = _get_web_context(company_name=company_name or "general", industry=industry or "technology")
            
            # Format response
            response_parts = []
            
            if web_data.get('news'):
                response_parts.append("📰 **Recent News:**")
                for news in web_data['news'][:3]:
                    response_parts.append(f"• {news['title']}")
            
            if web_data.get('company_info'):
                company_info = web_data['company_info']
                response_parts.append(f"\n🏢 **Company Info:** {company_info['name']} - {company_info['industry']} industry")
            
            if web_data.get('weather'):
                weather = web_data['weather']
                response_parts.append(f"\n🌤️ **Weather:** {weather['condition']} {weather['temperature']} in {weather['location']}")
            
            if not response_parts:
                response_parts.append("I couldn't find specific information about that topic. Please try a more specific query.")
            
            return persist_and_respond("\n".join(response_parts), intent, 'done')
            
        except Exception as e:
            return persist_and_respond(f"Research failed: {str(e)}", intent, 'error')

    try:
        # #region agent log
        # Check if any API keys exist using the same method as gemini_service
        from app.core.gemini_key_manager import key_manager
        has_any_key = len(key_manager.keys) > 0 or bool(settings.GEMINI_API_KEY)
        write_debug_log("simon.py:1886", "Reached chat intent handler", {
            "intent": intent,
            "message": message,
            "has_api_key": has_any_key,
            "keys_count": len(key_manager.keys),
            "settings_key_exists": bool(settings.GEMINI_API_KEY),
            "history_length": len(effective_history)
        }, "E")
        # #endregion
        # Check if any API keys exist (same method as gemini_service)
        api_key = settings.GEMINI_API_KEY or (key_manager.keys[0] if (key_manager.keys and len(key_manager.keys) > 0) else None)
        if not api_key:
            # #region agent log
            write_debug_log("simon.py:1888", "No API key - using fallback responses", {
                "message": message
            }, "C")
            # #endregion
            # Enhanced fallback response with conversation memory
            current_datetime = get_ist_now()
            current_date_str = current_datetime.strftime("%B %d, %Y")
            current_time_str = current_datetime.strftime("%I:%M %p")
            
            # Handle common queries without API
            message_lower = message.lower().strip()
            
            # Check conversation history for context
            has_history = len(effective_history) > 0
            last_user_message = None
            if has_history:
                # Find the last user message
                for msg in reversed(effective_history):
                    if msg.get('role') == 'user':
                        last_user_message = msg.get('text', '')
                        break
            
            # Handle conversation context
            if message_lower in ['?', 'what', 'huh', 'what?'] and last_user_message:
                # User is asking for clarification about previous message
                return persist_and_respond(
                    f"I see you're asking about your previous question: '{last_user_message}'\n\n"
                    f"Let me help you with that. Current time: {current_time_str} on {current_date_str}\n\n"
                    "Could you rephrase your question or let me know what specific information you need?", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['stop', 'stop it', 'enough', 'quit']):
                return persist_and_respond(
                    "I understand you'd like me to stop. I'm here to help when you need me. "
                    f"Current time: {current_time_str} on {current_date_str}. "
                    "Just let me know if you need assistance with anything!", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['time', 'what time', 'current time']):
                return persist_and_respond(
                    f"The current time is {current_time_str} IST.", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['date', 'today', 'what date', 'current date']):
                return persist_and_respond(
                    f"Today's date is {current_date_str}.", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
                return persist_and_respond(
                    f"Hello! I'm WolfAssistants, your AI assistant. How can I help you today?", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['help', 'what can you do', 'capabilities']):
                return persist_and_respond(
                    "I'm WolfAssistants, your AI business assistant! I can help you with:\n"
                    "• Sending emails\n"
                    "• Scheduling meetings\n"
                    "• Checking your inbox\n"
                    "• Looking up contacts\n"
                    "• General business questions\n\n"
                    f"Current time: {current_time_str} on {current_date_str}\n"
                    "What would you like to do?", 'chat', 'ok'
                )
            elif has_history and any(word in message_lower for word in ['previous', 'before', 'earlier', 'what i asked']):
                # User is referring to previous conversation
                return persist_and_respond(
                    f"I remember our conversation. You previously asked: '{last_user_message}'\n\n"
                    f"Current time: {current_time_str} on {current_date_str}\n\n"
                    "How can I help you with that or is there something else you'd like to know?", 'chat', 'ok'
                )
            else:
                # For other queries, provide a helpful response with context awareness
                context_note = ""
                if has_history:
                    context_note = f"I see we've been chatting. Your last question was about: '{last_user_message}'\n\n"
                
                return persist_and_respond(
                    f"{context_note}I understand you're asking about: '{message}'\n\n"
                    f"Current time: {current_time_str} on {current_date_str}\n\n"
                    "I'm WolfAssistants, your AI assistant. I can help with emails, meetings, inbox management, and more. "
                    "Could you be more specific about what you'd like me to help you with?", 'chat', 'ok'
                )
        # #region agent log
        write_debug_log("simon.py:1962", "Calling Gemini LLM for chat", {
            "message": message,
            "history_length": len(effective_history),
            "has_api_key": bool(api_key)
        }, "C")
        # #endregion
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        history_text = "\n".join([f"{h.get('role','user')}: {h.get('text','')}" for h in (effective_history or [])][-5:])
        biz = _make_business_context(owner, db)
        # Get current date and time for the AI
        current_datetime = get_ist_now()
        current_date_str = current_datetime.strftime("%B %d, %Y")
        current_time_str = current_datetime.strftime("%I:%M %p")
        
        # Detect query complexity and create appropriate prompt
        complexity = _detect_query_complexity(message)
        # #region agent log
        write_debug_log("simon.py:1974", "Query complexity detected", {
            "complexity": complexity,
            "history_text_length": len(history_text)
        }, "D")
        # #endregion
        
        if complexity == "basic":
            prompt = (
                "You are WolfAssistants, a trusted co-founder and business partner who genuinely cares about our success. "
                "Think like someone who's invested in the business and wants to help their friend/colleague succeed. "
                "Be conversational, supportive, and action-oriented. You're not just an AI - you're a business partner who gets things done.\n\n"
                "COMMUNICATION STYLE:\n"
                "- Talk like a friend who's also a business partner\n"
                "- Be direct and helpful, not robotic\n"
                "- Show genuine interest in the user's success\n"
                "- Use 'we' and 'our' when talking about business matters\n"
                "- Be encouraging and supportive\n"
                "- Take action, don't just explain\n"
                "- Keep the tone professional, warm, and optimistic\n"
                "- Start with a natural greeting that references the user if you know their name (otherwise use 'Hey there')\n"
                "- Keep sentences concise and conversational; avoid sounding like a memo\n"
                "- Close with either a suggested next step or an open question to keep the collaboration moving\n\n"
                f"Current Date and Time: {current_date_str} at {current_time_str} IST\n"
                f"User: {message}\n\n"
                "Respond naturally and helpfully. If it's a simple question, give a direct answer. If it's a task, do it or explain how to do it. Be conversational, professional, friendly, and supportive."
            )
        elif complexity == "operational":
            prompt = (
                "You are WolfAssistants, a co-founder and operational partner who's deeply invested in our business success. "
                "You think strategically but act practically. You're the kind of partner who rolls up their sleeves and gets things done. "
                "You genuinely care about our growth and want to help solve real business challenges.\n\n"
                "MINDSET:\n"
                "- Co-founder: You're invested in the business's success\n"
                "- Friend: You care about the person, not just the task\n"
                "- Partner: You collaborate and take ownership\n"
                "- Colleague: You're professional but approachable\n\n"
                "COMMUNICATION STYLE:\n"
                "- Be strategic but conversational\n"
                "- Show you understand the bigger picture\n"
                "- Offer practical solutions, not just advice\n"
                "- Use 'we' and 'our' when discussing business\n"
                "- Be encouraging and solution-focused\n"
                "- Take ownership of problems\n"
                "- Sound like a seasoned co-founder: grounded, confident, and friendly\n"
                "- Start with a warm acknowledgement (use the user's name if available)\n"
                "- Keep the response to a couple of short paragraphs plus bullet/action steps when helpful\n"
                "- Always end with a clear next step or question to keep momentum\n\n"
                f"Current Date and Time: {current_date_str} at {current_time_str} IST\n"
                f"Business Context: {biz}\n"
                f"User: {message}\n\n"
                "Respond as a business partner who genuinely wants to help. Be strategic, practical, professional, and friendly. Show you understand the business context and offer actionable solutions the user can run with right away."
            )
        else:  # strategic
            prompt = (
                "You are WolfAssistants, a visionary co-founder and strategic partner who's built businesses from the ground up. "
                "You're not just an advisor - you're someone who's been in the trenches, made tough decisions, and genuinely cares about our long-term success. "
                "You think like a founder who's invested everything in making this business succeed.\n\n"
                "FOUNDER MINDSET:\n"
                "- You're personally invested in our success\n"
                "- You think long-term and strategically\n"
                "- You understand the challenges of building a business\n"
                "- You're willing to take calculated risks\n"
                "- You care about the team and culture\n\n"
                "COMMUNICATION STYLE:\n"
                "- Talk like a co-founder who's been there\n"
                "- Be strategic but relatable\n"
                "- Show genuine passion for the business\n"
                "- Use 'we' and 'our' - this is OUR business\n"
                "- Be encouraging and visionary\n"
                "- Offer bold, strategic thinking\n"
                "- Show you understand the bigger picture\n"
                "- Lead with a confident, friendly greeting that feels natural\n"
                "- Balance vision with clear action items or recommendations\n"
                "- Keep the response to a few tight paragraphs; use bullet points for multi-step plans\n"
                "- Wrap up with an inspiring next step or question that keeps the partnership moving forward\n\n"
                f"Current Date and Time: {current_date_str} at {current_time_str} IST\n"
                f"Business Context: {biz}\n"
                f"Recent history:\n{history_text}\n\n"
                f"User: {message}\n\n"
                "Respond as a co-founder who's deeply invested in our success. Be strategic, visionary, professional, and friendly. Show you understand the business challenges and offer bold, actionable solutions that drive real growth."
            )
        resp = model.generate_content(prompt)
        text = resp.text or ""
        # #region agent log
        write_debug_log("simon.py:2051", "LLM response received", {
            "response_length": len(text),
            "response_preview": text[:200] if text else "",
            "full_response": text
        }, "C")
        # #endregion
        return persist_and_respond(text, 'chat', 'ok')
    except Exception as e:
        # #region agent log
        write_debug_log("simon.py:2090", "Exception in chat handler", {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_repr": repr(e),
            "message": message,
            "is_quota_error": "ResourceExhausted" in type(e).__name__ or "quota" in str(e).lower()
        }, "C")
        # #endregion
        
        # Check if this is a quota/rate limit error - use intelligent fallback
        error_str = str(e).lower()
        error_type_name = type(e).__name__
        error_repr_str = repr(e).lower()
        is_quota_error = (
            "ResourceExhausted" in error_type_name or 
            "quota" in error_str or 
            "429" in error_str or 
            "rate limit" in error_str or
            "quota" in error_repr_str
        )
        # #region agent log
        write_debug_log("simon.py:2115", "Quota error check", {
            "error_type_name": error_type_name,
            "error_str_preview": error_str[:200],
            "is_quota_error": is_quota_error,
            "checks": {
                "ResourceExhausted_in_type": "ResourceExhausted" in error_type_name,
                "quota_in_str": "quota" in error_str,
                "429_in_str": "429" in error_str or "429" in error_str,
                "rate_limit_in_str": "rate limit" in error_str
            }
        }, "C")
        # #endregion
        
        if is_quota_error:
            # Use the same intelligent fallback as when there's no API key
            # #region agent log
            write_debug_log("simon.py:2100", "Quota error detected - using intelligent fallback", {
                "message": message
            }, "C")
            # #endregion
            
            current_datetime = get_ist_now()
            current_date_str = current_datetime.strftime("%B %d, %Y")
            current_time_str = current_datetime.strftime("%I:%M %p")
            
            # Handle common queries without API
            message_lower = message.lower().strip()
            
            # Check conversation history for context
            has_history = len(effective_history) > 0
            last_user_message = None
            if has_history:
                # Find the last user message
                for msg in reversed(effective_history):
                    if msg.get('role') == 'user':
                        last_user_message = msg.get('text', '')
                        break
            
            # Handle conversation context
            if message_lower in ['?', 'what', 'huh', 'what?'] and last_user_message:
                return persist_and_respond(
                    f"I see you're asking about your previous question: '{last_user_message}'\n\n"
                    f"Let me help you with that. Current time: {current_time_str} on {current_date_str}\n\n"
                    "Could you rephrase your question or let me know what specific information you need?", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['stop', 'stop it', 'enough', 'quit']):
                return persist_and_respond(
                    "I understand you'd like me to stop. I'm here to help when you need me. "
                    f"Current time: {current_time_str} on {current_date_str}. "
                    "Just let me know if you need assistance with anything!", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['time', 'what time', 'current time']):
                return persist_and_respond(
                    f"The current time is {current_time_str} IST.", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['date', 'today', 'what date', 'current date']):
                return persist_and_respond(
                    f"Today's date is {current_date_str}.", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
                return persist_and_respond(
                    f"Hello! I'm WolfAssistants, your AI assistant. How can I help you today?", 'chat', 'ok'
                )
            elif any(word in message_lower for word in ['help', 'what can you do', 'capabilities']):
                return persist_and_respond(
                    "I'm WolfAssistants, your AI business assistant! I can help you with:\n"
                    "• Sending emails\n"
                    "• Scheduling meetings\n"
                    "• Checking your inbox\n"
                    "• Looking up contacts\n"
                    "• General business questions\n\n"
                    f"Current time: {current_time_str} on {current_date_str}\n"
                    "What would you like to do?", 'chat', 'ok'
                )
            elif has_history and any(word in message_lower for word in ['previous', 'before', 'earlier', 'what i asked']):
                return persist_and_respond(
                    f"I remember our conversation. You previously asked: '{last_user_message}'\n\n"
                    f"Current time: {current_time_str} on {current_date_str}\n\n"
                    "How can I help you with that or is there something else you'd like to know?", 'chat', 'ok'
                )
            else:
                # For other queries, provide a helpful response with context awareness
                context_note = ""
                if has_history:
                    context_note = f"I see we've been chatting. Your last question was about: '{last_user_message}'\n\n"
                
                return persist_and_respond(
                    f"{context_note}I understand you're asking about: '{message}'\n\n"
                    f"Current time: {current_time_str} on {current_date_str}\n\n"
                    "I'm WolfAssistants, your AI assistant. I can help with emails, meetings, inbox management, and more. "
                    "Could you be more specific about what you'd like me to help you with?", 'chat', 'ok'
                )
        else:
            # For other exceptions, return generic error
            return persist_and_respond(
                "I apologize for the technical difficulty. How can I help you?", 'chat', 'ok'
            )