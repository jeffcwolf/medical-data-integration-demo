#!/usr/bin/env python3
"""
Unit Tests for Data Quality Validator

Tests the data validation functionality including completeness, consistency,
validity, and referential integrity checks.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import pytest
import pandas as pd
from src.data_validator import DataQualityValidator


class TestDataQualityValidator:
    """Test suite for DataQualityValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a fresh validator instance for each test."""
        return DataQualityValidator()

    @pytest.fixture
    def sample_patients_df(self):
        """Sample patient data for testing."""
        return pd.DataFrame(
            {
                "PatientID": ["00001", "00002", "00003", ""],
                "FirstName": ["Max", "Anna", "", "Hans"],
                "LastName": ["Mustermann", "Schmidt", "Müller", ""],
                "Birthdate": ["1990-01-01", "01.01.1985", "invalid", "1970-05-15"],
                "Gender": ["male", "W", "männlich", "other"],
            }
        )

    @pytest.fixture
    def sample_conditions_df(self):
        """Sample condition data for testing."""
        return pd.DataFrame(
            {
                "ConditionID": ["C001", "C002", "C003", ""],
                "PatientID": ["00001", "00001", "00002", "00003"],
                "Code": ["E11.9", "I10", "invalid", "J06.9"],
                "CodeSystem": [
                    "ICD-10-GM",
                    "ICD-10-GM",
                    "ICD-10-GM",
                    "ICD-10-GM",
                ],
                "Display": ["Diabetes", "Hypertension", "", "Infection"],
                "RecordedDate": ["2020-01-01", "2020-02-15", "invalid", ""],
            }
        )

    @pytest.fixture
    def sample_medications_df(self):
        """Sample medication data for testing."""
        return pd.DataFrame(
            {
                "MedicationID": ["M001", "M002", "M003"],
                "PatientID": ["00001", "00002", "00003"],
                "MedicationCode": ["A10BA02", "C03CA01", "invalid"],
                "MedicationName": ["Metformin", "Furosemide", "Unknown"],
                "EffectiveDate": ["2020-01-01", "2020-02-15", ""],
            }
        )

    def test_validator_initialization(self, validator):
        """Test that validator initializes with empty state."""
        assert validator.issues == []
        assert validator.metrics == {}

    def test_validate_patient_data_completeness(self, validator, sample_patients_df):
        """Test patient data completeness checks."""
        results = validator.validate_patient_data(sample_patients_df)

        assert results["total_records"] == 4
        assert "completeness" in results

        # Check PatientID completeness
        assert "PatientID" in results["completeness"]
        patient_id_stats = results["completeness"]["PatientID"]
        assert patient_id_stats["missing_count"] == 1  # One empty PatientID
        assert patient_id_stats["is_critical"] is True

        # Should have error for missing required field
        assert any(
            issue["severity"] == "ERROR"
            and issue["field"] == "PatientID"
            for issue in results["issues"]
        )

    def test_validate_patient_data_date_consistency(
        self, validator, sample_patients_df
    ):
        """Test birthdate format consistency checks."""
        results = validator.validate_patient_data(sample_patients_df)

        assert "consistency" in results
        assert "Birthdate" in results["consistency"]

        birthdate_stats = results["consistency"]["Birthdate"]
        assert birthdate_stats["valid"] > 0
        assert birthdate_stats["invalid"] > 0

        # Should have warning for invalid dates
        assert any(
            issue["severity"] == "WARNING" and issue["field"] == "Birthdate"
            for issue in results["issues"]
        )

    def test_validate_patient_data_gender_consistency(
        self, validator, sample_patients_df
    ):
        """Test gender value consistency checks."""
        results = validator.validate_patient_data(sample_patients_df)

        assert "Gender" in results["consistency"]
        gender_stats = results["consistency"]["Gender"]

        # Should have raw variations but fewer standardized values
        assert gender_stats["unique_raw_values"] > 0
        assert len(gender_stats["standardized_values"]) > 0

    def test_validate_patient_data_duplicates(self, validator):
        """Test duplicate PatientID detection."""
        duplicate_df = pd.DataFrame(
            {
                "PatientID": ["00001", "00001", "00002"],
                "FirstName": ["Max", "Max", "Anna"],
                "LastName": ["Mustermann", "Mustermann", "Schmidt"],
            }
        )

        results = validator.validate_patient_data(duplicate_df)

        assert "validity" in results
        assert results["validity"]["duplicates"] == 1

        # Should have error for duplicates
        assert any(
            issue["severity"] == "ERROR" and issue["field"] == "PatientID"
            for issue in results["issues"]
        )

    def test_validate_condition_data_completeness(
        self, validator, sample_conditions_df
    ):
        """Test condition data completeness checks."""
        results = validator.validate_condition_data(sample_conditions_df)

        assert results["total_records"] == 4
        assert "completeness" in results

        # Check required fields
        assert "ConditionID" in results["completeness"]
        assert "PatientID" in results["completeness"]

    def test_validate_condition_data_icd10_codes(
        self, validator, sample_conditions_df
    ):
        """Test ICD-10 code validity checks."""
        results = validator.validate_condition_data(sample_conditions_df)

        assert "validity" in results
        assert "ICD10_codes" in results["validity"]

        code_stats = results["validity"]["ICD10_codes"]
        assert code_stats["valid"] > 0  # E11.9, I10, J06.9
        assert code_stats["invalid"] > 0  # "invalid"

        # Should have warning for invalid codes
        assert any(
            issue["severity"] == "WARNING" and issue["field"] == "Code"
            for issue in results["issues"]
        )

    def test_validate_medication_data_completeness(
        self, validator, sample_medications_df
    ):
        """Test medication data completeness checks."""
        results = validator.validate_medication_data(sample_medications_df)

        assert results["total_records"] == 3
        assert "completeness" in results

        # Check required fields
        assert "MedicationID" in results["completeness"]
        assert "PatientID" in results["completeness"]

    def test_validate_medication_data_atc_codes(
        self, validator, sample_medications_df
    ):
        """Test ATC code validity checks."""
        results = validator.validate_medication_data(sample_medications_df)

        assert "validity" in results
        assert "medication_codes" in results["validity"]

        code_stats = results["validity"]["medication_codes"]
        assert code_stats["valid_atc"] > 0  # A10BA02, C03CA01
        assert code_stats["invalid"] > 0  # "invalid"

    def test_validate_medication_data_pzn_codes(self, validator):
        """Test PZN code detection."""
        pzn_df = pd.DataFrame(
            {
                "MedicationID": ["M001", "M002"],
                "PatientID": ["00001", "00002"],
                "MedicationCode": ["PZN_12345678", "98765432"],
                "MedicationName": ["Med1", "Med2"],
            }
        )

        results = validator.validate_medication_data(pzn_df)

        code_stats = results["validity"]["medication_codes"]
        assert code_stats["pzn_codes"] == 2  # Both are PZN format

    def test_validate_referential_integrity_valid(self, validator):
        """Test referential integrity with valid references."""
        patients_df = pd.DataFrame({"PatientID": ["00001", "00002", "00003"]})

        conditions_df = pd.DataFrame(
            {"ConditionID": ["C001", "C002"], "PatientID": ["00001", "00002"]}
        )

        medications_df = pd.DataFrame(
            {"MedicationID": ["M001"], "PatientID": ["00001"]}
        )

        encounters_df = pd.DataFrame(
            {"EncounterID": ["E001"], "PatientID": ["00003"]}
        )

        results = validator.validate_referential_integrity(
            conditions_df, medications_df, encounters_df, patients_df
        )

        # All references should be valid
        assert results["orphaned_records"]["conditions"] == 0
        assert results["orphaned_records"]["medications"] == 0
        assert results["orphaned_records"]["encounters"] == 0
        assert len(results["issues"]) == 0

    def test_validate_referential_integrity_orphaned(self, validator):
        """Test referential integrity with orphaned records."""
        patients_df = pd.DataFrame({"PatientID": ["00001"]})

        conditions_df = pd.DataFrame(
            {
                "ConditionID": ["C001", "C002"],
                "PatientID": ["00001", "99999"],  # 99999 doesn't exist
            }
        )

        medications_df = pd.DataFrame(
            {
                "MedicationID": ["M001"],
                "PatientID": ["88888"],  # 88888 doesn't exist
            }
        )

        encounters_df = pd.DataFrame()  # Empty

        results = validator.validate_referential_integrity(
            conditions_df, medications_df, encounters_df, patients_df
        )

        # Should detect orphaned records
        assert results["orphaned_records"]["conditions"] == 1  # PatientID 99999
        assert results["orphaned_records"]["medications"] == 1  # PatientID 88888

        # Should have errors
        assert len(results["issues"]) == 2
        assert all(issue["severity"] == "ERROR" for issue in results["issues"])

    def test_generate_report(
        self,
        validator,
        sample_patients_df,
        sample_conditions_df,
        sample_medications_df,
    ):
        """Test comprehensive report generation."""
        # Run validations
        patient_results = validator.validate_patient_data(sample_patients_df)
        condition_results = validator.validate_condition_data(sample_conditions_df)
        medication_results = validator.validate_medication_data(sample_medications_df)

        patients_df = sample_patients_df
        encounters_df = pd.DataFrame()
        integrity_results = validator.validate_referential_integrity(
            sample_conditions_df, sample_medications_df, encounters_df, patients_df
        )

        # Generate report
        report = validator.generate_report(
            patient_results, condition_results, medication_results, integrity_results
        )

        # Check report structure
        assert "summary" in report
        assert "patient_quality" in report
        assert "condition_quality" in report
        assert "medication_quality" in report
        assert "referential_integrity" in report
        assert "all_issues" in report

        # Check summary stats
        summary = report["summary"]
        assert summary["total_patients"] == 4
        assert summary["total_conditions"] == 4
        assert summary["total_medications"] == 3
        assert "total_errors" in summary
        assert "total_warnings" in summary
        assert "quality_score" in summary

        # Quality score should be between 0 and 100
        assert 0 <= summary["quality_score"] <= 100

    def test_calculate_quality_score_perfect_data(self, validator):
        """Test quality score calculation with perfect data."""
        perfect_patients = pd.DataFrame(
            {
                "PatientID": ["00001", "00002"],
                "FirstName": ["Max", "Anna"],
                "LastName": ["Mustermann", "Schmidt"],
                "Birthdate": ["1990-01-01", "1985-02-15"],
                "Gender": ["male", "female"],
            }
        )

        perfect_conditions = pd.DataFrame(
            {
                "ConditionID": ["C001", "C002"],
                "PatientID": ["00001", "00002"],
                "Code": ["E11.9", "I10"],
            }
        )

        perfect_medications = pd.DataFrame(
            {
                "MedicationID": ["M001", "M002"],
                "PatientID": ["00001", "00002"],
                "MedicationCode": ["A10BA02", "C03CA01"],
            }
        )

        patient_results = validator.validate_patient_data(perfect_patients)
        condition_results = validator.validate_condition_data(perfect_conditions)
        medication_results = validator.validate_medication_data(perfect_medications)

        score = validator._calculate_quality_score(
            patient_results, condition_results, medication_results
        )

        # Perfect data should have 100% quality score
        assert score == 100.0

    def test_calculate_quality_score_poor_data(self, validator):
        """Test quality score calculation with poor data."""
        poor_patients = pd.DataFrame(
            {
                "PatientID": ["", "", ""],  # All missing
                "FirstName": ["", "", ""],
                "LastName": ["", "", ""],
            }
        )

        poor_conditions = pd.DataFrame(
            {
                "ConditionID": ["", ""],  # All missing
                "PatientID": ["", ""],
            }
        )

        poor_medications = pd.DataFrame(
            {
                "MedicationID": ["", ""],  # All missing
                "PatientID": ["", ""],
            }
        )

        patient_results = validator.validate_patient_data(poor_patients)
        condition_results = validator.validate_condition_data(poor_conditions)
        medication_results = validator.validate_medication_data(poor_medications)

        score = validator._calculate_quality_score(
            patient_results, condition_results, medication_results
        )

        # Poor data should have low quality score
        assert score < 50.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def validator(self):
        """Create a fresh validator instance for each test."""
        return DataQualityValidator()

    def test_empty_dataframe(self, validator):
        """Test validation with empty DataFrame."""
        empty_df = pd.DataFrame()

        results = validator.validate_patient_data(empty_df)
        assert results["total_records"] == 0
        assert len(results["issues"]) == 0

    def test_missing_columns(self, validator):
        """Test validation with missing expected columns."""
        minimal_df = pd.DataFrame({"PatientID": ["00001", "00002"]})

        # Should not crash - just skip missing fields
        results = validator.validate_patient_data(minimal_df)
        assert results["total_records"] == 2

    def test_all_na_column(self, validator):
        """Test validation with column containing all NA values."""
        all_na_df = pd.DataFrame(
            {"PatientID": ["00001", "00002"], "Birthdate": [None, None]}
        )

        results = validator.validate_patient_data(all_na_df)
        assert results["completeness"]["Birthdate"]["missing_count"] == 2

    def test_special_characters_in_data(self, validator):
        """Test validation with special characters and umlauts."""
        special_df = pd.DataFrame(
            {
                "PatientID": ["00001", "00002"],
                "FirstName": ["Müller", "Schröder"],
                "LastName": ["Weiß", "Größ"],
            }
        )

        # Should handle UTF-8 characters without errors
        results = validator.validate_patient_data(special_df)
        assert results["total_records"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
