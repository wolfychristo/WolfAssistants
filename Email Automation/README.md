# WolfAssistants - AI-Powered Email Automation Platform

A comprehensive, enterprise-grade email automation platform built with **React.js** frontend and **Python FastAPI** backend, powered by Google Gemini AI. Features intelligent email generation, context-aware replies, web research capabilities, and advanced security measures.

## 🏗️ **Architecture: React + FastAPI**

The project has been restructured with a modern, scalable architecture designed for enterprise use:

- **Frontend**: React.js with TypeScript, Tailwind CSS, and modern UI components
- **Backend**: Python FastAPI with SQLAlchemy, JWT authentication, and async support
- **Database**: SQLite (dev) / PostgreSQL (prod) with Alembic migrations
- **AI Integration**: Google Gemini API for intelligent email generation and analysis
- **Security**: Comprehensive security middleware with CSP, HSTS, rate limiting, and input sanitization
- **Monitoring**: Real-time health checks, user monitoring, and performance analytics
- **Web Research**: Free web scraping capabilities for real-time information gathering
- **OTP System**: Secure alphanumeric OTP generation (2 numbers, 2 uppercase, 2 lowercase)

## 🚀 **Quick Start**

### **Prerequisites**
- Node.js 18+ and npm
- Python 3.9+
- PostgreSQL (managed/cloud for prod; Docker for local dev recommended)
- Docker Desktop (optional but recommended for local Postgres)

### **1. Clone and Setup**
```bash
git clone <repository-url>
cd email-automation-tool
```

### **2. Frontend Setup**
```bash
cd frontend
npm install
npm start
```
Frontend will run on: **http://localhost:3000**

### **3. Backend Setup**
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
Backend will run on: **http://localhost:8000**

### **4. Environment Configuration**
Create `.env` files in both `frontend/` and `backend/` directories:

**Frontend (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000
```

**Backend (.env):**
```bash
# Core Configuration
SECRET_KEY=your-super-secret-key-here
GEMINI_API_KEY=your-gemini-api-key

# Database Configuration
# Recommended (PostgreSQL for prod/commercial use):
# DATABASE_URL=postgresql+psycopg://postgres:devpass@localhost:5432/postgres

# Local/dev (SQLite):
DATABASE_URL=postgresql+psycopg2://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE_NAME>

# Email Configuration (WolfAssistants System Email)
SYSTEM_EMAIL_HOST=smtp.gmail.com
SYSTEM_EMAIL_PORT=587
SYSTEM_EMAIL_USER=info@wolfassistants.com
SYSTEM_EMAIL_PASSWORD=your-app-password
SYSTEM_EMAIL_FROM=WolfAssistants <info@wolfassistants.com>
SYSTEM_EMAIL_USE_TLS=true

# User Email Configuration (for individual users)
# EMAIL_HOST=...
# EMAIL_PORT=587
# EMAIL_USER=...
# EMAIL_PASSWORD=...
# EMAIL_FROM=...
# EMAIL_USE_TLS=true

# IMAP (inbound email for reply monitoring)
# IMAP_HOST=...
# IMAP_PORT=993
# IMAP_USER=...
# IMAP_PASSWORD=...
# IMAP_USE_SSL=true

# Security Configuration
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Monitoring
ENABLE_MONITORING=true
LOG_LEVEL=INFO
```
See `backend/env.example` for a complete template.

## 🤖 **Wolfy AI Assistant**

Wolfy is your intelligent business assistant powered by Google Gemini AI, designed to handle complex email automation tasks with human-like intelligence.

### **Key Capabilities**
- **Context-Aware Email Generation**: Reads previous email threads to craft appropriate replies and follow-ups
- **Web Research**: Gathers real-time information about companies, news, weather, and market trends
- **Natural Language Processing**: Understands complex requests and responds precisely
- **Business Intelligence**: Provides strategic insights and industry-specific recommendations
- **Conversation Management**: Maintains context across multiple interactions

### **Usage Examples**
```
User: "Send a follow-up email to john@company.com about our meeting yesterday"
Wolfy: Reads the original meeting email, generates context-aware follow-up, and sends it

User: "Research information about Microsoft's latest AI developments"
Wolfy: Searches the web, gathers recent news, and provides comprehensive insights

User: "Reply to the email from sarah@client.com"
Wolfy: Reads Sarah's email, understands the context, and crafts an appropriate response

User: "Schedule a meeting with the team for tomorrow at 2 PM"
Wolfy: Creates meeting, finds available time slots, and sends calendar invites
```

## 🌟 **Features**

### **🤖 Wolfy AI Assistant**
- **Intelligent Email Generation**: Context-aware email creation using Google Gemini AI
- **Conversation Context**: Reads previous email threads for appropriate replies and follow-ups
- **Web Research**: Real-time information gathering (news, weather, company info) without paid APIs
- **Precise Responses**: Responds only to what users ask, providing nothing extra or less
- **Business Intelligence**: Strategic analysis and industry-specific insights

### **📧 Advanced Email Features**
- **Context-Aware Replies**: Automatically reads cold emails and client responses for appropriate replies
- **Smart Follow-ups**: References original cold emails from sent folder for follow-up context
- **Success Messages**: Specific confirmation messages after sending emails
- **Email Scheduling**: Natural language time parsing (e.g., "today at 2:55 PM", "tomorrow 09:00")
- **Conversation Threading**: Maintains email conversation context across interactions

### **🔒 Enterprise Security**
- **Security Headers**: CSP, HSTS, X-Frame-Options, and more
- **Rate Limiting**: IP-based and endpoint-specific rate limiting
- **Input Sanitization**: Protection against XSS, SQL injection, and other attacks
- **Security Auditing**: Real-time monitoring and threat detection
- **Secure OTP**: Alphanumeric OTP system (2 numbers, 2 uppercase, 2 lowercase)

### **📊 Monitoring & Analytics**
- **Real-time Health Checks**: Database, email service, AI API, and system monitoring
- **User Monitoring**: Track active users, feature usage, and performance metrics
- **Security Dashboard**: IP analysis, rate limit status, and threat monitoring
- **Performance Metrics**: Response times, error rates, and system utilization

### **Frontend (React.js)**
- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Real-time Updates**: Live dashboard with WebSocket integration
- **Type Safety**: Full TypeScript support
- **State Management**: React Query for server state
- **Form Handling**: React Hook Form with validation
- **Routing**: React Router with protected routes

### **Backend (FastAPI)**
- **Fast & Async**: Built on FastAPI with async/await support
- **Auto Documentation**: Interactive API docs at `/docs`
- **Database**: SQLAlchemy ORM with Alembic migrations
- **Authentication**: JWT-based auth with bcrypt password hashing
- **Validation**: Pydantic models for request/response validation
- **Background Tasks**: Celery for email processing and scheduling

### **Core Functionality**
- **Contact Management**: CRUD operations with CSV import/export
- **Email Automation**: AI-powered email generation and scheduling
- **Workflow Engine**: Autonomous outreach campaigns
- **Meeting Scheduling**: Calendar integration and management
- **Analytics**: Response tracking and performance metrics

## 📁 **Project Structure**

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
│   │   │       ├── simon.py        # Wolfy AI assistant (file kept as simon.py for backward compatibility, imported as wolfy_router)
│   │   │       ├── secure_otp.py   # Secure OTP system
│   │   │       ├── security_monitoring.py  # Security dashboard
│   │   │       └── monitoring.py   # System monitoring
│   │   ├── core/           # Core configuration
│   │   │   ├── otp_utils.py       # OTP generation utilities
│   │   │   └── config.py          # Application settings
│   │   ├── middleware/     # Security middleware
│   │   │   ├── security.py        # Security headers
│   │   │   ├── ip_rate_limiting.py # Rate limiting
│   │   │   ├── input_sanitization.py # Input validation
│   │   │   └── security_audit.py  # Security auditing
│   │   ├── monitoring/     # Monitoring system
│   │   │   ├── health_checker.py  # Health checks
│   │   │   └── user_monitoring.py # User monitoring
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── utils/          # Utility functions
│   ├── main.py             # FastAPI app entry point
│   └── requirements.txt
└── README.md
```

## 🔧 **Development**

### **Frontend Development**
```bash
cd frontend
npm run dev          # Start development server
npm run build        # Build for production
npm run test         # Run tests
npm run lint         # Lint code
```

### **Backend Development**
```bash
cd backend
# Activate virtual environment
python main.py       # Start development server
# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **Database Migrations**
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## 🌐 **API Endpoints**

### **Authentication**
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/forgot-password` - Send reset link
- `POST /api/v1/auth/reset-password` - Reset with token

### **Contacts**
- `GET /api/v1/contacts` - List all contacts
- `POST /api/v1/contacts` - Create new contact
- `GET /api/v1/contacts/{id}` - Get contact details
- `PUT /api/v1/contacts/{id}` - Update contact
- `DELETE /api/v1/contacts/{id}` - Delete contact
- `POST /api/v1/contacts/import` - Import CSV
- `GET /api/v1/contacts/export` - Export CSV

### **Emails**
- `GET /api/v1/emails` - List emails (supports folder filter)
- `GET /api/v1/emails/counts` - Folder counts
- `POST /api/v1/emails/send` - Send email
- `POST /api/v1/emails/reply` - Generate and send a reply
- `POST /api/v1/emails/reply/preview` - Preview a reply (no send)
- `POST /api/v1/emails/reply/preview-auto` - Preview reply for latest inbound
- `POST /api/v1/emails/followup` - Generate and send follow-up(s)
- `POST /api/v1/emails/follow-up/preview` - Preview a follow-up (no send)
- `POST /api/v1/emails/mark-read/{id}` - Mark email as read
- `POST /api/v1/emails/spam/{id}` - Move to spam
- `POST /api/v1/emails/not-spam` - Whitelist sender and move from spam

### **Meetings**
- `GET /api/v1/meetings` - List meetings
- `POST /api/v1/meetings` - Create meeting
- `PUT /api/v1/meetings/{id}` - Update meeting
- `DELETE /api/v1/meetings/{id}` - Delete meeting

### **Workflow**
- `GET /api/v1/workflow/status` - Get workflow status
- `POST /api/v1/workflow/start` - Start workflow
- `POST /api/v1/workflow/stop` - Stop workflow
- `GET /api/v1/workflow/stats` - Get workflow statistics

### **Email Settings**
- `GET /api/v1/email-settings/me` - Get my SMTP/IMAP settings
- `PUT /api/v1/email-settings/me` - Update my SMTP/IMAP settings
- `POST /api/v1/email-settings/test-smtp` - Test outbound SMTP
- `POST /api/v1/email-settings/test-imap` - Test inbound IMAP

### **Wolfy AI Assistant**
- `POST /api/v1/wolfy/chat` - Chat with Wolfy AI assistant
- `POST /api/v1/wolfy/send-email` - Send AI-generated email
- `POST /api/v1/wolfy/schedule-meeting` - Schedule meeting via Wolfy
- `POST /api/v1/wolfy/web-research` - Perform web research

### **Secure OTP System**
- `POST /api/v1/secure-otp/forgot-password` - Send structured OTP to email
- `POST /api/v1/secure-otp/verify-otp` - Verify structured OTP
- `POST /api/v1/secure-otp/reset-password` - Reset password with structured OTP

### **Security & Monitoring**
- `GET /api/v1/security/dashboard` - Security monitoring dashboard
- `GET /api/v1/security/ip-analysis` - IP analysis and blocking
- `GET /api/v1/security/rate-limits` - Rate limit status
- `GET /api/v1/monitoring/dashboard` - System monitoring dashboard
- `GET /api/v1/monitoring/health` - Health status of all services
- `GET /api/v1/monitoring/users` - Active user monitoring

### **Diagnostics**
- `GET /api/v1/diagnostics/self` - Check current user's DB/SMTP/IMAP setup

## 🔒 **Security Features**

### **Authentication & Authorization**
- **JWT Authentication**: Secure token-based auth with refresh tokens
- **Password Hashing**: bcrypt for secure password storage
- **Secure OTP**: Alphanumeric OTP system (2 numbers, 2 uppercase, 2 lowercase)
- **Rate Limiting**: IP-based and endpoint-specific rate limiting
- **Session Management**: Secure session handling with automatic cleanup

### **Security Middleware**
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Input Sanitization**: Protection against XSS, SQL injection, command injection
- **CORS Protection**: Configurable cross-origin settings
- **Request Validation**: Pydantic models for comprehensive data validation
- **Security Auditing**: Real-time monitoring and threat detection

### **Monitoring & Compliance**
- **Real-time Security Dashboard**: IP analysis, rate limits, and threat monitoring
- **Health Checks**: Database, email service, AI API, and system monitoring
- **User Activity Tracking**: Monitor user behavior and feature usage
- **Audit Logging**: Comprehensive logging of security events and user actions
- **Environment Variables**: Secure configuration management with validation

## 🔐 **Secure OTP System**

WolfAssistants features a military-grade OTP system for password resets and secure authentication.

### **Structured OTP Format**
- **Length**: 6 characters
- **Format**: 2 numbers + 2 uppercase letters + 2 lowercase letters
- **Examples**: `hW8w8T`, `P7Y4gy`, `o6Q7yY`
- **Security**: Cryptographically secure random generation
- **Validation**: Format validation ensures correct structure

### **OTP Features**
- **Unpredictable**: No sequential or common patterns
- **User-Friendly**: Easy to read and type
- **Secure**: Excludes confusing characters (0, 1, I, O, l)
- **Time-Limited**: 10-minute expiration window
- **Rate Limited**: Prevents brute force attacks

### **Usage**
```bash
# Send OTP
POST /api/v1/secure-otp/forgot-password
{"email": "user@example.com"}

# Verify OTP
POST /api/v1/secure-otp/verify-otp
{"email": "user@example.com", "otp": "hW8w8T"}

# Reset Password
POST /api/v1/secure-otp/reset-password
{"email": "user@example.com", "otp": "hW8w8T", "new_password": "newpass123"}
```

## 🧾 CSV Import Template

Required columns: `name, email`

Optional: `company, phone, position, status (prospect|active|inactive), notes, sender_name, sender_position, sender_firm`

Example:
```
name,email,company,phone,position,status,notes,sender_name,sender_position,sender_firm
Jane Doe,jane@acme.com,Acme,555-1111,CTO,prospect,"Met at expo",John Smith,Founder,JS Labs
John Roe,john@contoso.com,Contoso,555-2222,Head of Sales,active,"Warm lead",John Smith,Founder,JS Labs
```

Troubleshooting:
- Ensure the CSV includes a header row and UTF-8 encoding.
- Import uses `multipart/form-data` upload.

## 🚀 **Deployment**

### **Vercel Deployment (Recommended for Production)**

WolfAssistants is configured for easy deployment on Vercel with custom domain support (www.wolfassistants.com).

#### **Prerequisites**
- [ ] Vercel account (sign up at https://vercel.com)
- [ ] GitHub repository with your code
- [ ] Supabase account and database configured
- [ ] Domain name (www.wolfassistants.com) ready
- [ ] Google Gemini API keys (at least one)
- [ ] SMTP email credentials (for system emails)

#### **Quick Start**
1. **Database Setup**: Run migration script: `python backend/run_migration.py`
2. **Local Build Test**: Test production builds locally (see below)
3. **Backend Deployment**: Deploy `Email Automation/backend` as separate Vercel project
4. **Frontend Deployment**: Deploy `Email Automation/frontend` as separate Vercel project
5. **Custom Domain**: Add `www.wolfassistants.com` in Vercel dashboard
6. **Environment Variables**: Configure all required variables (see below)

#### **Local Production Environment Setup**

Before deploying, test your production build locally:

1. **Copy environment templates:**
   ```bash
   # Backend
   cp scripts/backend.env.local.production.template backend/.env.local.production
   # Edit backend/.env.local.production with your values
   
   # Frontend
   cp scripts/frontend.env.local.production.template frontend/.env.local.production
   # Edit frontend/.env.local.production with your values
   ```

2. **Test local production build:**
   
   **Windows:**
   ```powershell
   cd "Email Automation"
   .\scripts\test-local-build.ps1
   ```
   
   **Linux/Mac:**
   ```bash
   cd Email\ Automation
   chmod +x scripts/test-local-build.sh
   ./scripts/test-local-build.sh
   ```

   This script will:
   - Build frontend with production API URL pointing to localhost backend
   - Start backend in production mode
   - Run health checks
   - Test critical endpoints

#### **Detailed Deployment Guide**
See [VERCEL_DEPLOYMENT_GUIDE.md](./VERCEL_DEPLOYMENT_GUIDE.md) for complete step-by-step instructions including:
- Database migration steps
- Backend and frontend deployment configuration
- Custom domain setup with DNS configuration
- Environment variables setup
- Post-deployment verification
- Troubleshooting common issues

#### **Environment Variables**

**Required Variables:**
- Backend: `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, `CORS_ORIGINS`, `GEMINI_API_KEY_1`
- Frontend: `REACT_APP_API_URL`

See [VERCEL_ENV_VARIABLES.md](./VERCEL_ENV_VARIABLES.md) for complete list of all environment variables with examples and descriptions.

#### **Vercel Configuration Files**

The project includes pre-configured Vercel files:
- `vercel.json` - Root monorepo configuration
- `backend/vercel.json` - Backend-specific configuration
- `frontend/vercel.json` - Frontend-specific configuration

These files are ready to use and require no modifications for standard deployments.

### **Traditional Deployment**

#### **Frontend (Production)**
```bash
cd frontend
npm run build
# Serve the build folder with nginx or similar
```

#### **Backend (Production)**
```bash
cd backend
# Use gunicorn or uvicorn with proper WSGI server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### **Docker (Optional)**
```bash
docker-compose up -d
```

### **Local PostgreSQL with Docker**
```bash
docker run --name ea-postgres -e POSTGRES_PASSWORD=devpass -p 5432:5432 -d postgres:16
# .env
# DATABASE_URL=postgresql+psycopg://postgres:devpass@localhost:5432/postgres
```

## 📚 **Documentation**

### **Core Documentation**
- **API Docs**: Available at `http://localhost:8000/docs`
- **ReDoc**: Alternative docs at `http://localhost:8000/redoc`
- **Frontend**: React components and hooks documentation
- **Backend**: FastAPI route documentation

### **Deployment Documentation**
- **[VERCEL_DEPLOYMENT_GUIDE.md](./VERCEL_DEPLOYMENT_GUIDE.md)**: Complete Vercel deployment guide
- **[VERCEL_ENV_VARIABLES.md](./VERCEL_ENV_VARIABLES.md)**: Environment variables reference
- **[MAINTENANCE_CHECKLIST.md](./MAINTENANCE_CHECKLIST.md)**: Regular maintenance tasks
- **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)**: Pre and post-deployment checklist

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License.

## 🆘 **Support**

For support and questions:
- Create an issue in the repository
- Check the API documentation
- Review the code examples

## 🚀 **Deployment Readiness**

WolfAssistants is production-ready with enterprise-grade features:

### **Scalability for 100+ Users**
- **Concurrent User Support**: Optimized for 100+ simultaneous users
- **Rate Limiting**: Prevents abuse and ensures fair resource allocation
- **Database Optimization**: Efficient queries and connection pooling
- **Memory Management**: Automatic cleanup and resource optimization
- **Health Monitoring**: Real-time system health and performance tracking

### **Security Compliance**
- **100% Secure**: Comprehensive security measures against common attacks
- **Input Validation**: Protection against all major injection attacks
- **Rate Limiting**: Prevents brute force and DDoS attacks
- **Audit Logging**: Complete audit trail for compliance requirements
- **Secure OTP**: Military-grade OTP generation and validation

### **Enterprise Features**
- **Real-time Monitoring**: Live dashboards for system and user monitoring
- **Web Research**: Free real-time information gathering capabilities
- **Context-Aware AI**: Intelligent email generation with conversation context
- **Advanced Security**: Multi-layer security middleware and threat detection

---

**🎉 Welcome to WolfAssistants - The Future of Email Automation!**

The modern React + FastAPI architecture provides:
- **Enterprise Performance**: Async backend with modern frontend optimized for scale
- **Developer Experience**: Hot reload, TypeScript, auto-docs, and comprehensive monitoring
- **Scalability**: Microservices-ready architecture supporting 100+ concurrent users
- **Security**: Military-grade security with comprehensive threat protection
- **Intelligence**: AI-powered email generation with real-time web research capabilities
- **Maintainability**: Clean separation of concerns with comprehensive monitoring and health checks
