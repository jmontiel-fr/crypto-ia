"""
Tests for input validation and sanitization system.
"""

import pytest
import re
from datetime import datetime

from src.api.validation.input_validator import (
    InputValidator,
    ValidationError,
    ValidationResult,
    validate_request_data,
    required_string,
    optional_string,
    required_integer,
    optional_integer,
    required_choice,
    optional_choice
)


class TestInputValidator:
    """Test cases for InputValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create InputValidator instance."""
        return InputValidator()
    
    def test_validate_string_success(self, validator):
        """Test successful string validation."""
        result = validator.validate_string('test_field', 'hello world', min_length=5, max_length=20)
        assert result == 'hello world'
    
    def test_validate_string_required_missing(self, validator):
        """Test string validation with missing required field."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_string('test_field', None, required=True)
        
        assert exc_info.value.field == 'test_field'
        assert exc_info.value.code == 'REQUIRED'
    
    def test_validate_string_too_short(self, validator):
        """Test string validation with too short value."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_string('test_field', 'hi', min_length=5)
        
        assert exc_info.value.code == 'TOO_SHORT'
    
    def test_validate_string_too_long(self, validator):
        """Test string validation with too long value."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_string('test_field', 'a' * 1001, max_length=1000)
        
        assert exc_info.value.code == 'TOO_LONG'
    
    def test_validate_string_pattern_match(self, validator):
        """Test string validation with pattern matching."""
        pattern = re.compile(r'^[A-Z]{3}$')
        result = validator.validate_string('test_field', 'ABC', pattern=pattern)
        assert result == 'ABC'
    
    def test_validate_string_pattern_no_match(self, validator):
        """Test string validation with pattern not matching."""
        pattern = re.compile(r'^[A-Z]{3}$')
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_string('test_field', 'abc', pattern=pattern)
        
        assert exc_info.value.code == 'INVALID_FORMAT'
    
    def test_validate_string_xss_sanitization(self, validator):
        """Test XSS sanitization in string validation."""
        malicious_input = '<script>alert("xss")</script>Hello'
        result = validator.validate_string('test_field', malicious_input)
        
        # Should not contain script tags
        assert '<script>' not in result
        assert 'alert' not in result
        assert 'Hello' in result
    
    def test_validate_string_sql_injection_detection(self, validator):
        """Test SQL injection detection."""
        malicious_input = "'; DROP TABLE users; --"
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_string('test_field', malicious_input)
        
        assert exc_info.value.code == 'INVALID_CHARS'
    
    def test_validate_integer_success(self, validator):
        """Test successful integer validation."""
        result = validator.validate_integer('test_field', '42', min_value=0, max_value=100)
        assert result == 42
    
    def test_validate_integer_string_input(self, validator):
        """Test integer validation with string input."""
        result = validator.validate_integer('test_field', '123')
        assert result == 123
    
    def test_validate_integer_invalid_type(self, validator):
        """Test integer validation with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer('test_field', 'not_a_number')
        
        assert exc_info.value.code == 'INVALID_TYPE'
    
    def test_validate_integer_too_small(self, validator):
        """Test integer validation with too small value."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer('test_field', 5, min_value=10)
        
        assert exc_info.value.code == 'TOO_SMALL'
    
    def test_validate_integer_too_large(self, validator):
        """Test integer validation with too large value."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_integer('test_field', 150, max_value=100)
        
        assert exc_info.value.code == 'TOO_LARGE'
    
    def test_validate_float_success(self, validator):
        """Test successful float validation."""
        result = validator.validate_float('test_field', '3.14', min_value=0.0, max_value=10.0)
        assert result == 3.14
    
    def test_validate_float_invalid_type(self, validator):
        """Test float validation with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_float('test_field', 'not_a_number')
        
        assert exc_info.value.code == 'INVALID_TYPE'
    
    def test_validate_boolean_true_values(self, validator):
        """Test boolean validation with true values."""
        true_values = ['true', 'True', '1', 'yes', 'on', True, 1]
        
        for value in true_values:
            result = validator.validate_boolean('test_field', value)
            assert result is True
    
    def test_validate_boolean_false_values(self, validator):
        """Test boolean validation with false values."""
        false_values = ['false', 'False', '0', 'no', 'off', False, 0]
        
        for value in false_values:
            result = validator.validate_boolean('test_field', value)
            assert result is False
    
    def test_validate_boolean_invalid(self, validator):
        """Test boolean validation with invalid value."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_boolean('test_field', 'maybe')
        
        assert exc_info.value.code == 'INVALID_TYPE'
    
    def test_validate_email_success(self, validator):
        """Test successful email validation."""
        result = validator.validate_email('test_field', 'user@example.com')
        assert result == 'user@example.com'
    
    def test_validate_email_invalid_format(self, validator):
        """Test email validation with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_email('test_field', 'invalid_email')
        
        assert exc_info.value.code == 'INVALID_EMAIL'
    
    def test_validate_phone_success(self, validator):
        """Test successful phone validation."""
        result = validator.validate_phone('test_field', '+1234567890')
        assert result == '+1234567890'
    
    def test_validate_phone_with_formatting(self, validator):
        """Test phone validation with formatting characters."""
        result = validator.validate_phone('test_field', '(123) 456-7890')
        assert result == '1234567890'
    
    def test_validate_phone_invalid_format(self, validator):
        """Test phone validation with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_phone('test_field', '123')
        
        assert exc_info.value.code == 'INVALID_PHONE'
    
    def test_validate_crypto_symbol_success(self, validator):
        """Test successful crypto symbol validation."""
        result = validator.validate_crypto_symbol('test_field', 'btc')
        assert result == 'BTC'
    
    def test_validate_crypto_symbol_invalid(self, validator):
        """Test crypto symbol validation with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_crypto_symbol('test_field', 'bitcoin123')
        
        assert exc_info.value.code == 'INVALID_SYMBOL'
    
    def test_validate_datetime_success(self, validator):
        """Test successful datetime validation."""
        result = validator.validate_datetime('test_field', '2024-01-01')
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
    
    def test_validate_datetime_invalid_format(self, validator):
        """Test datetime validation with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_datetime('test_field', '01/01/2024')
        
        assert exc_info.value.code == 'INVALID_DATE'
    
    def test_validate_choice_success(self, validator):
        """Test successful choice validation."""
        choices = ['red', 'green', 'blue']
        result = validator.validate_choice('test_field', 'red', choices)
        assert result == 'red'
    
    def test_validate_choice_case_insensitive(self, validator):
        """Test choice validation with case insensitive matching."""
        choices = ['Red', 'Green', 'Blue']
        result = validator.validate_choice('test_field', 'red', choices, case_sensitive=False)
        assert result == 'Red'  # Returns original case
    
    def test_validate_choice_invalid(self, validator):
        """Test choice validation with invalid choice."""
        choices = ['red', 'green', 'blue']
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_choice('test_field', 'yellow', choices)
        
        assert exc_info.value.code == 'INVALID_CHOICE'
    
    def test_validate_json_object_success(self, validator):
        """Test successful JSON object validation."""
        json_string = '{"key": "value", "number": 42}'
        result = validator.validate_json_object('test_field', json_string)
        
        assert isinstance(result, dict)
        assert result['key'] == 'value'
        assert result['number'] == 42
    
    def test_validate_json_object_dict_input(self, validator):
        """Test JSON object validation with dict input."""
        dict_input = {'key': 'value'}
        result = validator.validate_json_object('test_field', dict_input)
        assert result == dict_input
    
    def test_validate_json_object_invalid(self, validator):
        """Test JSON object validation with invalid JSON."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_json_object('test_field', '{"invalid": json}')
        
        assert exc_info.value.code == 'INVALID_JSON'


class TestValidationRuleFactories:
    """Test cases for validation rule factories."""
    
    def test_required_string_factory(self):
        """Test required string factory."""
        rule = required_string(min_length=5, max_length=10)
        validator = InputValidator()
        
        # Valid input
        result = rule(validator, 'test_field', 'hello')
        assert result == 'hello'
        
        # Invalid input (too short)
        with pytest.raises(ValidationError):
            rule(validator, 'test_field', 'hi')
    
    def test_optional_string_factory(self):
        """Test optional string factory."""
        rule = optional_string(max_length=10)
        validator = InputValidator()
        
        # Valid input
        result = rule(validator, 'test_field', 'hello')
        assert result == 'hello'
        
        # None input (should be allowed)
        result = rule(validator, 'test_field', None)
        assert result == ""
    
    def test_required_integer_factory(self):
        """Test required integer factory."""
        rule = required_integer(min_value=0, max_value=100)
        validator = InputValidator()
        
        # Valid input
        result = rule(validator, 'test_field', 50)
        assert result == 50
        
        # Invalid input (too large)
        with pytest.raises(ValidationError):
            rule(validator, 'test_field', 150)
    
    def test_required_choice_factory(self):
        """Test required choice factory."""
        rule = required_choice(['red', 'green', 'blue'])
        validator = InputValidator()
        
        # Valid input
        result = rule(validator, 'test_field', 'red')
        assert result == 'red'
        
        # Invalid input
        with pytest.raises(ValidationError):
            rule(validator, 'test_field', 'yellow')


class TestValidateRequestData:
    """Test cases for validate_request_data function."""
    
    def test_validate_request_data_success(self):
        """Test successful request data validation."""
        data = {
            'name': 'John Doe',
            'age': '25',
            'email': 'john@example.com'
        }
        
        rules = {
            'name': required_string(min_length=1, max_length=100),
            'age': required_integer(min_value=0, max_value=150),
            'email': lambda v, f, val: v.validate_email(f, val)
        }
        
        result = validate_request_data(data, rules)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.sanitized_data['name'] == 'John Doe'
        assert result.sanitized_data['age'] == 25
        assert result.sanitized_data['email'] == 'john@example.com'
    
    def test_validate_request_data_with_errors(self):
        """Test request data validation with errors."""
        data = {
            'name': '',  # Too short
            'age': '200',  # Too large
            'email': 'invalid_email'  # Invalid format
        }
        
        rules = {
            'name': required_string(min_length=1, max_length=100),
            'age': required_integer(min_value=0, max_value=150),
            'email': lambda v, f, val: v.validate_email(f, val)
        }
        
        result = validate_request_data(data, rules)
        
        assert result.is_valid is False
        assert len(result.errors) == 3
        
        # Check error fields
        error_fields = [error.field for error in result.errors]
        assert 'name' in error_fields
        assert 'age' in error_fields
        assert 'email' in error_fields
    
    def test_validate_request_data_partial_success(self):
        """Test request data validation with some valid and some invalid fields."""
        data = {
            'name': 'John Doe',  # Valid
            'age': '200',  # Invalid (too large)
            'email': 'john@example.com'  # Valid
        }
        
        rules = {
            'name': required_string(min_length=1, max_length=100),
            'age': required_integer(min_value=0, max_value=150),
            'email': lambda v, f, val: v.validate_email(f, val)
        }
        
        result = validate_request_data(data, rules)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == 'age'
        
        # Valid fields should still be in sanitized data
        assert result.sanitized_data['name'] == 'John Doe'
        assert result.sanitized_data['email'] == 'john@example.com'


if __name__ == '__main__':
    pytest.main([__file__])