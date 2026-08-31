# WolfAssistants - Project Memory & Guidelines

## 🚀 Overview & Architecture
- **Project**: WolfAssistants AI Email Automation Platform
- **Backend**: FastAPI (Python 3.13+) in `Email Automation/backend`
- **Frontend**: React 18 (TypeScript, Tailwind CSS) in `Email Automation/frontend`
- **Extension**: Chrome Manifest V3 Lead Scraper in `Email Automation/extension`
- **Database**: Supabase PostgreSQL (Multi-tenant schema architecture with RLS)

## 🔑 Key Configurations
- **AI Engine**: Wolfy AI (Google Gemini 2.0 Flash) with 8-key automatic failover and load balancing.
- **Email Infrastructure**: SMTP Hostinger (`info@wolfassistants.com` on port 587 TLS).
- **Security**: JWT (`HS256`), password hashing via bcrypt, CORS origin policy enforcement.
- **Performance**: SQLAlchemy pool size: 10, overflow: 5, recycle: 1800s for Supabase free-tier connection limits.

## 🛠️ Essential Commands
- **Backend Start**: `cd "Email Automation/backend" && venv\Scripts\python main.py`
- **Frontend Build**: `cd "Email Automation/frontend" && npm run build`
- **Endpoint Verification**: `python backend/verify_endpoints.py`
- **Index Migration**: `python backend/add_performance_indexes.py`
