"""
Secure encryption utility for SMTP credentials
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings

class SMTPCredentialEncryption:
    """Encrypt and decrypt SMTP credentials securely"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key from SECRET_KEY"""
        # Use SECRET_KEY as password for key derivation
        password = settings.SECRET_KEY.encode()
        salt = b'email_automation_salt'  # In production, use random salt per user
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt SMTP password"""
        if not password:
            return ""
        try:
            encrypted_password = self.cipher_suite.encrypt(password.encode())
            encrypted_str = base64.urlsafe_b64encode(encrypted_password).decode()
            return encrypted_str
        except Exception as e:
            # Return empty string on error - this will cause authentication to fail
            return ""
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt SMTP password. If decryption fails, assume password is stored in plain text."""
        if not encrypted_password:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted_password = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_password.decode()
        except Exception:
            # Decryption failed - password might be stored in plain text (legacy data)
            # Return the password as-is, assuming it's plain text
            return encrypted_password

# Global instance
smtp_encryption = SMTPCredentialEncryption()
