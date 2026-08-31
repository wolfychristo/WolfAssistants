"""
Spam Detection Module for Email Automation
Detects spam emails and automatically moves them to spam folder
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SpamScore(Enum):
    """Spam score levels"""
    SAFE = 0
    SUSPICIOUS = 1
    LIKELY_SPAM = 2
    DEFINITELY_SPAM = 3

@dataclass
class SpamDetectionResult:
    """Result of spam detection analysis"""
    is_spam: bool
    score: int
    reasons: List[str]
    confidence: float

class SpamDetector:
    """Advanced spam detection using multiple heuristics"""
    
    def __init__(self):
        # Spam keywords and patterns
        self.spam_keywords = [
            # Financial spam (removed legitimate terms like 'money', 'profit', 'earn', 'investment')
            'viagra', 'cialis', 'lottery', 'winner', 'congratulations', 'prize',
            'bitcoin investment', 'crypto investment', 'forex trading scam',
            'loan approval guaranteed', 'credit card debt relief',
            'refinance now', 'mortgage rates slashed',
            
            # Urgency and pressure
            'urgent', 'act now', 'limited time', 'expires', 'deadline', 'immediately',
            'don\'t miss', 'once in a lifetime', 'exclusive offer', 'limited offer',
            
            # Suspicious phrases
            'click here', 'free money', 'no cost', 'risk-free', 'guaranteed',
            'work from home', 'make money', 'get rich', 'easy money',
            'lose weight', 'weight loss', 'diet pills', 'supplements',
            
            # Technical spam indicators
            'unsubscribe', 'opt out', 'remove', 'stop receiving',
            'nigerian prince', 'inheritance', 'bank account', 'transfer funds',
            
            # Common spam subjects
            'you have won', 'claim your prize', 'free gift', 'special offer',
            'act now', 'limited time', 'exclusive deal', 'don\'t miss out'
        ]
        
        # Suspicious email patterns (more lenient to avoid false positives)
        self.suspicious_patterns = [
            # Removed: r'\b\d{4,}\b' - too aggressive, matches dates like 2025-12-09
            # Removed: r'[A-Z]{3,}' - too aggressive, matches normal words like TEST, API, etc.
            r'[!]{3,}',     # Multiple exclamation marks (3+)
            r'[?]{3,}',     # Multiple question marks (3+)
            r'\$\d{5,}',    # Large money amounts ($10000+)
            r'%\d{3,}',     # High percentages (100%+)
            # URLs are checked separately with more context
        ]
        
        # Suspicious sender patterns
        self.suspicious_sender_patterns = [
            r'[a-z]+\d+@',  # Random alphanumeric senders
            r'[a-z]{1,2}\d+@',  # Short name + numbers
            r'[a-z]+[0-9]{3,}@',  # Name with many numbers
            r'[a-z]+\.[a-z]+\.[a-z]+@',  # Multiple dots in sender
        ]
        
        # Legitimate sender patterns (whitelist)
        self.legitimate_domains = [
            'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
            'company.com', 'business.com', 'org', 'edu', 'gov'
        ]
        
        # ADDED: Whitelist for legitimate financial domains
        self.legitimate_financial_domains = [
            'stripe.com', 'paypal.com', 'square.com', 'quickbooks.com',
            'xero.com', 'freshbooks.com', 'wave.com', 'invoice2go.com',
            'zoho.com', 'sage.com', 'intuit.com', 'mint.com',
            'bankofamerica.com', 'chase.com', 'wellsfargo.com',
            'payoneer.com', 'wise.com', 'transferwise.com'
        ]
        
        # ADDED: Whitelist for income-related keywords (reduce spam score)
        self.legitimate_income_keywords = [
            'invoice', 'payment received', 'payment confirmation',
            'receipt', 'transaction', 'deposit', 'withdrawal',
            'statement', 'balance', 'account activity', 'income',
            'revenue', 'salary', 'payroll', 'commission'
        ]
        
        # Spam score thresholds
        self.spam_threshold = 5  # Score above this is considered spam
        self.suspicious_threshold = 3  # Score above this is suspicious

    def detect_spam(self, subject: str, body: str, from_address: str, to_address: str) -> SpamDetectionResult:
        """
        Detect if an email is spam based on multiple factors
        
        Args:
            subject: Email subject line
            body: Email body content
            from_address: Sender email address
            to_address: Recipient email address
            
        Returns:
            SpamDetectionResult with detection details
        """
        score = 0
        reasons = []
        
        # Convert to lowercase for analysis
        subject_lower = subject.lower() if subject else ""
        body_lower = body.lower() if body else ""
        from_lower = from_address.lower() if from_address else ""
        
        # 1. Check for spam keywords in subject
        subject_score, subject_reasons = self._check_keywords(subject_lower, "subject")
        score += subject_score
        reasons.extend(subject_reasons)
        
        # 2. Check for spam keywords in body
        body_score, body_reasons = self._check_keywords(body_lower, "body")
        score += body_score
        reasons.extend(body_reasons)
        
        # 3. Check sender patterns
        sender_score, sender_reasons = self._check_sender_patterns(from_lower)
        score += sender_score
        reasons.extend(sender_reasons)
        
        # 4. Check for suspicious patterns
        pattern_score, pattern_reasons = self._check_suspicious_patterns(subject + " " + body)
        score += pattern_score
        reasons.extend(pattern_reasons)
        
        # 5. Check for excessive punctuation
        punctuation_score, punctuation_reasons = self._check_punctuation(subject + " " + body)
        score += punctuation_score
        reasons.extend(punctuation_reasons)
        
        # 6. Check for suspicious URLs
        url_score, url_reasons = self._check_urls(subject + " " + body)
        score += url_score
        reasons.extend(url_reasons)
        
        # 7. Check for legitimate sender (reduces spam score)
        if self._is_legitimate_sender(from_lower):
            score = max(0, score - 2)  # Reduce score for legitimate senders
            reasons.append("Legitimate sender detected - score reduced")
        
        # NEW: Check if sender is legitimate financial service
        if self._is_legitimate_financial_sender(from_lower):
            score = max(0, score - 5)  # Significantly reduce spam score
            reasons.append("Legitimate financial service detected - score reduced")
        
        # NEW: Check for legitimate income-related content
        combined_text = f"{subject_lower} {body_lower}"
        income_keyword_count = sum(1 for keyword in self.legitimate_income_keywords if keyword in combined_text)
        if income_keyword_count > 0:
            score = max(0, score - (income_keyword_count * 2))  # Reduce score for each legitimate keyword
            reasons.append(f"Legitimate income-related content detected ({income_keyword_count} keywords)")
        
        # Determine if spam based on score
        is_spam = score >= self.spam_threshold
        confidence = min(1.0, score / 10.0)  # Normalize confidence to 0-1
        
        return SpamDetectionResult(
            is_spam=is_spam,
            score=score,
            reasons=reasons,
            confidence=confidence
        )
    
    def _check_keywords(self, text: str, context: str) -> Tuple[int, List[str]]:
        """Check for spam keywords in text"""
        score = 0
        reasons = []
        
        for keyword in self.spam_keywords:
            if keyword in text:
                score += 1
                reasons.append(f"Spam keyword '{keyword}' found in {context}")
        
        return score, reasons
    
    def _check_sender_patterns(self, from_address: str) -> Tuple[int, List[str]]:
        """Check for suspicious sender patterns"""
        score = 0
        reasons = []
        
        for pattern in self.suspicious_sender_patterns:
            if re.search(pattern, from_address):
                score += 2
                reasons.append(f"Suspicious sender pattern detected: {pattern}")
        
        return score, reasons
    
    def _check_suspicious_patterns(self, text: str) -> Tuple[int, List[str]]:
        """Check for suspicious text patterns"""
        score = 0
        reasons = []
        
        for pattern in self.suspicious_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Only add score if there are multiple matches (reduce false positives)
                if len(matches) >= 2:
                    score += min(len(matches), 3)  # Cap at 3 points
                    reasons.append(f"Suspicious pattern found: {pattern} ({len(matches)} matches)")
        
        return score, reasons
    
    def _check_punctuation(self, text: str) -> Tuple[int, List[str]]:
        """Check for excessive punctuation"""
        score = 0
        reasons = []
        
        # Check for excessive exclamation marks
        exclamation_count = text.count('!')
        if exclamation_count > 3:
            score += exclamation_count - 3
            reasons.append(f"Excessive exclamation marks: {exclamation_count}")
        
        # Check for excessive question marks
        question_count = text.count('?')
        if question_count > 3:
            score += question_count - 3
            reasons.append(f"Excessive question marks: {question_count}")
        
        # Check for all caps
        if len(text) > 10 and text.isupper():
            score += 3
            reasons.append("Text is in all caps")
        
        return score, reasons
    
    def _check_urls(self, text: str) -> Tuple[int, List[str]]:
        """Check for suspicious URLs"""
        score = 0
        reasons = []
        
        # Find all URLs
        url_pattern = r'http[s]?://[^\s]+'
        urls = re.findall(url_pattern, text)
        
        if urls:
            score += len(urls) * 2  # Each URL adds 2 points
            reasons.append(f"Suspicious URLs found: {len(urls)} URLs")
            
            # Check for suspicious URL patterns
            for url in urls:
                if any(suspicious in url.lower() for suspicious in ['bit.ly', 'tinyurl', 'goo.gl', 't.co']):
                    score += 1
                    reasons.append(f"Shortened URL detected: {url}")
        
        return score, reasons
    
    def _is_legitimate_sender(self, from_address: str) -> bool:
        """Check if sender appears to be legitimate"""
        # Extract domain
        if '@' in from_address:
            domain = from_address.split('@')[1]
            
            # Check against legitimate domains
            for legit_domain in self.legitimate_domains:
                if legit_domain in domain:
                    return True
            
            # Check for business-like domains (not random strings)
            if '.' in domain and len(domain.split('.')[0]) > 3:
                return True
        
        return False
    
    def _is_legitimate_financial_sender(self, from_address: str) -> bool:
        """Check if sender is a known legitimate financial service"""
        if '@' in from_address:
            domain = from_address.split('@')[1]
            for legit_domain in self.legitimate_financial_domains:
                if legit_domain in domain:
                    return True
        return False

# Global spam detector instance
spam_detector = SpamDetector()

def detect_email_spam(subject: str, body: str, from_address: str, to_address: str) -> SpamDetectionResult:
    """
    Convenience function to detect spam in an email
    
    Args:
        subject: Email subject line
        body: Email body content
        from_address: Sender email address
        to_address: Recipient email address
        
    Returns:
        SpamDetectionResult with detection details
    """
    return spam_detector.detect_spam(subject, body, from_address, to_address)
