"""
Secure OTP utilities for WolfAssistants
Provides secure alphanumeric OTP generation and validation
"""
import secrets
import string
import re
from typing import Optional
from datetime import datetime, timedelta

class SecureOTPGenerator:
    """Secure OTP generator with configurable options"""
    
    # Safe characters excluding confusing ones: 0, O, I, l, 1
    SAFE_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    # Character sets for different OTP types
    NUMERIC_CHARS = "23456789"  # Excludes 0, 1
    ALPHANUMERIC_CHARS = SAFE_CHARS
    UPPERCASE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Excludes I, O
    LOWERCASE_CHARS = "abcdefghijkmnopqrstuvwxyz"  # Excludes l, i
    
    @classmethod
    def generate_otp(cls, length: int = 8, char_set: str | None = None) -> str:
        """
        Generate a secure OTP
        
        Args:
            length: Length of the OTP (default: 8)
            char_set: Character set to use (default: SAFE_CHARS)
        
        Returns:
            str: Generated OTP
        """
        if char_set is None:
            char_set = cls.SAFE_CHARS
        
        if length < 4:
            raise ValueError("OTP length must be at least 4 characters")
        
        if length > 32:
            raise ValueError("OTP length cannot exceed 32 characters")
        
        return "".join(secrets.choice(char_set) for _ in range(length))
    
    @classmethod
    def generate_numeric_otp(cls, length: int = 6) -> str:
        """Generate numeric OTP (excluding 0, 1)"""
        return cls.generate_otp(length, cls.NUMERIC_CHARS)
    
    @classmethod
    def generate_alphanumeric_otp(cls, length: int = 8) -> str:
        """Generate alphanumeric OTP (mixed case, excluding confusing chars)"""
        return cls.generate_otp(length, cls.ALPHANUMERIC_CHARS)
    
    @classmethod
    def generate_structured_otp(cls) -> str:
        """
        Generate structured OTP with specific format:
        - 2 numbers
        - 2 uppercase letters
        - 2 lowercase letters
        Total: 6 characters
        """
        # Safe character sets
        numbers = "23456789"  # Excludes 0, 1
        uppercase = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Excludes I, O
        lowercase = "abcdefghijkmnopqrstuvwxyz"  # Excludes l, i
        
        # Generate exactly 2 of each type
        num_chars = [secrets.choice(numbers) for _ in range(2)]
        upper_chars = [secrets.choice(uppercase) for _ in range(2)]
        lower_chars = [secrets.choice(lowercase) for _ in range(2)]
        
        # Combine and shuffle
        all_chars = num_chars + upper_chars + lower_chars
        secrets.SystemRandom().shuffle(all_chars)
        
        return ''.join(all_chars)
    
    @classmethod
    def generate_uppercase_otp(cls, length: int = 8) -> str:
        """Generate uppercase OTP (excluding I, O)"""
        return cls.generate_otp(length, cls.UPPERCASE_CHARS)
    
    @classmethod
    def generate_lowercase_otp(cls, length: int = 8) -> str:
        """Generate lowercase OTP (excluding l, i)"""
        return cls.generate_otp(length, cls.LOWERCASE_CHARS)
    
    @classmethod
    def validate_otp_format(cls, otp: str, expected_length: int = 8) -> bool:
        """
        Validate OTP format
        
        Args:
            otp: OTP to validate
            expected_length: Expected length of OTP
        
        Returns:
            bool: True if valid format
        """
        if not otp or not isinstance(otp, str):
            return False
        
        if len(otp) != expected_length:
            return False
        
        # Check if OTP contains only safe characters
        pattern = f"^[{re.escape(cls.SAFE_CHARS)}]{{{expected_length}}}$"
        return bool(re.match(pattern, otp))
    
    @classmethod
    def get_otp_entropy(cls, length: int = 8, char_set: str | None = None) -> float:
        """
        Calculate OTP entropy in bits
        
        Args:
            length: Length of OTP
            char_set: Character set used
        
        Returns:
            float: Entropy in bits
        """
        if char_set is None:
            char_set = cls.SAFE_CHARS
        
        import math
        return length * math.log2(len(char_set))
    
    @classmethod
    def get_otp_strength(cls, otp: str) -> dict:
        """
        Analyze OTP strength
        
        Args:
            otp: OTP to analyze
        
        Returns:
            dict: Strength analysis
        """
        if not otp:
            return {"strength": "invalid", "entropy": 0, "issues": ["Empty OTP"]}
        
        issues = []
        strength = "weak"
        
        # Check length
        if len(otp) < 6:
            issues.append("Too short (minimum 6 characters recommended)")
        elif len(otp) < 8:
            issues.append("Short length (8+ characters recommended)")
        else:
            strength = "medium"
        
        # Check character diversity
        has_upper = any(c.isupper() for c in otp)
        has_lower = any(c.islower() for c in otp)
        has_digit = any(c.isdigit() for c in otp)
        
        char_types = sum([has_upper, has_lower, has_digit])
        
        if char_types == 1:
            issues.append("Only one character type used")
        elif char_types == 2:
            if strength == "medium":
                strength = "good"
        else:
            if strength == "medium":
                strength = "strong"
            else:
                strength = "good"
        
        # Check for patterns
        if len(set(otp)) < len(otp) * 0.5:
            issues.append("Low character diversity")
        
        # Check for sequential patterns
        if cls._has_sequential_pattern(otp):
            issues.append("Contains sequential patterns")
        
        # Check for repeated patterns
        if cls._has_repeated_pattern(otp):
            issues.append("Contains repeated patterns")
        
        # Calculate entropy
        entropy = cls.get_otp_entropy(len(otp))
        
        if entropy < 20:
            issues.append("Low entropy")
        elif entropy < 30:
            if strength == "strong":
                strength = "good"
        elif entropy >= 30:
            if strength == "good":
                strength = "strong"
        
        return {
            "strength": strength,
            "entropy": entropy,
            "length": len(otp),
            "char_types": char_types,
            "issues": issues
        }
    
    @classmethod
    def _has_sequential_pattern(cls, otp: str) -> bool:
        """Check for sequential patterns like 123, abc, etc."""
        if len(otp) < 3:
            return False
        
        for i in range(len(otp) - 2):
            # Check numeric sequences
            if otp[i:i+3].isdigit():
                if int(otp[i+1]) - int(otp[i]) == 1 and int(otp[i+2]) - int(otp[i+1]) == 1:
                    return True
            
            # Check alphabetic sequences
            if otp[i:i+3].isalpha():
                if ord(otp[i+1].lower()) - ord(otp[i].lower()) == 1 and ord(otp[i+2].lower()) - ord(otp[i+1].lower()) == 1:
                    return True
        
        return False
    
    @classmethod
    def _has_repeated_pattern(cls, otp: str) -> bool:
        """Check for repeated patterns like 121, aba, etc."""
        if len(otp) < 4:
            return False
        
        # Check for 2-character patterns
        for i in range(len(otp) - 3):
            pattern = otp[i:i+2]
            if otp[i+2:i+4] == pattern:
                return True
        
        # Check for 3-character patterns
        for i in range(len(otp) - 6):
            pattern = otp[i:i+3]
            if otp[i+3:i+6] == pattern:
                return True
        
        return False

# Convenience functions
def generate_secure_otp(length: int = 8) -> str:
    """Generate a secure alphanumeric OTP"""
    return SecureOTPGenerator.generate_alphanumeric_otp(length)

def generate_structured_otp() -> str:
    """Generate structured OTP: 2 numbers, 2 uppercase, 2 lowercase (6 chars total)"""
    return SecureOTPGenerator.generate_structured_otp()

def validate_otp(otp: str, expected_length: int = 8) -> bool:
    """Validate OTP format"""
    return SecureOTPGenerator.validate_otp_format(otp, expected_length)

def validate_structured_otp(otp: str) -> bool:
    """Validate structured OTP format: 2 numbers, 2 uppercase, 2 lowercase"""
    if not otp or len(otp) != 6:
        return False
    
    # Count character types
    numbers = sum(1 for c in otp if c.isdigit() and c in "23456789")
    uppercase = sum(1 for c in otp if c.isupper() and c in "ABCDEFGHJKLMNPQRSTUVWXYZ")
    lowercase = sum(1 for c in otp if c.islower() and c in "abcdefghijkmnopqrstuvwxyz")
    
    # Check if we have exactly 2 of each type
    return numbers == 2 and uppercase == 2 and lowercase == 2

def analyze_otp_strength(otp: str) -> dict:
    """Analyze OTP strength"""
    return SecureOTPGenerator.get_otp_strength(otp)

