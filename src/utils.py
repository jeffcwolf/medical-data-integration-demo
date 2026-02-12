#!/usr/bin/env python3
"""
Utility Functions - Medical Data Integration Pipeline

Helper functions for data normalization and cleaning.
Used by both the validator and transformer modules.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import re
from datetime import datetime
from typing import Optional


def clean_patient_id(id_value: str) -> str:
    """
    Normalize patient ID to consistent format.

    Handles variations like:
    - "P-00001" → "00001"
    - "PAT00001" → "00001"
    - "WP1-00001" → "00001"
    - "Polar-WP1.1-00001" → "00001"

    Args:
        id_value: Raw patient ID from source system

    Returns:
        Normalized patient ID (5-digit number)
    """
    if not id_value:
        return ""

    # Extract numeric portion
    numbers = re.findall(r'\d+', id_value)
    if numbers:
        # Get the last number (typically the patient sequence)
        number = numbers[-1]
        # Ensure 5 digits with zero padding
        return number.zfill(5)

    return id_value  # Return as-is if no numbers found


def normalize_date(date_value: str) -> Optional[str]:
    """
    Convert various date formats to ISO format (YYYY-MM-DD).

    Handles formats:
    - DD.MM.YYYY (German)
    - DD-MM-YYYY
    - YYYY/MM/DD
    - YYYY-MM-DD (ISO - pass through)
    - ISO datetime with timezone

    Args:
        date_value: Raw date string

    Returns:
        ISO date string (YYYY-MM-DD) or None if invalid
    """
    if not date_value or date_value.strip() == "":
        return None

    # Remove timezone info if present (e.g., "2019-01-01T00:00:00+01:00")
    date_value = date_value.split('T')[0]

    # Try different formats
    formats = [
        ('%Y-%m-%d', r'^\d{4}-\d{2}-\d{2}$'),          # ISO: 2019-01-01
        ('%d.%m.%Y', r'^\d{2}\.\d{2}\.\d{4}$'),        # German: 01.01.2019
        ('%Y/%m/%d', r'^\d{4}/\d{2}/\d{2}$'),          # Slash: 2019/01/01
        ('%d-%m-%Y', r'^\d{2}-\d{2}-\d{4}$'),          # Reverse: 01-01-2019
        ('%d/%m/%Y', r'^\d{2}/\d{2}/\d{4}$'),          # German slash: 01/01/2019
    ]

    for date_format, pattern in formats:
        if re.match(pattern, date_value):
            try:
                dt = datetime.strptime(date_value, date_format)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

    # If no format matched, return None
    return None


def normalize_gender(gender_value: str) -> str:
    """
    Normalize gender to FHIR standard values.

    Maps variations to FHIR valueSet:
    - male, female, other, unknown

    Args:
        gender_value: Raw gender value

    Returns:
        FHIR gender value (male|female|other|unknown)
    """
    if not gender_value or gender_value.strip() == "":
        return "unknown"

    gender_lower = gender_value.lower().strip()

    # Male variations
    male_values = ['m', 'male', 'männlich', 'mann', 'man']
    if gender_lower in male_values:
        return "male"

    # Female variations
    female_values = ['f', 'w', 'female', 'weiblich', 'frau', 'woman', 'fe']
    if gender_lower in female_values:
        return "female"

    # Other/diverse
    other_values = ['d', 'divers', 'diverse', 'other', 'x']
    if gender_lower in other_values:
        return "other"

    # Default to unknown for unrecognized values
    return "unknown"


def normalize_code_system(system_value: str) -> str:
    """
    Normalize coding system URIs to standard format.

    Args:
        system_value: Raw coding system URI

    Returns:
        Normalized system URI
    """
    if not system_value:
        return ""

    # Common variations
    if 'icd-10-gm' in system_value.lower():
        return "http://fhir.de/CodeSystem/bfarm/icd-10-gm"

    if 'atc' in system_value.lower():
        return "http://fhir.de/CodeSystem/bfarm/atc"

    if 'loinc' in system_value.lower():
        return "http://loinc.org"

    # Return as-is if no match
    return system_value


def validate_date_range(date_str: Optional[str],
                        min_year: int = 1900,
                        max_year: int = 2030) -> bool:
    """
    Check if date is within reasonable range.

    Args:
        date_str: ISO date string (YYYY-MM-DD)
        min_year: Minimum valid year
        max_year: Maximum valid year

    Returns:
        True if date is valid and in range
    """
    if not date_str:
        return False

    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return min_year <= dt.year <= max_year
    except ValueError:
        return False


def clean_string(value: str) -> str:
    """
    Clean string value: trim whitespace, handle empty strings.

    Args:
        value: Raw string value

    Returns:
        Cleaned string or empty string
    """
    if not value or not isinstance(value, str):
        return ""

    cleaned = value.strip()
    return cleaned if cleaned else ""


def is_valid_icd10_code(code: str) -> bool:
    """
    Basic validation for ICD-10-GM code format.

    ICD-10-GM codes follow pattern: Letter + 2 digits + optional dot + more digits/letters
    Examples: M80.00, S02.0, E11.9

    Args:
        code: ICD-10 code to validate

    Returns:
        True if code matches basic ICD-10 pattern
    """
    if not code:
        return False

    # Basic pattern: Letter, 2-3 digits, optional dot and more chars
    pattern = r'^[A-Z]\d{2}\.?\d*[A-Z]?$'
    return bool(re.match(pattern, code.upper()))


def is_valid_atc_code(code: str) -> bool:
    """
    Basic validation for ATC code format.

    ATC codes follow pattern: Letter + 2 digits + 2 letters + 2 digits
    Examples: N06AA09, M05BA01

    Args:
        code: ATC code to validate

    Returns:
        True if code matches basic ATC pattern
    """
    if not code:
        return False

    # ATC pattern: 1 letter, 2 digits, 2 letters, 2 digits
    pattern = r'^[A-Z]\d{2}[A-Z]{2}\d{2}$'
    return bool(re.match(pattern, code.upper()))


def format_fhir_identifier(system: str, value: str) -> dict:
    """
    Create FHIR Identifier object.

    Args:
        system: Identifier system URI
        value: Identifier value

    Returns:
        Dict representing FHIR Identifier
    """
    return {
        "system": system,
        "value": value
    }


def format_fhir_codeable_concept(system: str,
                                  code: str,
                                  display: Optional[str] = None) -> dict:
    """
    Create FHIR CodeableConcept object.

    Args:
        system: Coding system URI
        code: Code value
        display: Optional display text

    Returns:
        Dict representing FHIR CodeableConcept
    """
    coding = {
        "system": system,
        "code": code
    }

    if display:
        coding["display"] = display

    result = {
        "coding": [coding]
    }

    if display:
        result["text"] = display

    return result


def extract_reference_id(reference: str) -> Optional[str]:
    """
    Extract ID from FHIR reference string.

    Examples:
    - "Patient/00001" → "00001"
    - "Encounter/E-123" → "E-123"

    Args:
        reference: FHIR reference string

    Returns:
        Extracted ID or None
    """
    if not reference:
        return None

    if '/' in reference:
        return reference.split('/')[-1]

    return reference


def safe_int(value: str, default: int = 0) -> int:
    """
    Safely convert string to integer.

    Args:
        value: String to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default
    """
    if not value:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: str, default: float = 0.0) -> float:
    """
    Safely convert string to float.

    Args:
        value: String to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    if not value:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default
