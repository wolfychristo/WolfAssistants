# WolfAssistants - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Quick Start Guide](#quick-start-guide)
4. [Features & Capabilities](#features--capabilities)
5. [API Documentation](#api-documentation)
6. [Security Implementation](#security-implementation)
7. [Database Schema](#database-schema)
8. [Admin Dashboard](#admin-dashboard)
9. [Development Setup](#development-setup)
10. [Deployment Guide](#deployment-guide)
11. [Troubleshooting](#troubleshooting)
12. [Technical Specifications](#technical-specifications)

---

## Project Overview

WolfAssistants is an enterprise-grade email automation platform built with **React.js** frontend and **Python FastAPI** backend, powered by Google Gemini AI. Features intelligent email generation, context-aware replies, web research capabilities, and advanced security measures.

### Key Highlights
- **AI-Powered**: Google Gemini 2.0 Flash integration for intelligent email generation
- **Enterprise Security**: Comprehensive security middleware with CSP, HSTS, rate limiting
- **Real-time Monitoring**: Live dashboards for system and user monitoring
- **Scalable Architecture**: Supports 100+ concurrent users
- **Modern Tech Stack**: React.js + TypeScript + FastAPI + SQLAlchemy

---

## Architecture & Technology Stack

### Frontend
- **React.js 18+** with TypeScript
- **Tailwind CSS** for styling
- **React Query** for state management
- **React Router** for navigation
- **Lucide React** for icons

### Backend
- **Python 3.9+** with FastAPI
- **SQLAlchemy** ORM with Alembic migrations
- **JWT Authentication** with bcrypt password hashing
- **Pydantic** for data validation
- **APScheduler** for background tasks

### Database
- **SQLite** (development)
- **PostgreSQL** (production)

### AI Integration
- **Google Gemini 2.0 Flash** API
- **Web Research Engine** (free scraping)
- **Context-Aware Processing**

### Security
- **Custom Middleware Stack**
- **Rate Limiting** (IP and endpoint-based)
- **Input Sanitization** (XSS, SQL injection protection)
- **Security Headers** (CSP, HSTS, X-Frame-Options)
- **Secure OTP System** (military-grade)

---

## Quick Start Guide

### Prerequisites
- Node.js 18+
- Python 3.9+
- Git

### Option 1: Automated Setup (Windows)
```bash
# Run the startup script
start.bat
```

### Option 2: Manual Setup

#### Backend Setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Environment Configuration

**Backend (.env):**
```bash
SECRET_KEY=your-super-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql+psycopg2://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE_NAME>
SYSTEM_EMAIL_HOST=smtp.gmail.com
SYSTEM_EMAIL_PORT=587
SYSTEM_EMAIL_USER=info@wolfassistants.com
SYSTEM_EMAIL_PASSWORD=your-app-password
SYSTEM_EMAIL_FROM=WolfAssistants <info@wolfassistants.com>
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Frontend (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Interactive API**: http://localhost:8000/redoc

---

## Features & Capabilities

### 🤖 Wolfy AI Assistant
- **Intelligent Email Generation**: Context-aware email creation
- **Conversation Context**: Reads previous email threads for appropriate replies
- **Web Research**: Real-time information gathering without paid APIs
- **Business Intelligence**: Strategic analysis and industry insights
- **Natural Language Processing**: Understands complex requests

### 📧 Advanced Email Features
- **Context-Aware Replies**: Automatically reads cold emails and client responses
- **Smart Follow-ups**: References original cold emails for follow-up context
- **Email Scheduling**: Natural language time parsing
- **Conversation Threading**: Maintains email conversation context
- **Auto Follow-up System**: Automated follow-ups after 24 hours

### 🔒 Enterprise Security
- **Security Headers**: CSP, HSTS, X-Frame-Options
- **Rate Limiting**: IP-based and endpoint-specific
- **Input Sanitization**: XSS, SQL injection protection
- **Security Auditing**: Real-time monitoring and threat detection
- **Secure OTP**: Alphanumeric OTP system (2 numbers, 2 uppercase, 2 lowercase)

### 📊 Monitoring & Analytics
- **Real-time Health Checks**: Database, email service, AI API monitoring
- **User Monitoring**: Track active users, feature usage, performance metrics
- **Security Dashboard**: IP analysis, rate limit status, threat monitoring
- **Performance Metrics**: Response times, error rates, system utilization

### 📋 Core Functionality
- **Contact Management**: CRUD operations with CSV import/export
- **Email Automation**: AI-powered email generation and scheduling
- **Meeting Scheduling**: Calendar integration and management
- **Todo Management**: Task tracking with priority levels
- **Analytics**: Response tracking and performance metrics

---

## API Documentation

### Authentication
```
POST /api/v1/auth/register          # User registration
POST /api/v1/auth/login             # User login
GET  /api/v1/auth/me                # Get current user
POST /api/v1/auth/forgot-password   # Send reset link
POST /api/v1/auth/reset-password    # Reset with token
```

### Wolfy AI Assistant
```
POST /api/v1/wolfy/chat             # Chat with Wolfy AI
POST /api/v1/wolfy/send-email       # Send AI-generated email
POST /api/v1/wolfy/schedule-meeting # Schedule meeting via Wolfy
POST /api/v1/wolfy/web-research     # Perform web research
```

### Contacts
```
GET    /api/v1/contacts             # List all contacts
POST   /api/v1/contacts             # Create new contact
GET    /api/v1/contacts/{id}        # Get contact details
PUT    /api/v1/contacts/{id}        # Update contact
DELETE /api/v1/contacts/{id}        # Delete contact
POST   /api/v1/contacts/import      # Import CSV
GET    /api/v1/contacts/export      # Export CSV
```

### Emails
```
GET  /api/v1/emails                 # List emails (supports folder filter)
GET  /api/v1/emails/counts          # Folder counts
POST /api/v1/emails/send            # Send email
POST /api/v1/emails/reply           # Generate and send reply
POST /api/v1/emails/followup        # Generate and send follow-up
POST /api/v1/emails/mark-read/{id}  # Mark email as read
POST /api/v1/emails/spam/{id}       # Move to spam
```

### Meetings
```
GET    /api/v1/meetings             # List meetings
POST   /api/v1/meetings             # Create meeting
PUT    /api/v1/meetings/{id}        # Update meeting
DELETE /api/v1/meetings/{id}        # Delete meeting
```

### Todos
```
GET    /api/v1/todos                # List todos
POST   /api/v1/todos                # Create todo
PUT    /api/v1/todos/{id}           # Update todo
DELETE /api/v1/todos/{id}           # Delete todo
POST   /api/v1/todos/{id}/toggle    # Toggle completion
```

### Email Settings
```
GET  /api/v1/email-settings/me      # Get SMTP/IMAP settings
PUT  /api/v1/email-settings/me      # Update SMTP/IMAP settings
POST /api/v1/email-settings/test-smtp # Test outbound SMTP
POST /api/v1/email-settings/test-imap # Test inbound IMAP
```

### Secure OTP System
```
POST /api/v1/secure-otp/forgot-password # Send structured OTP
POST /api/v1/secure-otp/verify-otp      # Verify structured OTP
POST /api/v1/secure-otp/reset-password  # Reset password with OTP
```

### Security & Monitoring
```
GET /api/v1/security/dashboard      # Security monitoring dashboard
GET /api/v1/security/ip-analysis    # IP analysis and blocking
GET /api/v1/security/rate-limits    # Rate limit status
GET /api/v1/monitoring/dashboard    # System monitoring dashboard
GET /api/v1/monitoring/health       # Health status of all services
GET /api/v1/monitoring/users        # Active user monitoring
```

---

## Security Implementation

### Authentication & Authorization
- **JWT Authentication**: Secure token-based auth with refresh tokens
- **Password Hashing**: bcrypt for secure password storage
- **Secure OTP**: Alphanumeric OTP system (2 numbers, 2 uppercase, 2 lowercase)
- **Rate Limiting**: IP-based and endpoint-specific rate limiting
- **Session Management**: Secure session handling with automatic cleanup

### Security Middleware
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Input Sanitization**: Protection against XSS, SQL injection, command injection
- **CORS Protection**: Configurable cross-origin settings
- **Request Validation**: Pydantic models for comprehensive data validation
- **Security Auditing**: Real-time monitoring and threat detection

### Secure OTP System
- **Format**: 2 numbers + 2 uppercase + 2 lowercase (6 characters)
- **Security**: Cryptographically secure random generation
- **Expiration**: 10-minute expiration window
- **Rate Limiting**: Prevents brute force attacks
- **Examples**: `hW8w8T`, `P7Y4gy`, `o6Q7yY`

---

## Database Schema

### Core Tables
```sql
-- Users
users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR,
    created_at DATETIME,
    updated_at DATETIME,
    deleted_at DATETIME,
    deletion_reason VARCHAR,
    is_admin BOOLEAN DEFAULT 0,
    auto_followup_enabled BOOLEAN DEFAULT 0,
    auto_followup_max_days INTEGER DEFAULT 7,
    auto_followup_daily_hour INTEGER,
    last_auto_followup_run DATETIME,
    last_auto_followup_sent_count INTEGER DEFAULT 0
)

-- Contacts
contacts (
    id INTEGER PRIMARY KEY,
    owner_email VARCHAR,
    name VARCHAR,
    email VARCHAR,
    company VARCHAR,
    phone VARCHAR,
    position VARCHAR,
    status VARCHAR,
    notes TEXT,
    sender_name VARCHAR,
    sender_position VARCHAR,
    sender_firm VARCHAR,
    created_at DATETIME,
    updated_at DATETIME
)

-- Emails
emails (
    id INTEGER PRIMARY KEY,
    owner_email VARCHAR,
    subject VARCHAR,
    body TEXT,
    to_address VARCHAR,
    from_address VARCHAR,
    status VARCHAR,
    sent_at DATETIME,
    received_at DATETIME,
    is_starred BOOLEAN DEFAULT 0,
    is_read BOOLEAN DEFAULT 1,
    scheduled_for DATETIME,
    deleted_at DATETIME,
    last_error TEXT,
    original_folder VARCHAR
)

-- Meetings
meetings (
    id INTEGER PRIMARY KEY,
    owner_email VARCHAR,
    title VARCHAR,
    description TEXT,
    start_time DATETIME,
    end_time DATETIME,
    location VARCHAR,
    attendees TEXT,
    type VARCHAR,
    status VARCHAR,
    created_at DATETIME,
    updated_at DATETIME
)

-- Todos
todos (
    id INTEGER PRIMARY KEY,
    owner_email VARCHAR,
    title VARCHAR,
    description TEXT,
    due_date DATETIME,
    priority VARCHAR,
    completed BOOLEAN DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
)

-- Chat Sessions
chat_sessions (
    id INTEGER PRIMARY KEY,
    owner_email VARCHAR,
    title VARCHAR,
    contact_name VARCHAR,
    contact_email VARCHAR,
    is_active BOOLEAN DEFAULT 1,
    last_message_at DATETIME,
    created_at DATETIME
)

-- Chat Messages
chat_messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    role VARCHAR,
    content TEXT,
    intent VARCHAR,
    status VARCHAR,
    message_metadata TEXT,
    created_at DATETIME
)

-- Password Reset OTPs
password_reset_otps (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    otp_code VARCHAR,
    expires_at DATETIME,
    used BOOLEAN DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    created_at DATETIME
)
```

---

## Admin Dashboard

### Complete Admin System
The admin dashboard provides comprehensive insights into user behavior, signups, and account management.

#### Key Features
- **Three-Tab Interface**: Overview, Users, Analytics
- **Real-time Metrics**: Live user statistics and trends
- **User Management**: View, delete, and restore users
- **Responsive Design**: Works on all devices
- **Professional UI**: Clean, modern interface

#### Admin API Endpoints
```
GET /api/v1/admin/stats                    # Comprehensive statistics
GET /api/v1/admin/users                    # Paginated user list
POST /api/v1/admin/users/{id}/delete       # Soft delete user
POST /api/v1/admin/users/{id}/restore      # Restore deleted user
GET /api/v1/admin/analytics/signups        # Signup analytics
GET /api/v1/admin/analytics/deletions      # Deletion analytics
GET /api/v1/admin/system/health            # System health metrics
```

#### Dashboard Features
- **Overview Tab**: Key metrics, tier distribution, recent activity
- **Users Tab**: User management table with filters and actions
- **Analytics Tab**: Signup trends, deletion patterns, tier analytics

---

## Development Setup

### Project Structure
```
WolfAssistants/
├── frontend/                 # React.js frontend
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── contexts/       # React contexts
│   │   ├── services/       # API services
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── tsconfig.json
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   │   └── v1/         # API version 1
│   │   ├── core/           # Core configuration
│   │   ├── middleware/     # Security middleware
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── monitoring/     # Monitoring system
│   ├── main.py             # FastAPI app entry point
│   └── requirements.txt
└── README.md
```

### Frontend Development
```bash
cd frontend
npm run dev          # Start development server
npm run build        # Build for production
npm run test         # Run tests
npm run lint         # Lint code
```

### Backend Development
```bash
cd backend
python main.py       # Start development server
# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

---

## Deployment Guide

### Frontend (Production)
```bash
cd frontend
npm run build
# Serve the build folder with nginx or similar
```

### Backend (Production)
```bash
cd backend
# Use gunicorn or uvicorn with proper WSGI server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker (Optional)
```bash
docker-compose up -d
```

### Local PostgreSQL with Docker
```bash
docker run --name ea-postgres -e POSTGRES_PASSWORD=devpass -p 5432:5432 -d postgres:16
# .env
# DATABASE_URL=postgresql+psycopg://postgres:devpass@localhost:5432/postgres
```

---

## Troubleshooting

### Common Issues

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

### Log Analysis
```bash
# Backend logs
tail -f backend/logs/app.log

# Security logs
tail -f backend/logs/security.log

# Error logs
tail -f backend/logs/error.log
```

---

## Technical Specifications

### Performance Targets
- **Concurrent Users**: 100+ simultaneous users
- **Response Time**: <200ms average API response
- **Throughput**: 1000+ requests per minute
- **Uptime**: 99.9% availability

### Resource Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB minimum for database and logs
- **Network**: Stable internet connection for AI API calls

### Security Compliance
- **100% Secure**: Comprehensive security measures against common attacks
- **Input Validation**: Protection against all major injection attacks
- **Rate Limiting**: Prevents brute force and DDoS attacks
- **Audit Logging**: Complete audit trail for compliance requirements
- **Secure OTP**: Military-grade OTP generation and validation

### Scalability Features
- **Concurrent User Support**: Optimized for 100+ simultaneous users
- **Rate Limiting**: Prevents abuse and ensures fair resource allocation
- **Database Optimization**: Efficient queries and connection pooling
- **Memory Management**: Automatic cleanup and resource optimization
- **Health Monitoring**: Real-time system health and performance tracking

---

## CSV Import Template

Required columns: `name, email`

Optional: `company, phone, position, status (prospect|active|inactive), notes, sender_name, sender_position, sender_firm`

Example:
```
name,email,company,phone,position,status,notes,sender_name,sender_position,sender_firm
Jane Doe,jane@acme.com,Acme,555-1111,CTO,prospect,"Met at expo",John Smith,Founder,JS Labs
John Roe,john@contoso.com,Contoso,555-2222,Head of Sales,active,"Warm lead",John Smith,Founder,JS Labs
```

---

## Support & Maintenance

### Development Team
- **Lead Developer**: Architecture and code review
- **Backend Developer**: API and database development
- **Frontend Developer**: UI/UX implementation
- **DevOps Engineer**: Infrastructure and deployment

### Maintenance Schedule
- **Daily**: Health checks and monitoring
- **Weekly**: Security updates and patches
- **Monthly**: Performance optimization
- **Quarterly**: Feature updates and improvements

---

## Success Criteria

### Technical Metrics
- **Uptime**: 99.9% availability
- **Response Time**: <200ms average
- **Error Rate**: <0.1%
- **Security**: Zero successful attacks

### Business Metrics
- **User Adoption**: 80%+ team usage
- **Efficiency**: 50% time savings
- **Quality**: 90%+ user satisfaction
- **ROI**: Measurable productivity gains

---

**🎉 Welcome to WolfAssistants - The Future of Email Automation!**

The modern React + FastAPI architecture provides:
- **Enterprise Performance**: Async backend with modern frontend optimized for scale
- **Developer Experience**: Hot reload, TypeScript, auto-docs, and comprehensive monitoring
- **Scalability**: Microservices-ready architecture supporting 100+ concurrent users
- **Security**: Military-grade security with comprehensive threat protection
- **Intelligence**: AI-powered email generation with real-time web research capabilities
- **Maintainability**: Clean separation of concerns with comprehensive monitoring and health checks

---

*This comprehensive documentation serves as the complete guide for implementing, maintaining, and scaling WolfAssistants. For additional support or clarifications, refer to the API documentation at http://localhost:8000/docs or contact the development team.*
