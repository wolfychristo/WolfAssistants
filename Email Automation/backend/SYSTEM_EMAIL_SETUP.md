# System Email Configuration Guide

## Overview
The system now uses a dedicated email address `info@thewascard.com` for sending OTPs and system notifications.

## Configuration

### Environment Variables
Add these to your `.env` file:

```env
# System Email Configuration for OTPs and Notifications
SYSTEM_EMAIL_HOST=smtp.your-provider.com
SYSTEM_EMAIL_PORT=587
SYSTEM_EMAIL_USER=info@thewascard.com
SYSTEM_EMAIL_PASSWORD=your-secure-password
SYSTEM_EMAIL_FROM=WolfAssistants <info@thewascard.com>
SYSTEM_EMAIL_USE_TLS=true
```

### Email Provider Setup
1. **SMTP Host**: Configure with your email provider's SMTP server
2. **Port**: Usually 587 for TLS or 465 for SSL
3. **Username**: info@thewascard.com
4. **Password**: Your email account password
5. **TLS**: Enable for secure connection

## Features Using System Email
- ✅ Password Reset OTPs
- ✅ Email Verification OTPs
- ✅ System Notifications
- ✅ Security Alerts
- ✅ Welcome Emails

## Benefits
- **Reliability**: Dedicated email service for system notifications
- **Professional**: Consistent branding with WolfAssistants
- **Separation**: Keeps user emails separate from system emails
- **Security**: Centralized email configuration management

## Testing
After configuration, test the system email by:
1. Requesting a password reset OTP
2. Checking that emails are sent from info@thewascard.com
3. Verifying email delivery and formatting

## Troubleshooting
- Ensure SMTP credentials are correct
- Check firewall settings for SMTP ports
- Verify email provider allows SMTP access
- Check spam folders for test emails
