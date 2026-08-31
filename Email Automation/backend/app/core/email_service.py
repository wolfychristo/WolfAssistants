"""
Email Service for Referral System

Handles sending invitation emails and other referral-related communications.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending referral emails."""
    
    def __init__(self):
        self.smtp_host = settings.SYSTEM_EMAIL_HOST or "localhost"
        self.smtp_port = settings.SYSTEM_EMAIL_PORT or 587
        self.smtp_user = settings.SYSTEM_EMAIL_USER or ""
        self.smtp_password = settings.SYSTEM_EMAIL_PASSWORD or ""
        self.from_email = settings.SYSTEM_EMAIL_FROM or "noreply@wolfy.com"
        self.use_tls = settings.SYSTEM_EMAIL_USE_TLS
    
    async def send_invitation_email(
        self,
        to_email: str,
        referrer_name: str,
        personal_message: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> bool:
        """Send referral invitation email."""
        
        # Validate email configuration
        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            logger.error("Email service not properly configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = f"{referrer_name} invited you to join Wolfy! 🎉"
            
            # Create HTML content
            html_content = self._create_invitation_html(
                referrer_name, personal_message, referral_code
            )
            
            # Create plain text content
            text_content = self._create_invitation_text(
                referrer_name, personal_message, referral_code
            )
            
            # Attach parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Invitation email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invitation email to {to_email}: {e}")
            return False
    
    def _create_invitation_html(
        self,
        referrer_name: str,
        personal_message: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> str:
        """Create HTML content for invitation email."""
        
        signup_url = f"https://wolfy.com/signup?ref={referral_code}" if referral_code else "https://wolfy.com/signup"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>You're Invited to Wolfy!</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #4F46E5;
                    margin-bottom: 10px;
                }}
                .invitation-text {{
                    font-size: 18px;
                    margin-bottom: 20px;
                    color: #666;
                }}
                .personal-message {{
                    background: #F3F4F6;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    font-style: italic;
                    border-left: 4px solid #4F46E5;
                }}
                .benefits {{
                    margin: 30px 0;
                }}
                .benefit {{
                    display: flex;
                    align-items: center;
                    margin: 15px 0;
                    font-size: 16px;
                }}
                .benefit-icon {{
                    font-size: 24px;
                    margin-right: 15px;
                }}
                .cta-button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #4F46E5, #7C3AED);
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 18px;
                    text-align: center;
                    margin: 20px 0;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .cta-button:hover {{
                    background: linear-gradient(135deg, #3730A3, #6D28D9);
                }}
                .referral-code {{
                    background: #FEF3C7;
                    border: 2px dashed #F59E0B;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    margin: 20px 0;
                    font-family: monospace;
                    font-size: 18px;
                    font-weight: bold;
                    color: #92400E;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #E5E7EB;
                    color: #666;
                    font-size: 14px;
                }}
                .social-links {{
                    margin: 20px 0;
                }}
                .social-links a {{
                    color: #4F46E5;
                    text-decoration: none;
                    margin: 0 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🐺 Wolfy</div>
                    <h1>You're Invited to Join Wolfy!</h1>
                    <p class="invitation-text">
                        <strong>{referrer_name}</strong> has invited you to join Wolfy, 
                        the AI-powered email automation platform that's revolutionizing 
                        how businesses communicate.
                    </p>
                </div>
                
                {f'<div class="personal-message"><strong>Personal message from {referrer_name}:</strong><br>"{personal_message}"</div>' if personal_message else ''}
                
                <div class="benefits">
                    <h2>Why Join Wolfy?</h2>
                    <div class="benefit">
                        <span class="benefit-icon">🤖</span>
                        <span>AI-powered email automation that saves you hours every day</span>
                    </div>
                    <div class="benefit">
                        <span class="benefit-icon">📊</span>
                        <span>Smart analytics and insights to optimize your campaigns</span>
                    </div>
                    <div class="benefit">
                        <span class="benefit-icon">🎯</span>
                        <span>Personalized recommendations based on your industry</span>
                    </div>
                    <div class="benefit">
                        <span class="benefit-icon">⚡</span>
                        <span>Lightning-fast setup and easy-to-use interface</span>
                    </div>
                </div>
                
                {f'<div class="referral-code">Your Referral Code: {referral_code}</div>' if referral_code else ''}
                
                <div style="text-align: center;">
                    <a href="{signup_url}" class="cta-button">
                        Join Wolfy & Get 25 Free Credits! 🎁
                    </a>
                </div>
                
                <div class="footer">
                    <p>This invitation was sent by {referrer_name} through Wolfy's referral program.</p>
                    <p>If you didn't expect this email, you can safely ignore it.</p>
                    <div class="social-links">
                        <a href="https://wolfy.com">Website</a> |
                        <a href="https://wolfy.com/privacy">Privacy</a> |
                        <a href="https://wolfy.com/unsubscribe">Unsubscribe</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_invitation_text(
        self,
        referrer_name: str,
        personal_message: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> str:
        """Create plain text content for invitation email."""
        
        signup_url = f"https://wolfy.com/signup?ref={referral_code}" if referral_code else "https://wolfy.com/signup"
        
        text = f"""
        🐺 WOLFY - You're Invited!
        
        Hi there!
        
        {referrer_name} has invited you to join Wolfy, the AI-powered email automation platform that's revolutionizing how businesses communicate.
        
        {f'Personal message from {referrer_name}:' if personal_message else ''}
        {f'"{personal_message}"' if personal_message else ''}
        
        Why Join Wolfy?
        🤖 AI-powered email automation that saves you hours every day
        📊 Smart analytics and insights to optimize your campaigns  
        🎯 Personalized recommendations based on your industry
        ⚡ Lightning-fast setup and easy-to-use interface
        
        {f'Your Referral Code: {referral_code}' if referral_code else ''}
        
        Join Wolfy & Get 25 Free Credits! 🎁
        {signup_url}
        
        This invitation was sent by {referrer_name} through Wolfy's referral program.
        If you didn't expect this email, you can safely ignore it.
        
        ---
        Wolfy - AI Email Automation Platform
        Website: https://wolfy.com
        Privacy: https://wolfy.com/privacy
        Unsubscribe: https://wolfy.com/unsubscribe
        """
        
        return text
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        referral_code: Optional[str] = None
    ) -> bool:
        """Send welcome email to new user."""
        
        # Validate email configuration
        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            logger.error("Email service not properly configured")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "Welcome to Wolfy! 🎉"
            
            # Create content
            html_content = self._create_welcome_html(user_name, referral_code)
            text_content = self._create_welcome_text(user_name, referral_code)
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Welcome email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {to_email}: {e}")
            return False
    
    def _create_welcome_html(self, user_name: str, referral_code: Optional[str] = None) -> str:
        """Create HTML content for welcome email."""
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Wolfy!</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #4F46E5;
                    margin-bottom: 10px;
                }}
                .welcome-bonus {{
                    background: linear-gradient(135deg, #10B981, #059669);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🐺 Wolfy</div>
                    <h1>Welcome to Wolfy, {user_name}!</h1>
                </div>
                
                <div class="welcome-bonus">
                    <h2>🎁 You've Received 25 Free Credits!</h2>
                    <p>Start exploring Wolfy's AI-powered features right away!</p>
                </div>
                
                {f'<p><strong>Referral Code:</strong> {referral_code}</p>' if referral_code else ''}
                
                <p>Ready to get started? Here's what you can do next:</p>
                <ul>
                    <li>🤖 Try our AI email composer</li>
                    <li>📊 Set up your first campaign</li>
                    <li>🎯 Explore personalized recommendations</li>
                    <li>👥 Invite friends and earn more credits!</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://wolfy.com/dashboard" style="background: #4F46E5; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Go to Dashboard
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_welcome_text(self, user_name: str, referral_code: Optional[str] = None) -> str:
        """Create plain text content for welcome email."""
        
        return f"""
        🐺 WOLFY - Welcome!
        
        Hi {user_name},
        
        Welcome to Wolfy! 🎉
        
        🎁 You've Received 25 Free Credits!
        Start exploring Wolfy's AI-powered features right away!
        
        {f'Referral Code: {referral_code}' if referral_code else ''}
        
        Ready to get started? Here's what you can do next:
        🤖 Try our AI email composer
        📊 Set up your first campaign  
        🎯 Explore personalized recommendations
        👥 Invite friends and earn more credits!
        
        Go to Dashboard: https://wolfy.com/dashboard
        
        ---
        Wolfy - AI Email Automation Platform
        """
