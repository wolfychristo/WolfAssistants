"""Email content validation to prevent spam triggers"""
import re
import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

# Common spam trigger words and phrases that should be avoided
SPAM_TRIGGER_WORDS = [
    # Urgency and pressure tactics
    'act now', 'limited time', 'expires today', 'deadline', 'urgent', 'immediately',
    'don\'t miss', 'once in a lifetime', 'exclusive offer', 'limited offer',
    'buy now', 'order now', 'call now', 'click here now',
    
    # Financial spam triggers
    'free money', 'get rich quick', 'make money fast', 'easy money',
    'guaranteed income', 'risk-free', 'no risk', 'guaranteed profit',
    'work from home', 'earn cash', 'investment opportunity',
    
    # Suspicious phrases
    'click here', 'free gift', 'special offer', 'you have won', 'claim your prize',
    'congratulations', 'winner', 'prize', 'lottery',
    
    # Excessive punctuation patterns
    '!!!', '???', '$$$', '%%%',
    
    # ALL CAPS words (more than 3 consecutive capital letters)
    # This will be checked separately
    
    # Suspicious links
    'bit.ly', 'tinyurl', 'short.link',
]

# Words that are acceptable in context but should be used carefully
CAUTION_WORDS = [
    'free', 'guarantee', 'guaranteed', 'discount', 'save', 'sale',
    'offer', 'special', 'limited', 'new', 'now'
]

def validate_email_content(subject: str, body: str) -> Tuple[bool, List[str], Dict[str, int]]:
    """
    Enhanced validation for 99.9% deliverability - stricter spam detection.
    
    Returns:
        (is_valid, warnings, score_details)
        - is_valid: True if content is safe, False if high spam risk
        - warnings: List of warning messages about potential issues
        - score_details: Dictionary with score breakdown
    """
    warnings = []
    score_details = {
        'spam_trigger_count': 0,
        'caution_word_count': 0,
        'excessive_caps': 0,
        'excessive_punctuation': 0,
        'suspicious_link_count': 0,
        'subject_length_issue': 0,
        'body_length_issue': 0,
        'link_ratio_issue': 0,
        'total_score': 0
    }
    
    subject = subject or ""
    body = body or ""
    subject_lower = subject.lower()
    body_lower = body.lower()
    combined = f"{subject} {body}".lower()
    
    # ENHANCED: Subject line validation for 99.9% deliverability
    # Subject should be 30-100 characters for optimal deliverability
    if len(subject) < 10:
        score_details['subject_length_issue'] = 2
        warnings.append("Subject line is too short (minimum 10 characters recommended)")
    elif len(subject) > 100:
        score_details['subject_length_issue'] = 2
        warnings.append("Subject line is too long (maximum 100 characters recommended)")
    
    # ENHANCED: Body length validation
    # Body should have sufficient content (at least 50 characters)
    if len(body.strip()) < 50:
        score_details['body_length_issue'] = 3
        warnings.append("Email body is too short - may trigger spam filters")
    elif len(body.strip()) > 50000:  # Very long emails can trigger spam
        score_details['body_length_issue'] = 1
        warnings.append("Email body is very long - consider breaking into multiple emails")
    
    # Check for spam trigger words
    for trigger in SPAM_TRIGGER_WORDS:
        count = combined.count(trigger.lower())
        if count > 0:
            score_details['spam_trigger_count'] += count
            warnings.append(f"Spam trigger phrase found: '{trigger}'")
    
    # ENHANCED: Stricter caution word checking
    for word in CAUTION_WORDS:
        count = combined.count(word.lower())
        if count > 1:  # More than 1 occurrence is suspicious for 99.9% deliverability
            score_details['caution_word_count'] += count - 1
            warnings.append(f"Caution word used multiple times: '{word}' ({count} times)")
    
    # ENHANCED: Check for excessive capitalization (more than 2 consecutive caps)
    caps_pattern = r'\b[A-Z]{3,}\b'
    caps_matches = len(re.findall(caps_pattern, subject + " " + body))
    if caps_matches > 0:
        score_details['excessive_caps'] = caps_matches * 2  # Increased penalty
        warnings.append(f"Excessive capitalization detected ({caps_matches} instances)")
    
    # ENHANCED: Stricter punctuation check
    punctuation_pattern = r'[!?]{2,}|[$%]{2,}'
    punct_matches = len(re.findall(punctuation_pattern, subject + " " + body))
    if punct_matches > 0:
        score_details['excessive_punctuation'] = punct_matches * 2
        warnings.append(f"Excessive punctuation detected ({punct_matches} instances)")
    
    # ENHANCED: Check for suspicious short links and link density
    suspicious_domains = ['bit.ly', 'tinyurl.com', 'short.link', 't.co', 'goo.gl', 'ow.ly']
    link_pattern = r'https?://[^\s]+'
    links = re.findall(link_pattern, combined)
    
    for domain in suspicious_domains:
        if domain in combined:
            score_details['suspicious_link_count'] += 1
            warnings.append(f"Suspicious link shortener detected: {domain}")
    
    # ENHANCED: Check link-to-text ratio (too many links = spam)
    if len(links) > 0:
        text_length = len(body.strip())
        if text_length > 0:
            link_ratio = len(links) / (text_length / 100)  # Links per 100 chars
            if link_ratio > 2:  # More than 2 links per 100 characters
                score_details['link_ratio_issue'] = 3
                warnings.append(f"Too many links in email ({len(links)} links) - may trigger spam filters")
    
    # ENHANCED: Check for common spam patterns
    spam_patterns = [
        r'\$\d+',  # Dollar amounts (can be spam)
        r'\d+% off',  # Percentage discounts
        r'click (here|now|today)',  # Click here variations
        r'(free|guaranteed|risk-free).{0,20}(trial|offer|money)',  # Free offers
    ]
    for pattern in spam_patterns:
        matches = len(re.findall(pattern, combined, re.IGNORECASE))
        if matches > 0:
            score_details['spam_trigger_count'] += matches
            warnings.append(f"Spam pattern detected: {pattern}")
    
    # ENHANCED: Calculate total spam score with stricter thresholds
    # Each spam trigger = 4 points (increased from 3)
    # Each caution word over limit = 2 points (increased from 1)
    # Excessive caps = 3 points per instance (increased from 2)
    # Excessive punctuation = 3 points per instance (increased from 2)
    # Suspicious link = 6 points (increased from 5)
    # Subject/body length issues = as defined above
    # Link ratio issue = 3 points
    total_score = (
        score_details['spam_trigger_count'] * 4 +
        score_details['caution_word_count'] * 2 +
        score_details['excessive_caps'] * 3 +
        score_details['excessive_punctuation'] * 3 +
        score_details['suspicious_link_count'] * 6 +
        score_details['subject_length_issue'] +
        score_details['body_length_issue'] +
        score_details['link_ratio_issue']
    )
    score_details['total_score'] = total_score
    
    # ENHANCED: Stricter validation for 99.9% deliverability
    # Score of 3 or less = safe
    # Score of 4-7 = caution
    # Score above 7 = high spam risk
    is_valid = total_score < 7
    
    if total_score >= 7:
        warnings.insert(0, f"⚠️ HIGH SPAM RISK: Content score is {total_score} (threshold: 7). Revise for 99.9% deliverability.")
    elif total_score >= 4:
        warnings.insert(0, f"⚠️ CAUTION: Content score is {total_score}. Some spam triggers detected. Optimize for better deliverability.")
    
    return is_valid, warnings, score_details

def get_content_suggestions(warnings: List[str], score_details: Dict[str, int]) -> List[str]:
    """Get suggestions to improve email content based on validation results"""
    suggestions = []
    
    if score_details['spam_trigger_count'] > 0:
        suggestions.append("Remove urgency phrases like 'act now', 'limited time', 'urgent'")
        suggestions.append("Avoid financial spam triggers like 'free money', 'get rich quick'")
    
    if score_details['excessive_caps'] > 0:
        suggestions.append("Avoid excessive capitalization - use normal sentence case")
    
    if score_details['excessive_punctuation'] > 0:
        suggestions.append("Use normal punctuation - avoid multiple exclamation marks or question marks")
    
    if score_details['suspicious_link_count'] > 0:
        suggestions.append("Use full URLs instead of link shorteners for better deliverability")
    
    if score_details['caution_word_count'] > 2:
        suggestions.append("Reduce repetition of marketing words like 'free', 'guaranteed', 'special'")
    
    if not suggestions:
        suggestions.append("Content looks good! No major spam triggers detected.")
    
    return suggestions

