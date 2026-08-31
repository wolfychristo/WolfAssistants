# 🔧 WolfAssistants - Technical Specification

## System Overview

WolfAssistants is an enterprise-grade email automation platform built with modern web technologies, featuring AI-powered email generation, comprehensive security measures, and real-time monitoring capabilities.

---

## 🏗️ **Architecture**

### **Technology Stack**
- **Frontend**: React.js 18+ with TypeScript
- **Backend**: Python 3.9+ with FastAPI
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI**: Google Gemini API
- **Authentication**: JWT with bcrypt
- **Security**: Custom middleware stack

### **System Components**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React.js      │    │   FastAPI       │    │   Database      │
│   Frontend      │◄──►│   Backend       │◄──►│   (SQLite/PG)   │
│   (Port 3000)   │    │   (Port 8000)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Tailwind CSS  │    │   Security      │    │   Monitoring    │
│   UI Framework  │    │   Middleware    │    │   System        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🔐 **Security Architecture**

### **Security Middleware Stack**
1. **SecurityHeadersMiddleware**: CSP, HSTS, X-Frame-Options
2. **InputSanitizationMiddleware**: XSS, SQL injection protection
3. **IPRateLimitMiddleware**: Rate limiting and abuse prevention
4. **SecurityAuditMiddleware**: Real-time threat detection

### **Authentication Flow**
```
User Login → JWT Token → Middleware Validation → API Access
     ↓
Password Reset → OTP Generation → Email Delivery → Verification
```

### **OTP System**
- **Format**: 2 numbers + 2 uppercase + 2 lowercase
- **Length**: 6 characters
- **Security**: Cryptographically secure random generation
- **Expiration**: 10 minutes
- **Rate Limiting**: 3 attempts per 10 minutes

---

## 🤖 **AI Integration**

### **Wolfy AI Assistant**
- **Model**: Google Gemini 2.0 Flash
- **Context Window**: Maintains conversation history
- **Capabilities**: Email generation, web research, meeting scheduling
- **Response Types**: Basic, operational, strategic

### **Web Research Engine**
- **Method**: Free web scraping (requests + BeautifulSoup4)
- **Sources**: Google News, company websites, industry trends
- **Rate Limiting**: Respectful scraping with delays
- **Caching**: Temporary storage for performance

---

## 📊 **Database Schema**

### **Core Tables**
```sql
-- Users
users (id, email, hashed_password, created_at, updated_at)

-- Contacts
contacts (id, owner_email, name, email, company, phone, position, status, notes)

-- Emails
emails (id, owner_email, subject, body, to_address, from_address, status, sent_at, received_at)

-- Password Reset OTPs
password_reset_otps (id, user_id, otp_code, expires_at, used, attempts, created_at)

-- Chat Sessions
chat_sessions (id, owner_email, title, contact_name, contact_email, is_active, last_message_at)

-- Chat Messages
chat_messages (id, session_id, role, content, intent, status, message_metadata, created_at)

-- Meetings
meetings (id, owner_email, title, description, start_time, end_time, location, attendees, type, status)
```

---

## 🔄 **API Endpoints**

### **Authentication**
```
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
```

### **Wolfy AI Assistant**
```
POST /api/v1/wolfy/chat
POST /api/v1/wolfy/send-email
POST /api/v1/wolfy/schedule-meeting
POST /api/v1/wolfy/web-research
```

### **Secure OTP System**
```
POST /api/v1/secure-otp/forgot-password
POST /api/v1/secure-otp/verify-otp
POST /api/v1/secure-otp/reset-password
```

### **Security & Monitoring**
```
GET  /api/v1/security/dashboard
GET  /api/v1/security/ip-analysis
GET  /api/v1/security/rate-limits
GET  /api/v1/monitoring/dashboard
GET  /api/v1/monitoring/health
GET  /api/v1/monitoring/users
```

---

## 📈 **Performance Specifications**

### **Scalability Targets**
- **Concurrent Users**: 100+ simultaneous users
- **Response Time**: <200ms average API response
- **Throughput**: 1000+ requests per minute
- **Uptime**: 99.9% availability

### **Resource Requirements**
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB minimum for database and logs
- **Network**: Stable internet connection for AI API calls

---

## 🔧 **Development Setup**

### **Prerequisites**
```bash
# Node.js 18+
node --version

# Python 3.9+
python --version

# Git
git --version
```

### **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
python main.py
```

### **Frontend Setup**
```bash
cd frontend
npm install
npm start
```

### **Environment Configuration**
```bash
# Backend .env
SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-gemini-key
DATABASE_URL=postgresql+psycopg2://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE_NAME>
SYSTEM_EMAIL_HOST=smtp.gmail.com
SYSTEM_EMAIL_PORT=587
SYSTEM_EMAIL_USER=info@wolfassistants.com
SYSTEM_EMAIL_PASSWORD=your-app-password
SYSTEM_EMAIL_FROM=WolfAssistants <info@wolfassistants.com>
```

---

## 🧪 **Testing Strategy**

### **Unit Tests**
- API endpoint testing
- Database model testing
- Security middleware testing
- OTP generation and validation

### **Integration Tests**
- End-to-end email flow
- AI integration testing
- Security middleware integration
- Database transaction testing

### **Load Testing**
- 100+ concurrent user simulation
- API rate limiting validation
- Database performance under load
- Memory usage monitoring

### **Security Testing**
- Penetration testing
- SQL injection testing
- XSS vulnerability testing
- Rate limiting validation

---

## 📊 **Monitoring & Observability**

### **Health Checks**
- Database connectivity
- Email service status
- AI API availability
- System resource usage

### **Metrics Collection**
- Request/response times
- Error rates and types
- User activity patterns
- Security event logging

### **Alerting**
- High error rates
- Resource usage thresholds
- Security incidents
- Service downtime

---

## 🚀 **Deployment Architecture**

### **Development Environment**
```
Local Machine
├── React.js (Port 3000)
├── FastAPI (Port 8000)
├── SQLite Database
└── Local File System
```

### **Production Environment**
```
Load Balancer
├── React.js (Static Files)
├── FastAPI (Multiple Instances)
├── PostgreSQL (Primary)
├── Redis (Caching)
└── File Storage (S3/Cloud)
```

---

## 🔒 **Security Implementation**

### **Input Validation**
```python
# Example: Email validation
from pydantic import EmailStr, validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

### **Rate Limiting**
```python
# Example: API rate limiting
@router.post("/api/v1/wolfy/chat")
@rate_limit(requests=10, per=60)  # 10 requests per minute
async def chat_endpoint(request: Request):
    # Implementation
```

### **Security Headers**
```python
# Example: Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

---

## 📋 **API Documentation**

### **Request/Response Examples**

#### Wolfy Chat
```json
// Request
POST /api/v1/wolfy/chat
{
  "message": "Send follow-up to john@company.com",
  "context": {},
  "history": [],
  "session_id": "uuid",
  "contact_name": "John Doe",
  "contact_email": "john@company.com"
}

// Response
{
  "session_id": "uuid",
  "session_title": "Chat with John Doe",
  "is_new_session": false,
  "message": {
    "id": "uuid",
    "role": "wolfy",
    "content": "The email has been successfully sent to John Doe. This was a follow-up to your previous conversation.",
    "intent": "send_email",
    "status": "done",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### Secure OTP
```json
// Request
POST /api/v1/secure-otp/forgot-password
{
  "email": "user@example.com"
}

// Response
{
  "message": "Password reset code sent to your email address."
}
```

---

## 🔧 **Troubleshooting Guide**

### **Common Issues**

#### Backend Won't Start
```bash
# Check Python version
python --version

# Check dependencies
pip list

# Check database connection
python -c "from app.core.database import engine; print(engine.execute('SELECT 1').fetchone())"
```

#### Frontend Build Issues
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version
```

#### AI Integration Issues
```bash
# Test Gemini API
python -c "import google.generativeai as genai; genai.configure(api_key='your-key'); print('API working')"
```

### **Log Analysis**
```bash
# Backend logs
tail -f backend/logs/app.log

# Security logs
tail -f backend/logs/security.log

# Error logs
tail -f backend/logs/error.log
```

---

## 📚 **Development Guidelines**

### **Code Standards**
- **Python**: PEP 8 compliance
- **TypeScript**: ESLint configuration
- **Git**: Conventional commit messages
- **Testing**: 80%+ code coverage

### **Security Best Practices**
- Never commit secrets to version control
- Use environment variables for configuration
- Validate all user inputs
- Implement proper error handling
- Regular security audits

### **Performance Optimization**
- Use database indexes appropriately
- Implement caching where beneficial
- Monitor memory usage
- Optimize API response times
- Regular performance testing

---

## 🎯 **Success Criteria**

### **Technical Metrics**
- **Uptime**: 99.9% availability
- **Response Time**: <200ms average
- **Error Rate**: <0.1%
- **Security**: Zero successful attacks

### **Business Metrics**
- **User Adoption**: 80%+ team usage
- **Efficiency**: 50% time savings
- **Quality**: 90%+ user satisfaction
- **ROI**: Measurable productivity gains

---

## 📞 **Support & Maintenance**

### **Development Team**
- **Lead Developer**: Architecture and code review
- **Backend Developer**: API and database development
- **Frontend Developer**: UI/UX implementation
- **DevOps Engineer**: Infrastructure and deployment

### **Maintenance Schedule**
- **Daily**: Health checks and monitoring
- **Weekly**: Security updates and patches
- **Monthly**: Performance optimization
- **Quarterly**: Feature updates and improvements

---

*This technical specification serves as the comprehensive guide for implementing, maintaining, and scaling WolfAssistants. For additional support or clarifications, refer to the API documentation at http://localhost:8000/docs or contact the development team.*
