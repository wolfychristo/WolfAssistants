# Setup Guide - Email Automation Tool

## 🚀 Quick Start

### Option 1: Use the Startup Script (Recommended)
```bash
# Windows
start.bat

# This will automatically:
# 1. Create Python virtual environment
# 2. Install dependencies
# 3. Start both services
```

### Option 2: Manual Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Python Version Issues
**Problem**: Python version compatibility

**Solution**:
- Use Python 3.9+ (recommended: 3.11+)
- Check version: `python --version`
- **Note**: Python 3.13 has some package compatibility issues

#### 2. Virtual Environment Issues
**Problem**: Virtual environment not activating

**Solution**:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`
- Ensure you see `(venv)` in your prompt

#### 3. Port Already in Use
**Problem**: Port 8000 or 3000 already occupied

**Solution**:
- Backend: Change port in `backend/app/core/config.py`
- Frontend: Change port in `frontend/package.json` proxy setting

#### 4. Package Installation Issues
**Problem**: Some packages fail to install

**Solution**:
- The requirements.txt includes only essential packages
- Advanced features are commented out for compatibility
- Uncomment packages as needed after basic setup works

### Dependencies Explained

#### Essential Packages (Always Installed)
- **FastAPI**: Web framework
- **SQLAlchemy**: Database ORM  
- **JWT**: Authentication
- **Basic utilities**: File handling, HTTP client

#### Optional Packages (Commented Out)
- **pandas**: Data manipulation (uncomment when needed)
- **openpyxl**: Excel support
- **jinja2**: Template engine
- **google-generativeai**: AI features
- **celery**: Background tasks
- **redis**: Task queue backend

## 📁 Project Structure

```
email-automation-tool/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── core/          # Configuration & database
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── api/           # API routes
│   ├── main.py            # FastAPI app entry point
│   └── requirements.txt    # Dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── pages/         # Page components
│   │   └── services/      # API services
│   └── package.json
├── start.bat              # Windows startup script
└── README.md              # Main documentation
```

## 🌐 Access Points

After successful setup:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Interactive API**: http://localhost:8000/redoc

## 🔒 Environment Variables

Create `.env` files in both directories:

**Backend (.env):**
```bash
SECRET_KEY=your-super-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql+psycopg2://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE_NAME>
```

**Frontend (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000
```

## 📝 Next Steps

1. **Start with basic setup** using the current requirements.txt
2. **Test basic functionality** (auth, contacts, emails)
3. **Add advanced features** by uncommenting packages in requirements.txt
4. **Configure production settings** (database, security, etc.)

## 🆘 Getting Help

- Check the console output for error messages
- Verify Python and Node.js versions
- Ensure virtual environment is activated
- Check if ports are available
- Review the main README.md for detailed information
