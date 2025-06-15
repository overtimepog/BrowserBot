"""
Input validation and sanitization for BrowserBot.
"""

import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from ..core.logger import get_logger
from ..core.errors import ValidationError, ErrorSeverity, ErrorCategory, ErrorContext

logger = get_logger(__name__)


class ValidationType(Enum):
    """Types of validation."""
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SCRIPT_TAG = "script_tag"
    HTML_TAG = "html_tag"


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    sanitized_value: Any
    violations: List[str]
    risk_level: str  # "low", "medium", "high", "critical"


class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|;|\*|\/\*|\*\/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<applet[^>]*>",
        r"<meta[^>]*>",
        r"<link[^>]*>",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\b(rm|del|format|mkfs|fdisk)\b",
        r"(wget|curl|nc|netcat)",
        r"(exec|eval|system|shell_exec)",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e\\",
        r"..%2f",
        r"..%5c",
    ]
    
    # Safe patterns
    URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$", re.IGNORECASE
    )
    
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    
    PHONE_PATTERN = re.compile(
        r"^[\+]?[\d\s\-\(\)]+$"
    )
    
    def __init__(self):
        self.validation_rules: Dict[str, List[ValidationType]] = {}
        self.custom_validators: Dict[str, callable] = {}
    
    def validate(
        self,
        value: Any,
        validation_types: List[ValidationType],
        field_name: str = "input",
        strict: bool = False
    ) -> ValidationResult:
        """
        Validate input against specified validation types.
        
        Args:
            value: Value to validate
            validation_types: List of validation types to apply
            field_name: Name of the field for logging
            strict: Whether to use strict validation
            
        Returns:
            ValidationResult with validation outcome
        """
        violations = []
        sanitized_value = value
        risk_level = "low"
        
        # Convert to string for pattern matching
        str_value = str(value) if value is not None else ""
        
        for validation_type in validation_types:
            result = self._apply_validation(str_value, validation_type, strict)
            
            if not result.is_valid:
                violations.extend(result.violations)
                risk_level = self._escalate_risk(risk_level, result.risk_level)
            
            # Use the most sanitized version
            if result.sanitized_value != str_value:
                sanitized_value = result.sanitized_value
        
        is_valid = len(violations) == 0
        
        # Log validation results
        if not is_valid:
            logger.warning(
                "Input validation failed",
                field=field_name,
                violations=violations,
                risk_level=risk_level,
                original_length=len(str_value),
                sanitized_length=len(str(sanitized_value))
            )
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=sanitized_value,
            violations=violations,
            risk_level=risk_level
        )
    
    def _apply_validation(
        self,
        value: str,
        validation_type: ValidationType,
        strict: bool
    ) -> ValidationResult:
        """Apply specific validation type."""
        violations = []
        sanitized_value = value
        risk_level = "low"
        
        if validation_type == ValidationType.URL:
            if not self._validate_url(value):
                violations.append("Invalid URL format")
                risk_level = "medium"
            sanitized_value = self._sanitize_url(value)
            
        elif validation_type == ValidationType.EMAIL:
            if not self._validate_email(value):
                violations.append("Invalid email format")
                risk_level = "low"
            sanitized_value = self._sanitize_email(value)
            
        elif validation_type == ValidationType.PHONE:
            if not self._validate_phone(value):
                violations.append("Invalid phone format")
                risk_level = "low"
            sanitized_value = self._sanitize_phone(value)
            
        elif validation_type == ValidationType.CREDIT_CARD:
            if self._detect_credit_card(value):
                violations.append("Potential credit card number detected")
                risk_level = "critical"
                sanitized_value = "[REDACTED]"
            
        elif validation_type == ValidationType.SQL_INJECTION:
            if self._detect_sql_injection(value):
                violations.append("Potential SQL injection detected")
                risk_level = "critical"
            sanitized_value = self._sanitize_sql(value)
            
        elif validation_type == ValidationType.XSS:
            if self._detect_xss(value):
                violations.append("Potential XSS attack detected")
                risk_level = "high"
            sanitized_value = self._sanitize_xss(value)
            
        elif validation_type == ValidationType.COMMAND_INJECTION:
            if self._detect_command_injection(value):
                violations.append("Potential command injection detected")
                risk_level = "critical"
            sanitized_value = self._sanitize_command_injection(value)
            
        elif validation_type == ValidationType.PATH_TRAVERSAL:
            if self._detect_path_traversal(value):
                violations.append("Potential path traversal detected")
                risk_level = "high"
            sanitized_value = self._sanitize_path_traversal(value)
            
        elif validation_type == ValidationType.SCRIPT_TAG:
            if self._detect_script_tags(value):
                violations.append("Script tags detected")
                risk_level = "high"
            sanitized_value = self._remove_script_tags(value)
            
        elif validation_type == ValidationType.HTML_TAG:
            sanitized_value = self._sanitize_html(value)
        
        is_valid = len(violations) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=sanitized_value,
            violations=violations,
            risk_level=risk_level
        )
    
    def _validate_url(self, value: str) -> bool:
        """Validate URL format."""
        return bool(self.URL_PATTERN.match(value))
    
    def _validate_email(self, value: str) -> bool:
        """Validate email format."""
        return bool(self.EMAIL_PATTERN.match(value))
    
    def _validate_phone(self, value: str) -> bool:
        """Validate phone format."""
        return bool(self.PHONE_PATTERN.match(value))
    
    def _detect_credit_card(self, value: str) -> bool:
        """Detect potential credit card numbers."""
        # Remove common separators
        cleaned = re.sub(r"[\s\-]", "", value)
        
        # Check for 13-19 digit sequences
        if re.match(r"^\d{13,19}$", cleaned):
            # Luhn algorithm check
            return self._luhn_check(cleaned)
        
        return False
    
    def _luhn_check(self, card_number: str) -> bool:
        """Perform Luhn algorithm check."""
        digits = [int(d) for d in card_number]
        checksum = 0
        
        for i in range(len(digits) - 2, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        
        return sum(digits) % 10 == 0
    
    def _detect_sql_injection(self, value: str) -> bool:
        """Detect SQL injection patterns."""
        value_lower = value.lower()
        
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_xss(self, value: str) -> bool:
        """Detect XSS patterns."""
        value_lower = value.lower()
        
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_command_injection(self, value: str) -> bool:
        """Detect command injection patterns."""
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_path_traversal(self, value: str) -> bool:
        """Detect path traversal patterns."""
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_script_tags(self, value: str) -> bool:
        """Detect script tags."""
        return bool(re.search(r"<script[^>]*>", value, re.IGNORECASE))
    
    def _sanitize_url(self, value: str) -> str:
        """Sanitize URL."""
        # URL encode and validate scheme
        parsed = urllib.parse.urlparse(value)
        
        if parsed.scheme not in ("http", "https"):
            return ""
        
        return urllib.parse.urlunparse(parsed)
    
    def _sanitize_email(self, value: str) -> str:
        """Sanitize email."""
        # Basic email sanitization
        return value.strip().lower()
    
    def _sanitize_phone(self, value: str) -> str:
        """Sanitize phone number."""
        # Keep only digits, spaces, dashes, parentheses, and plus
        return re.sub(r"[^\d\s\-\(\)\+]", "", value)
    
    def _sanitize_sql(self, value: str) -> str:
        """Sanitize against SQL injection."""
        # Escape single quotes and remove SQL keywords
        sanitized = value.replace("'", "''")
        
        # Remove dangerous SQL keywords
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER"]
        for keyword in sql_keywords:
            sanitized = re.sub(rf"\b{keyword}\b", "", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def _sanitize_xss(self, value: str) -> str:
        """Sanitize against XSS."""
        # HTML escape
        sanitized = html.escape(value)
        
        # Remove javascript: URLs
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        
        # Remove event handlers
        sanitized = re.sub(r"on\w+\s*=\s*[\"'][^\"']*[\"']", "", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def _sanitize_command_injection(self, value: str) -> str:
        """Sanitize against command injection."""
        # Remove dangerous characters
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
        sanitized = value
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        
        return sanitized
    
    def _sanitize_path_traversal(self, value: str) -> str:
        """Sanitize against path traversal."""
        # Remove path traversal sequences
        sanitized = value.replace("../", "").replace("..\\", "")
        sanitized = urllib.parse.unquote(sanitized)
        sanitized = sanitized.replace("../", "").replace("..\\", "")
        
        return sanitized
    
    def _remove_script_tags(self, value: str) -> str:
        """Remove script tags."""
        return re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    
    def _sanitize_html(self, value: str) -> str:
        """Sanitize HTML content."""
        # HTML escape all content
        return html.escape(value)
    
    def _escalate_risk(self, current_risk: str, new_risk: str) -> str:
        """Escalate risk level."""
        risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        
        current_level = risk_levels.get(current_risk, 1)
        new_level = risk_levels.get(new_risk, 1)
        
        max_level = max(current_level, new_level)
        
        for risk, level in risk_levels.items():
            if level == max_level:
                return risk
        
        return "low"
    
    def validate_dict(
        self,
        data: Dict[str, Any],
        validation_rules: Dict[str, List[ValidationType]],
        strict: bool = False
    ) -> Dict[str, ValidationResult]:
        """Validate dictionary of values."""
        results = {}
        
        for field_name, value in data.items():
            if field_name in validation_rules:
                results[field_name] = self.validate(
                    value=value,
                    validation_types=validation_rules[field_name],
                    field_name=field_name,
                    strict=strict
                )
        
        return results
    
    def register_custom_validator(
        self,
        name: str,
        validator_func: callable
    ) -> None:
        """Register custom validator function."""
        self.custom_validators[name] = validator_func
        logger.info(f"Custom validator registered: {name}")
    
    def get_sanitized_data(
        self,
        data: Dict[str, Any],
        validation_rules: Dict[str, List[ValidationType]]
    ) -> Dict[str, Any]:
        """Get sanitized version of data."""
        results = self.validate_dict(data, validation_rules)
        
        sanitized_data = {}
        for field_name, result in results.items():
            sanitized_data[field_name] = result.sanitized_value
        
        return sanitized_data
    
    def has_high_risk_violations(
        self,
        results: Dict[str, ValidationResult]
    ) -> bool:
        """Check if any validation results have high risk violations."""
        high_risk_levels = {"high", "critical"}
        
        return any(
            result.risk_level in high_risk_levels
            for result in results.values()
            if not result.is_valid
        )


# Global validator instance
_validator_instance: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get global validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = InputValidator()
    return _validator_instance


def validate_user_input(
    data: Dict[str, Any],
    validation_rules: Optional[Dict[str, List[ValidationType]]] = None
) -> Dict[str, Any]:
    """
    Validate and sanitize user input.
    
    Args:
        data: Input data to validate
        validation_rules: Validation rules per field
        
    Returns:
        Sanitized data
        
    Raises:
        ValidationError: If high-risk violations are found
    """
    validator = get_validator()
    
    # Default validation rules
    if validation_rules is None:
        validation_rules = {
            field_name: [ValidationType.XSS, ValidationType.SQL_INJECTION]
            for field_name in data.keys()
        }
    
    # Validate data
    results = validator.validate_dict(data, validation_rules)
    
    # Check for high-risk violations
    if validator.has_high_risk_violations(results):
        violations = []
        for field_name, result in results.items():
            if not result.is_valid and result.risk_level in ("high", "critical"):
                violations.extend([f"{field_name}: {v}" for v in result.violations])
        
        raise ValidationError(
            message=f"High-risk input violations detected: {', '.join(violations)}",
            context=ErrorContext(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.SECURITY,
                metadata={"violations": violations}
            )
        )
    
    # Return sanitized data
    return validator.get_sanitized_data(data, validation_rules)