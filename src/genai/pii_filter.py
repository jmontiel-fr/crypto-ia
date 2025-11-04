"""
PII (Personally Identifiable Information) Filter module.
Detects and sanitizes PII from user input to protect privacy and security.
"""

import re
import logging
from typing import Tuple, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIDetectionResult:
    """Result of PII detection analysis."""
    contains_pii: bool
    patterns_detected: List[str]
    sanitized_text: str


class PIIFilter:
    """
    PII detection and filtering class.
    Uses regex patterns and NER to detect personally identifiable information.
    """
    
    def __init__(self):
        """Initialize PII filter with detection patterns."""
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        )
        
        # Phone number patterns (various formats)
        self.phone_patterns = [
            # US format: (123) 456-7890, 123-456-7890, 123.456.7890
            re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            # International format: +1-123-456-7890, +44 20 1234 5678
            re.compile(r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'),
            # Simple 10-digit: 1234567890
            re.compile(r'\b\d{10}\b'),
        ]
        
        # Credit card pattern (basic - 13-19 digits with optional spaces/dashes)
        self.credit_card_pattern = re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4,7}\b'
        )
        
        # SSN pattern (US): 123-45-6789
        self.ssn_pattern = re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        )
        
        # Bank account pattern (simple - 8-17 digits)
        self.bank_account_pattern = re.compile(
            r'\b\d{8,17}\b'
        )
        
        # Street address pattern (basic)
        self.address_pattern = re.compile(
            r'\b\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way)\b',
            re.IGNORECASE
        )
        
        # IP address pattern (IPv4)
        self.ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        )
        
        # URL with personal domains
        self.personal_url_pattern = re.compile(
            r'https?://(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?',
            re.IGNORECASE
        )
        
        # Names pattern (basic - capitalized words that might be names)
        # This is a simple heuristic and will be enhanced with spaCy NER
        self.name_pattern = re.compile(
            r'\b(?:my name is|i am|i\'m|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            re.IGNORECASE
        )
        
        # Try to load spaCy model for NER
        self.nlp = None
        try:
            import spacy
            # Try to load the model
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy NER model loaded successfully")
            except OSError:
                logger.warning(
                    "spaCy model 'en_core_web_sm' not found. "
                    "Install with: python -m spacy download en_core_web_sm"
                )
        except ImportError:
            logger.warning("spaCy not installed. NER-based name detection will be disabled.")
    
    def contains_pii(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains PII.
        
        Args:
            text: Text to analyze.
        
        Returns:
            Tuple of (contains_pii, list of detected PII types).
        """
        if not text or not text.strip():
            return False, []
        
        detected_patterns = []
        
        # Check for email
        if self.email_pattern.search(text):
            detected_patterns.append('email')
        
        # Check for phone numbers
        for phone_pattern in self.phone_patterns:
            if phone_pattern.search(text):
                detected_patterns.append('phone')
                break
        
        # Check for credit card
        if self.credit_card_pattern.search(text):
            detected_patterns.append('credit_card')
        
        # Check for SSN
        if self.ssn_pattern.search(text):
            detected_patterns.append('ssn')
        
        # Check for bank account (be careful with false positives)
        # Only flag if it's not part of a crypto address or other numeric data
        bank_matches = self.bank_account_pattern.findall(text)
        if bank_matches:
            # Filter out common false positives (crypto amounts, timestamps, etc.)
            for match in bank_matches:
                # If it's a standalone long number, it might be a bank account
                if len(match) >= 10 and not any(word in text.lower() for word in ['btc', 'eth', 'price', 'volume', 'market']):
                    detected_patterns.append('bank_account')
                    break
        
        # Check for street address
        if self.address_pattern.search(text):
            detected_patterns.append('address')
        
        # Check for IP address (might be personal)
        if self.ip_pattern.search(text):
            # Only flag if it's not a common public IP range
            ip_matches = self.ip_pattern.findall(text)
            for ip in ip_matches:
                # Skip common public IPs like 8.8.8.8, 1.1.1.1
                if ip not in ['8.8.8.8', '1.1.1.1', '0.0.0.0', '127.0.0.1']:
                    detected_patterns.append('ip_address')
                    break
        
        # Check for personal URLs (social media, personal websites)
        if self.personal_url_pattern.search(text):
            url_matches = self.personal_url_pattern.findall(text)
            for url in url_matches:
                # Flag if it contains personal identifiers
                if any(word in url.lower() for word in ['facebook', 'linkedin', 'twitter', 'instagram', 'profile', 'user']):
                    detected_patterns.append('personal_url')
                    break
        
        # Check for names using pattern matching
        if self.name_pattern.search(text):
            detected_patterns.append('name')
        
        # Check for names using spaCy NER
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == 'PERSON':
                        detected_patterns.append('name')
                        break
            except Exception as e:
                logger.warning(f"spaCy NER failed: {e}")
        
        # Remove duplicates
        detected_patterns = list(set(detected_patterns))
        
        return len(detected_patterns) > 0, detected_patterns
    
    def sanitize_text(self, text: str) -> str:
        """
        Remove detected PII from text.
        
        Args:
            text: Text to sanitize.
        
        Returns:
            Sanitized text with PII replaced by placeholders.
        """
        if not text or not text.strip():
            return text
        
        sanitized = text
        
        # Replace email
        sanitized = self.email_pattern.sub('[EMAIL]', sanitized)
        
        # Replace phone numbers
        for phone_pattern in self.phone_patterns:
            sanitized = phone_pattern.sub('[PHONE]', sanitized)
        
        # Replace credit card
        sanitized = self.credit_card_pattern.sub('[CREDIT_CARD]', sanitized)
        
        # Replace SSN
        sanitized = self.ssn_pattern.sub('[SSN]', sanitized)
        
        # Replace bank account (with same filtering as detection)
        bank_matches = self.bank_account_pattern.findall(sanitized)
        for match in bank_matches:
            if len(match) >= 10 and not any(word in sanitized.lower() for word in ['btc', 'eth', 'price', 'volume', 'market']):
                sanitized = sanitized.replace(match, '[BANK_ACCOUNT]')
        
        # Replace street address
        sanitized = self.address_pattern.sub('[ADDRESS]', sanitized)
        
        # Replace IP address (with same filtering as detection)
        ip_matches = self.ip_pattern.findall(sanitized)
        for ip in ip_matches:
            if ip not in ['8.8.8.8', '1.1.1.1', '0.0.0.0', '127.0.0.1']:
                sanitized = sanitized.replace(ip, '[IP_ADDRESS]')
        
        # Replace personal URLs
        url_matches = self.personal_url_pattern.findall(sanitized)
        for url in url_matches:
            if any(word in url.lower() for word in ['facebook', 'linkedin', 'twitter', 'instagram', 'profile', 'user']):
                sanitized = sanitized.replace(url, '[PERSONAL_URL]')
        
        # Replace names using pattern matching
        name_matches = self.name_pattern.finditer(sanitized)
        for match in name_matches:
            name = match.group(1)
            sanitized = sanitized.replace(name, '[NAME]')
        
        # Replace names using spaCy NER
        if self.nlp:
            try:
                doc = self.nlp(sanitized)
                for ent in doc.ents:
                    if ent.label_ == 'PERSON':
                        sanitized = sanitized.replace(ent.text, '[NAME]')
            except Exception as e:
                logger.warning(f"spaCy NER sanitization failed: {e}")
        
        return sanitized
    
    def analyze(self, text: str) -> PIIDetectionResult:
        """
        Analyze text for PII and return comprehensive result.
        
        Args:
            text: Text to analyze.
        
        Returns:
            PIIDetectionResult with detection status, patterns, and sanitized text.
        """
        contains_pii, patterns = self.contains_pii(text)
        sanitized = self.sanitize_text(text) if contains_pii else text
        
        return PIIDetectionResult(
            contains_pii=contains_pii,
            patterns_detected=patterns,
            sanitized_text=sanitized
        )
