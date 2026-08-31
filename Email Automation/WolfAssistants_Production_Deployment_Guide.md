# WolfAssistants Production Deployment Guide
## Complete Step-by-Step Guide to Deploy Without Errors

---

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Server Requirements](#server-requirements)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Backend Deployment](#backend-deployment)
6. [Frontend Deployment](#frontend-deployment)
7. [Web Server Configuration](#web-server-configuration)
8. [SSL/HTTPS Setup](#sslhttps-setup)
9. [Domain Configuration](#domain-configuration)
10. [Testing & Validation](#testing--validation)
11. [Troubleshooting Common Issues](#troubleshooting-common-issues)
12. [Maintenance & Monitoring](#maintenance--monitoring)

---

## Pre-Deployment Checklist

### ✅ **Before You Start**
- [ ] Domain name registered and DNS configured
- [ ] VPS/Server with root access (Ubuntu 20.04+ recommended)
- [ ] SSL certificate ready (Let's Encrypt recommended)
- [ ] Database server configured (PostgreSQL recommended)
- [ ] Email server configured (SMTP/IMAP)
- [ ] Google Gemini API key obtained
- [ ] All environment variables prepared

### ✅ **Required Software**
- [ ] Node.js 18+ installed
- [ ] Python 3.9+ installed
- [ ] PostgreSQL 13+ installed
- [ ] Nginx installed
- [ ] Git installed
- [ ] Certbot for SSL

---

## Server Requirements

### **Minimum Specifications**
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **OS**: Ubuntu 20.04 LTS or CentOS 8+

### **Recommended Specifications**
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **OS**: Ubuntu 22.04 LTS

---

## Environment Configuration

### **Step 1: Server Preparation**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y nginx postgresql postgresql-contrib python3 python3-pip python3-venv nodejs npm git certbot python3-certbot-nginx

# Install Node.js 18+ (if not available)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.9+ (if not available)
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev
```

### **Step 2: Create Application User**

```bash
# Create dedicated user for the application
sudo adduser wolfassistants
sudo usermod -aG sudo wolfassistants
sudo su - wolfassistants
```

### **Step 3: Clone Repository**

```bash
# Clone the repository
git clone https://github.com/yourusername/wolfassistants.git
cd wolfassistants/Email\ Automation
```

---

## Database Setup

### **Step 1: PostgreSQL Configuration**

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE wolfassistants;
CREATE USER wolfassistants_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE wolfassistants TO wolfassistants_user;
ALTER USER wolfassistants_user CREATEDB;
\q
```

### **Step 2: Database Connection Test**

```bash
# Test connection
psql -h localhost -U wolfassistants_user -d wolfassistants -c "SELECT version();"
```

---

## Backend Deployment

### **Step 1: Backend Environment Setup**

```bash
cd backend

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install production server
pip install gunicorn
```

### **Step 2: Backend Environment Variables**

```bash
# Create production .env file
cat > .env << 'EOF'
# Core Configuration
SECRET_KEY=your-super-secure-secret-key-here-minimum-32-characters
GEMINI_API_KEY=your-gemini-api-key-here

# Database Configuration
DATABASE_URL=postgresql://wolfassistants_user:your_secure_password@localhost:5432/wolfassistants

# Email Configuration
SYSTEM_EMAIL_HOST=smtp.gmail.com
SYSTEM_EMAIL_PORT=587
SYSTEM_EMAIL_USER=info@wolfassistants.com
SYSTEM_EMAIL_PASSWORD=your-app-password
SYSTEM_EMAIL_FROM=WolfAssistants <info@wolfassistants.com>
SYSTEM_EMAIL_USE_TLS=true

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Security Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Monitoring
ENABLE_MONITORING=true
LOG_LEVEL=INFO

# Production Settings
DEBUG=false
ENVIRONMENT=production
EOF
```

### **Step 3: Database Migration**

```bash
# Run database migrations
python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"'))
    conn.commit()
"

# Initialize database schema
python -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.models.contact import Contact
from app.models.email import Email
from app.models.meeting import Meeting
from app.models.todo import Todo
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.password_reset_otp import PasswordResetOTP

# Create all tables
from app.core.database import Base
Base.metadata.create_all(bind=engine)
print('Database schema created successfully')
"
```

### **Step 4: Gunicorn Configuration**

```bash
# Create Gunicorn configuration
cat > gunicorn.conf.py << 'EOF'
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Logging
accesslog = "/home/wolfassistants/logs/gunicorn_access.log"
errorlog = "/home/wolfassistants/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "wolfassistants_backend"

# Server mechanics
daemon = False
pidfile = "/home/wolfassistants/logs/gunicorn.pid"
user = "wolfassistants"
group = "wolfassistants"
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
EOF
```

### **Step 5: Systemd Service Configuration**

```bash
# Create systemd service file
sudo tee /etc/systemd/system/wolfassistants-backend.service << 'EOF'
[Unit]
Description=WolfAssistants Backend API
After=network.target postgresql.service

[Service]
Type=notify
User=wolfassistants
Group=wolfassistants
WorkingDirectory=/home/wolfassistants/wolfassistants/Email Automation/backend
Environment=PATH=/home/wolfassistants/wolfassistants/Email Automation/backend/venv/bin
ExecStart=/home/wolfassistants/wolfassistants/Email Automation/backend/venv/bin/gunicorn -c gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create logs directory
sudo mkdir -p /home/wolfassistants/logs
sudo chown wolfassistants:wolfassistants /home/wolfassistants/logs

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable wolfassistants-backend
sudo systemctl start wolfassistants-backend
sudo systemctl status wolfassistants-backend
```

---

## Frontend Deployment

### **Step 1: Frontend Environment Setup**

```bash
cd ../frontend

# Install dependencies
npm install

# Create production .env file
cat > .env << 'EOF'
REACT_APP_API_URL=https://yourdomain.com/api
GENERATE_SOURCEMAP=false
EOF

# Build for production
npm run build
```

### **Step 2: Frontend Build Optimization**

```bash
# Install serve for production serving
npm install -g serve

# Test the build locally
serve -s build -l 3000
```

---

## Web Server Configuration

### **Step 1: Nginx Configuration**

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/wolfassistants << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Frontend (React app)
    location / {
        root /home/wolfassistants/wolfassistants/Email\ Automation/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/wolfassistants /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## SSL/HTTPS Setup

### **Step 1: Obtain SSL Certificate**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### **Step 2: Update Nginx for HTTPS**

```bash
# The certbot command above should have automatically updated your Nginx config
# Verify the configuration
sudo nginx -t
sudo systemctl reload nginx
```

---

## Domain Configuration

### **Step 1: DNS Configuration**

Ensure your domain's DNS records point to your server:

```
A Record: yourdomain.com → YOUR_SERVER_IP
A Record: www.yourdomain.com → YOUR_SERVER_IP
CNAME Record: api.yourdomain.com → yourdomain.com (optional)
```

### **Step 2: Update Frontend Configuration**

```bash
# Update frontend .env with your domain
echo "REACT_APP_API_URL=https://yourdomain.com/api" > frontend/.env

# Rebuild frontend
npm run build
```

---

## Testing & Validation

### **Step 1: Backend API Testing**

```bash
# Test backend health
curl -I https://yourdomain.com/api/health

# Test authentication endpoint
curl -X POST https://yourdomain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@yourdomain.com","password":"testpass123"}'

# Test API documentation
curl -I https://yourdomain.com/api/docs
```

### **Step 2: Frontend Testing**

```bash
# Test frontend accessibility
curl -I https://yourdomain.com/

# Test static assets
curl -I https://yourdomain.com/static/js/main.js
```

### **Step 3: End-to-End Testing**

1. **Visit your domain**: https://yourdomain.com
2. **Register a new account**
3. **Test login functionality**
4. **Test contact management**
5. **Test email features**
6. **Test admin dashboard**

---

## Troubleshooting Common Issues

### **Issue 1: 502 Bad Gateway**

**Symptoms**: Frontend shows 502 error, backend not responding

**Solutions**:
```bash
# Check if backend service is running
sudo systemctl status wolfassistants-backend

# Check backend logs
sudo journalctl -u wolfassistants-backend -f

# Restart backend service
sudo systemctl restart wolfassistants-backend

# Check if port 8000 is listening
sudo netstat -tlnp | grep :8000
```

### **Issue 2: CORS Errors**

**Symptoms**: Browser console shows CORS errors

**Solutions**:
```bash
# Check CORS configuration in backend
grep -r "allow_origins" backend/

# Update CORS origins in backend/main.py
# Add your domain to the allowed origins list
```

### **Issue 3: Database Connection Errors**

**Symptoms**: 500 errors, database connection failed

**Solutions**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U wolfassistants_user -d wolfassistants -c "SELECT 1;"

# Check database permissions
sudo -u postgres psql -c "\du wolfassistants_user"
```

### **Issue 4: Static Files Not Loading**

**Symptoms**: CSS/JS files return 404

**Solutions**:
```bash
# Check if build files exist
ls -la frontend/build/static/

# Check Nginx configuration
sudo nginx -t

# Check file permissions
sudo chown -R www-data:www-data frontend/build/
```

### **Issue 5: SSL Certificate Issues**

**Symptoms**: Mixed content errors, SSL warnings

**Solutions**:
```bash
# Check SSL certificate
sudo certbot certificates

# Renew certificate if needed
sudo certbot renew

# Check Nginx SSL configuration
sudo nginx -t
```

---

## Maintenance & Monitoring

### **Step 1: Log Monitoring**

```bash
# Backend logs
sudo journalctl -u wolfassistants-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Application logs
tail -f /home/wolfassistants/logs/gunicorn_error.log
```

### **Step 2: Performance Monitoring**

```bash
# Check system resources
htop
df -h
free -h

# Check database performance
sudo -u postgres psql -d wolfassistants -c "SELECT * FROM pg_stat_activity;"
```

### **Step 3: Backup Strategy**

```bash
# Database backup
pg_dump -h localhost -U wolfassistants_user wolfassistants > backup_$(date +%Y%m%d).sql

# Application backup
tar -czf wolfassistants_backup_$(date +%Y%m%d).tar.gz /home/wolfassistants/wolfassistants/
```

### **Step 4: Update Procedure**

```bash
# Update application
cd /home/wolfassistants/wolfassistants/
git pull origin main

# Update backend
cd Email\ Automation/backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart wolfassistants-backend

# Update frontend
cd ../frontend
npm install
npm run build
sudo systemctl reload nginx
```

---

## Security Checklist

### **✅ Essential Security Measures**

- [ ] SSL certificate installed and working
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Database user has minimal required permissions
- [ ] Environment variables are secure and not exposed
- [ ] Regular security updates applied
- [ ] Log monitoring enabled
- [ ] Backup strategy implemented
- [ ] Rate limiting configured
- [ ] Input validation enabled
- [ ] CORS properly configured

---

## Performance Optimization

### **Step 1: Database Optimization**

```sql
-- Create indexes for better performance
CREATE INDEX idx_emails_owner_email ON emails(owner_email);
CREATE INDEX idx_contacts_owner_email ON contacts(owner_email);
CREATE INDEX idx_meetings_owner_email ON meetings(owner_email);
CREATE INDEX idx_todos_owner_email ON todos(owner_email);
```

### **Step 2: Nginx Optimization**

```nginx
# Add to Nginx configuration
worker_processes auto;
worker_connections 1024;

# Enable caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=10g inactive=60m use_temp_path=off;

# Add to server block
proxy_cache my_cache;
proxy_cache_valid 200 302 10m;
proxy_cache_valid 404 1m;
```

---

## Final Checklist

### **✅ Pre-Launch Verification**

- [ ] Domain resolves to your server
- [ ] SSL certificate is valid and working
- [ ] Backend API responds correctly
- [ ] Frontend loads without errors
- [ ] User registration works
- [ ] User login works
- [ ] All major features functional
- [ ] Admin dashboard accessible
- [ ] Database connections stable
- [ ] Logs are being generated
- [ ] Monitoring is active
- [ ] Backup system is working

### **✅ Post-Launch Monitoring**

- [ ] Monitor error logs for 24 hours
- [ ] Check performance metrics
- [ ] Verify all features work as expected
- [ ] Test with multiple users
- [ ] Monitor resource usage
- [ ] Check SSL certificate renewal

---

## Emergency Procedures

### **If Backend Goes Down**

```bash
# Restart backend service
sudo systemctl restart wolfassistants-backend

# Check logs for errors
sudo journalctl -u wolfassistants-backend -f

# If service won't start, check configuration
sudo systemctl status wolfassistants-backend
```

### **If Frontend Shows Errors**

```bash
# Check Nginx status
sudo systemctl status nginx

# Restart Nginx
sudo systemctl restart nginx

# Check if build files exist
ls -la frontend/build/
```

### **If Database Issues Occur**

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check database connectivity
psql -h localhost -U wolfassistants_user -d wolfassistants
```

---

## Support & Maintenance

### **Regular Maintenance Tasks**

1. **Daily**: Check error logs and system health
2. **Weekly**: Review performance metrics and user activity
3. **Monthly**: Update dependencies and security patches
4. **Quarterly**: Review and optimize database performance

### **Monitoring Commands**

```bash
# System health check
curl -s https://yourdomain.com/api/health | jq

# Database status
sudo -u postgres psql -d wolfassistants -c "SELECT count(*) FROM users;"

# Service status
sudo systemctl status wolfassistants-backend nginx postgresql
```

---

**🎉 Congratulations! Your WolfAssistants application is now successfully deployed in production!**

This guide ensures a robust, secure, and scalable deployment that can handle production traffic without endpoint errors or file crashes. Follow each step carefully, and your application will be ready for your users.

For additional support or specific issues, refer to the logs and monitoring tools provided in this guide.

---

*Last Updated: [Current Date]*
*Version: 1.0*
*WolfAssistants Production Deployment Guide*
