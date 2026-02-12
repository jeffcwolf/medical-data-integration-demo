#!/usr/bin/env python3
"""
Data Quality Validator - Medical Data Integration Pipeline

Validates data quality before FHIR transformation.
Checks completeness, consistency, validity, and referential integrity.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

from typing import Dict, List, Set
import pandas as pd
from src.utils import (
    normalize_date,
    normalize_gender,
    is_valid_icd10_code,
    is_valid_atc_code
)


class DataQualityValidator:
    """
    Validates data quality for medical data transformation.

    Performs checks on:
    - Completeness (missing required fields)
    - Consistency (format standardization)
    - Validity (valid codes, dates, values)
    - Referential integrity (ID relationships)
    """

    def __init__(self):
        """Initialize validator with empty results."""
        self.issues: List[Dict] = []
        self.metrics: Dict = {}

    def validate_patient_data(self, df: pd.DataFrame) -> Dict:
        """
        Validate patient data quality.

        Args:
            df: DataFrame with patient data

        Returns:
            Dict with validation results
        """
        results = {
            'total_records': len(df),
            'completeness': {},
            'consistency': {},
            'validity': {},
            'issues': []
        }

        # Completeness checks
        required_fields = ['PatientID']
        important_fields = ['FirstName', 'LastName', 'Birthdate', 'Gender']

        for field in required_fields + important_fields:
            if field in df.columns:
                missing_count = df[field].isna().sum() + (df[field] == '').sum()
                missing_pct = (missing_count / len(df)) * 100

                results['completeness'][field] = {
                    'missing_count': int(missing_count),
                    'missing_percentage': round(missing_pct, 2),
                    'is_critical': field in required_fields
                }

                if field in required_fields and missing_count > 0:
                    results['issues'].append({
                        'severity': 'ERROR',
                        'field': field,
                        'message': f'Required field has {missing_count} missing values'
                    })

        # Consistency checks - Date formats
        if 'Birthdate' in df.columns:
            valid_dates = 0
            invalid_dates = 0

            for date_val in df['Birthdate']:
                if date_val and date_val != '':
                    normalized = normalize_date(str(date_val))
                    if normalized:
                        valid_dates += 1
                    else:
                        invalid_dates += 1

            results['consistency']['Birthdate'] = {
                'valid': valid_dates,
                'invalid': invalid_dates,
                'invalid_percentage': round((invalid_dates / len(df)) * 100, 2)
            }

            if invalid_dates > 0:
                results['issues'].append({
                    'severity': 'WARNING',
                    'field': 'Birthdate',
                    'message': f'{invalid_dates} dates could not be parsed'
                })

        # Consistency checks - Gender values
        if 'Gender' in df.columns:
            gender_values = df[df['Gender'] != '']['Gender'].unique()
            standardized_genders = set()

            for gender in gender_values:
                standardized = normalize_gender(str(gender))
                standardized_genders.add(standardized)

            results['consistency']['Gender'] = {
                'unique_raw_values': len(gender_values),
                'standardized_values': list(standardized_genders),
                'has_variations': len(gender_values) > len(standardized_genders)
            }

        # Validity checks - Duplicate PatientIDs
        if 'PatientID' in df.columns:
            duplicates = df[df['PatientID'] != '']['PatientID'].duplicated().sum()
            results['validity']['duplicates'] = int(duplicates)

            if duplicates > 0:
                results['issues'].append({
                    'severity': 'ERROR',
                    'field': 'PatientID',
                    'message': f'{duplicates} duplicate patient IDs found'
                })

        return results

    def validate_condition_data(self, df: pd.DataFrame) -> Dict:
        """
        Validate condition/diagnosis data quality.

        Args:
            df: DataFrame with condition data

        Returns:
            Dict with validation results
        """
        results = {
            'total_records': len(df),
            'completeness': {},
            'validity': {},
            'issues': []
        }

        # Completeness checks
        required_fields = ['ConditionID', 'PatientID']
        important_fields = ['Code', 'CodeSystem', 'RecordedDate']

        for field in required_fields + important_fields:
            if field in df.columns:
                missing_count = df[field].isna().sum() + (df[field] == '').sum()
                missing_pct = (missing_count / len(df)) * 100

                results['completeness'][field] = {
                    'missing_count': int(missing_count),
                    'missing_percentage': round(missing_pct, 2)
                }

        # Validity checks - ICD-10 codes
        if 'Code' in df.columns:
            valid_codes = 0
            invalid_codes = 0

            for code in df['Code']:
                if code and code != '':
                    if is_valid_icd10_code(str(code)):
                        valid_codes += 1
                    else:
                        invalid_codes += 1

            results['validity']['ICD10_codes'] = {
                'valid': valid_codes,
                'invalid': invalid_codes,
                'invalid_percentage': round((invalid_codes / len(df)) * 100, 2)
            }

            if invalid_codes > 0:
                results['issues'].append({
                    'severity': 'WARNING',
                    'field': 'Code',
                    'message': f'{invalid_codes} invalid ICD-10 code formats'
                })

        return results

    def validate_medication_data(self, df: pd.DataFrame) -> Dict:
        """
        Validate medication data quality.

        Args:
            df: DataFrame with medication data

        Returns:
            Dict with validation results
        """
        results = {
            'total_records': len(df),
            'completeness': {},
            'validity': {},
            'issues': []
        }

        # Completeness checks
        required_fields = ['MedicationID', 'PatientID']
        important_fields = ['MedicationCode', 'MedicationName', 'EffectiveDate']

        for field in required_fields + important_fields:
            if field in df.columns:
                missing_count = df[field].isna().sum() + (df[field] == '').sum()
                missing_pct = (missing_count / len(df)) * 100

                results['completeness'][field] = {
                    'missing_count': int(missing_count),
                    'missing_percentage': round(missing_pct, 2)
                }

        # Validity checks - ATC codes
        if 'MedicationCode' in df.columns:
            valid_codes = 0
            invalid_codes = 0
            pzn_codes = 0

            for code in df['MedicationCode']:
                if code and code != '':
                    code_str = str(code)
                    if code_str.startswith('PZN_') or code_str.isdigit():
                        pzn_codes += 1
                    elif is_valid_atc_code(code_str):
                        valid_codes += 1
                    else:
                        invalid_codes += 1

            results['validity']['medication_codes'] = {
                'valid_atc': valid_codes,
                'pzn_codes': pzn_codes,
                'invalid': invalid_codes
            }

        return results

    def validate_referential_integrity(self,
                                       conditions_df: pd.DataFrame,
                                       medications_df: pd.DataFrame,
                                       encounters_df: pd.DataFrame,
                                       patients_df: pd.DataFrame) -> Dict:
        """
        Validate referential integrity between tables.

        Checks if all PatientIDs in related tables exist in patients table.

        Args:
            conditions_df: Conditions DataFrame
            medications_df: Medications DataFrame
            encounters_df: Encounters DataFrame
            patients_df: Patients DataFrame

        Returns:
            Dict with integrity check results
        """
        results = {
            'patients_valid': True,
            'orphaned_records': {},
            'issues': []
        }

        # Get set of valid patient IDs (after cleaning, we'd use normalized IDs)
        valid_patient_ids = set(
            patients_df[patients_df['PatientID'] != '']['PatientID'].unique()
        )

        # Check conditions
        if not conditions_df.empty and 'PatientID' in conditions_df.columns:
            condition_patient_ids = set(
                conditions_df[conditions_df['PatientID'] != '']['PatientID'].unique()
            )
            orphaned_conditions = condition_patient_ids - valid_patient_ids

            results['orphaned_records']['conditions'] = len(orphaned_conditions)

            if orphaned_conditions:
                results['issues'].append({
                    'severity': 'ERROR',
                    'table': 'conditions',
                    'message': f'{len(orphaned_conditions)} condition records reference non-existent patients'
                })

        # Check medications
        if not medications_df.empty and 'PatientID' in medications_df.columns:
            medication_patient_ids = set(
                medications_df[medications_df['PatientID'] != '']['PatientID'].unique()
            )
            orphaned_medications = medication_patient_ids - valid_patient_ids

            results['orphaned_records']['medications'] = len(orphaned_medications)

            if orphaned_medications:
                results['issues'].append({
                    'severity': 'ERROR',
                    'table': 'medications',
                    'message': f'{len(orphaned_medications)} medication records reference non-existent patients'
                })

        # Check encounters
        if not encounters_df.empty and 'PatientID' in encounters_df.columns:
            encounter_patient_ids = set(
                encounters_df[encounters_df['PatientID'] != '']['PatientID'].unique()
            )
            orphaned_encounters = encounter_patient_ids - valid_patient_ids

            results['orphaned_records']['encounters'] = len(orphaned_encounters)

            if orphaned_encounters:
                results['issues'].append({
                    'severity': 'ERROR',
                    'table': 'encounters',
                    'message': f'{len(orphaned_encounters)} encounter records reference non-existent patients'
                })

        return results

    def generate_report(self,
                        patient_results: Dict,
                        condition_results: Dict,
                        medication_results: Dict,
                        integrity_results: Dict) -> Dict:
        """
        Generate comprehensive data quality report.

        Args:
            patient_results: Patient validation results
            condition_results: Condition validation results
            medication_results: Medication validation results
            integrity_results: Referential integrity results

        Returns:
            Combined quality report
        """
        # Collect all issues
        all_issues = (
            patient_results.get('issues', []) +
            condition_results.get('issues', []) +
            medication_results.get('issues', []) +
            integrity_results.get('issues', [])
        )

        # Count by severity
        errors = sum(1 for issue in all_issues if issue['severity'] == 'ERROR')
        warnings = sum(1 for issue in all_issues if issue['severity'] == 'WARNING')

        report = {
            'summary': {
                'total_patients': patient_results['total_records'],
                'total_conditions': condition_results['total_records'],
                'total_medications': medication_results['total_records'],
                'total_errors': errors,
                'total_warnings': warnings,
                'quality_score': self._calculate_quality_score(
                    patient_results,
                    condition_results,
                    medication_results
                )
            },
            'patient_quality': patient_results,
            'condition_quality': condition_results,
            'medication_quality': medication_results,
            'referential_integrity': integrity_results,
            'all_issues': all_issues
        }

        return report

    def _calculate_quality_score(self,
                                  patient_results: Dict,
                                  condition_results: Dict,
                                  medication_results: Dict) -> float:
        """
        Calculate overall quality score (0-100).

        Based on completeness of critical fields across all tables.

        Args:
            patient_results: Patient validation results
            condition_results: Condition validation results
            medication_results: Medication validation results

        Returns:
            Quality score (0-100)
        """
        scores = []

        # Patient completeness
        for field, stats in patient_results.get('completeness', {}).items():
            if stats.get('is_critical', False):
                completeness = 100 - stats['missing_percentage']
                scores.append(completeness)

        # Condition completeness (required fields)
        for field in ['ConditionID', 'PatientID']:
            if field in condition_results.get('completeness', {}):
                completeness = 100 - condition_results['completeness'][field]['missing_percentage']
                scores.append(completeness)

        # Medication completeness (required fields)
        for field in ['MedicationID', 'PatientID']:
            if field in medication_results.get('completeness', {}):
                completeness = 100 - medication_results['completeness'][field]['missing_percentage']
                scores.append(completeness)

        # Calculate average
        if scores:
            return round(sum(scores) / len(scores), 2)

        return 0.0
