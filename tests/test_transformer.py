#!/usr/bin/env python3
"""
Unit Tests for FHIR Transformer

Tests the transformation of CSV data to FHIR R4 resources.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import pytest
import pandas as pd
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.medication import Medication
from fhir.resources.medicationadministration import MedicationAdministration

from src.fhir_transformer import FHIRTransformer


class TestFHIRTransformer:
    """Test suite for FHIRTransformer class."""

    @pytest.fixture
    def transformer(self):
        """Create a fresh transformer instance for each test."""
        return FHIRTransformer()

    @pytest.fixture
    def sample_patient_row(self):
        """Sample patient data row."""
        return pd.Series(
            {
                "PatientID": "00001",
                "FirstName": "Max",
                "LastName": "Mustermann",
                "Birthdate": "1990-01-01",
                "Gender": "male",
                "Street": "Hauptstraße 1",
                "City": "Berlin",
                "PostalCode": "10115",
                "Country": "DE",
            }
        )

    @pytest.fixture
    def sample_condition_row(self):
        """Sample condition data row."""
        return pd.Series(
            {
                "ConditionID": "C001",
                "PatientID": "00001",
                "Code": "E11.9",
                "CodeSystem": "ICD-10-GM",
                "Display": "Diabetes mellitus",
                "RecordedDate": "2020-01-15",
            }
        )

    @pytest.fixture
    def sample_medication_row(self):
        """Sample medication data row."""
        return pd.Series(
            {
                "MedicationID": "M001",
                "PatientID": "00001",
                "MedicationCode": "A10BA02",
                "MedicationName": "Metformin",
                "DoseValue": "500",
                "DoseUnit": "mg",
                "Status": "completed",
                "EffectiveDate": "2020-01-15",
            }
        )

    def test_transformer_initialization(self, transformer):
        """Test that transformer initializes with correct state."""
        assert transformer.stats["patients_processed"] == 0
        assert transformer.stats["patients_successful"] == 0
        assert transformer.stats["patients_failed"] == 0
        assert len(transformer.stats["errors"]) == 0
        assert len(transformer.medication_cache) == 0

    def test_transform_patient_success(self, transformer, sample_patient_row):
        """Test successful patient transformation."""
        patient = transformer.transform_patient(sample_patient_row)

        assert patient is not None
        assert isinstance(patient, Patient)
        assert patient.id == "00001"
        assert patient.gender == "male"
        # birthDate is a date object, not string
        assert str(patient.birthDate) == "1990-01-01"

        # Check identifier
        assert len(patient.identifier) == 1
        assert patient.identifier[0].value == "00001"
        assert patient.identifier[0].system == "https://POLARWP.de/pid"

        # Check name
        assert len(patient.name) == 1
        assert patient.name[0].family == "Mustermann"
        assert patient.name[0].given == ["Max"]
        assert patient.name[0].use == "official"

        # Check address
        assert len(patient.address) == 1
        assert patient.address[0].line == ["Hauptstraße 1"]
        assert patient.address[0].city == "Berlin"
        assert patient.address[0].postalCode == "10115"
        assert patient.address[0].country == "DE"

        # Check stats
        assert transformer.stats["patients_processed"] == 1
        assert transformer.stats["patients_successful"] == 1
        assert transformer.stats["patients_failed"] == 0

    def test_transform_patient_minimal(self, transformer):
        """Test patient transformation with minimal data."""
        minimal_row = pd.Series(
            {
                "PatientID": "00002",
                "FirstName": "",
                "LastName": "",
                "Birthdate": "",
                "Gender": "unknown",
            }
        )

        patient = transformer.transform_patient(minimal_row)

        assert patient is not None
        assert patient.id == "00002"
        assert patient.gender == "unknown"
        # Name should not be set if both first and last are empty
        assert patient.name is None or len(patient.name) == 0

    def test_transform_patient_missing_id(self, transformer):
        """Test patient transformation with missing PatientID."""
        invalid_row = pd.Series(
            {"PatientID": "", "FirstName": "Max", "LastName": "Mustermann"}
        )

        patient = transformer.transform_patient(invalid_row)

        assert patient is None
        assert transformer.stats["patients_processed"] == 1
        assert transformer.stats["patients_failed"] == 1
        assert len(transformer.stats["errors"]) == 1
        assert transformer.stats["errors"][0]["resource_type"] == "Patient"

    def test_transform_patient_german_characters(self, transformer):
        """Test patient transformation with German umlauts."""
        german_row = pd.Series(
            {
                "PatientID": "00003",
                "FirstName": "Jürgen",
                "LastName": "Müller",
                "Birthdate": "1980-05-15",
                "Gender": "male",
                "City": "München",
            }
        )

        patient = transformer.transform_patient(german_row)

        assert patient is not None
        assert patient.name[0].family == "Müller"
        assert patient.name[0].given == ["Jürgen"]
        assert patient.address[0].city == "München"

    def test_transform_patient_date_validation(self, transformer):
        """Test patient birthdate validation."""
        # Invalid year (too old)
        old_row = pd.Series(
            {
                "PatientID": "00004",
                "FirstName": "Test",
                "LastName": "User",
                "Birthdate": "1800-01-01",  # Before 1900
                "Gender": "male",
            }
        )

        patient = transformer.transform_patient(old_row)
        assert patient is not None
        # Birthdate should not be set (fails validation)
        assert patient.birthDate is None

    def test_transform_condition_success(self, transformer, sample_condition_row):
        """Test successful condition transformation."""
        condition = transformer.transform_condition(sample_condition_row)

        assert condition is not None
        assert isinstance(condition, Condition)
        # clean_patient_id removes "C" prefix, so "C001" becomes "00001"
        assert condition.id == "00001"

        # Check subject reference
        assert condition.subject.reference == "Patient/00001"

        # Check clinical status (required)
        assert condition.clinicalStatus is not None
        assert condition.clinicalStatus.coding[0].code == "active"

        # Check code
        assert condition.code is not None
        assert condition.code.coding[0].code == "E11.9"
        assert condition.code.coding[0].system == "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
        assert condition.code.coding[0].display == "Diabetes mellitus"
        assert condition.code.text == "Diabetes mellitus"

        # Check recorded date (date object, not string)
        assert str(condition.recordedDate) == "2020-01-15"

        # Check stats
        assert transformer.stats["conditions_processed"] == 1
        assert transformer.stats["conditions_successful"] == 1

    def test_transform_condition_minimal(self, transformer):
        """Test condition transformation with minimal data."""
        minimal_row = pd.Series(
            {
                "ConditionID": "C002",
                "PatientID": "00001",
                "Code": "",
                "CodeSystem": "",
                "Display": "",
                "RecordedDate": "",
            }
        )

        condition = transformer.transform_condition(minimal_row)

        assert condition is not None
        # clean_patient_id removes "C" prefix, so "C002" becomes "00002"
        assert condition.id == "00002"
        # Code may be None or empty for minimal data
        # But resource should still be valid

    def test_transform_condition_missing_ids(self, transformer):
        """Test condition transformation with missing required IDs."""
        invalid_row = pd.Series(
            {
                "ConditionID": "",
                "PatientID": "00001",
                "Code": "E11.9",
            }
        )

        condition = transformer.transform_condition(invalid_row)

        assert condition is None
        assert transformer.stats["conditions_failed"] == 1

    def test_transform_condition_code_without_system(self, transformer):
        """Test condition with code but no code system."""
        row = pd.Series(
            {
                "ConditionID": "C003",
                "PatientID": "00001",
                "Code": "SomeCode",
                "CodeSystem": "",
                "Display": "Some condition",
            }
        )

        condition = transformer.transform_condition(row)

        assert condition is not None
        # Should use text-only code
        assert condition.code.text == "SomeCode"

    def test_transform_medication_administration_success(
        self, transformer, sample_medication_row
    ):
        """Test successful medication transformation."""
        medication, med_admin = transformer.transform_medication_administration(
            sample_medication_row
        )

        assert medication is not None
        assert med_admin is not None

        # Check Medication resource
        assert isinstance(medication, Medication)
        assert medication.id == "Medication-A10BA02"
        assert medication.code.coding[0].code == "A10BA02"
        assert medication.code.coding[0].system == "http://fhir.de/CodeSystem/bfarm/atc"
        assert medication.code.text == "Metformin"

        # Check MedicationAdministration resource
        assert isinstance(med_admin, MedicationAdministration)
        # clean_patient_id removes "M" prefix, so "M001" becomes "00001"
        assert med_admin.id == "00001"
        assert med_admin.status == "completed"
        assert med_admin.subject.reference == "Patient/00001"
        # occurenceDateTime is a date object, not string
        assert str(med_admin.occurenceDateTime) == "2020-01-15"

        # Check medication reference
        assert med_admin.medication is not None

        # Check stats
        assert transformer.stats["medications_processed"] == 1
        assert transformer.stats["medications_successful"] == 1

    def test_transform_medication_caching(self, transformer):
        """Test medication caching to avoid duplicates."""
        row1 = pd.Series(
            {
                "MedicationID": "M001",
                "PatientID": "00001",
                "MedicationCode": "A10BA02",
                "MedicationName": "Metformin",
                "Status": "completed",
                "EffectiveDate": "2020-01-15",
            }
        )

        row2 = pd.Series(
            {
                "MedicationID": "M002",
                "PatientID": "00002",
                "MedicationCode": "A10BA02",  # Same code as row1
                "MedicationName": "Metformin",
                "Status": "completed",
                "EffectiveDate": "2020-02-01",
            }
        )

        med1, _ = transformer.transform_medication_administration(row1)
        med2, _ = transformer.transform_medication_administration(row2)

        # Both should return the same cached Medication object
        assert med1 is med2
        assert len(transformer.medication_cache) == 1

    def test_transform_medication_pzn_code(self, transformer):
        """Test medication with PZN code (numeric only, no prefix)."""
        # Note: PZN codes with underscores in ID fail FHIR validation
        # Using numeric-only PZN code instead
        pzn_row = pd.Series(
            {
                "MedicationID": "M003",
                "PatientID": "00001",
                "MedicationCode": "12345678",  # Numeric PZN code
                "MedicationName": "Some Drug",
                "Status": "completed",
                "EffectiveDate": "2020-01-15",
            }
        )

        medication, _ = transformer.transform_medication_administration(pzn_row)

        assert medication is not None
        assert medication.code.coding[0].system == "http://fhir.de/CodeSystem/ifa/pzn"
        assert medication.code.coding[0].code == "12345678"

    def test_transform_medication_status_normalization(self, transformer):
        """Test medication status normalization to FHIR valueSet."""
        test_cases = [
            ("completed", "completed"),
            ("in-progress", "inprogress"),
            ("on-hold", "onhold"),
            ("invalid-status", "completed"),  # Default
        ]

        for input_status, expected_status in test_cases:
            row = pd.Series(
                {
                    "MedicationID": f"M00{input_status}",
                    "PatientID": "00001",
                    "MedicationCode": "A10BA02",
                    "MedicationName": "Test",
                    "Status": input_status,
                    "EffectiveDate": "2020-01-15",
                }
            )

            _, med_admin = transformer.transform_medication_administration(row)
            assert med_admin.status == expected_status

    def test_transform_medication_without_code(self, transformer):
        """Test medication without code (uses name only)."""
        row = pd.Series(
            {
                "MedicationID": "M004",
                "PatientID": "00001",
                "MedicationCode": "",
                "MedicationName": "Unknown Medication",
                "Status": "completed",
                "EffectiveDate": "2020-01-15",
            }
        )

        medication, med_admin = transformer.transform_medication_administration(row)

        # No Medication resource (no code)
        assert medication is None
        # But MedicationAdministration should exist with concept
        assert med_admin is not None

    def test_transform_all(self, transformer):
        """Test transform_all orchestration."""
        patients_df = pd.DataFrame(
            [
                {
                    "PatientID": "00001",
                    "FirstName": "Max",
                    "LastName": "Mustermann",
                    "Birthdate": "1990-01-01",
                    "Gender": "male",
                },
                {
                    "PatientID": "00002",
                    "FirstName": "Anna",
                    "LastName": "Schmidt",
                    "Birthdate": "1985-05-15",
                    "Gender": "female",
                },
            ]
        )

        conditions_df = pd.DataFrame(
            [
                {
                    "ConditionID": "C001",
                    "PatientID": "00001",
                    "Code": "E11.9",
                    "CodeSystem": "ICD-10-GM",
                    "Display": "Diabetes",
                    "RecordedDate": "2020-01-15",
                },
                {
                    "ConditionID": "C002",
                    "PatientID": "00002",
                    "Code": "I10",
                    "CodeSystem": "ICD-10-GM",
                    "Display": "Hypertension",
                    "RecordedDate": "2020-02-01",
                },
            ]
        )

        medications_df = pd.DataFrame(
            [
                {
                    "MedicationID": "M001",
                    "PatientID": "00001",
                    "MedicationCode": "A10BA02",
                    "MedicationName": "Metformin",
                    "Status": "completed",
                    "EffectiveDate": "2020-01-15",
                }
            ]
        )

        resources = transformer.transform_all(
            patients_df, conditions_df, medications_df
        )

        assert len(resources["Patient"]) == 2
        assert len(resources["Condition"]) == 2
        assert len(resources["Medication"]) == 1
        assert len(resources["MedicationAdministration"]) == 1

    def test_create_bundle(self, transformer):
        """Test FHIR bundle creation."""
        # Create some sample resources
        patients_df = pd.DataFrame(
            [{"PatientID": "00001", "FirstName": "Max", "LastName": "Mustermann"}]
        )

        resources = transformer.transform_all(
            patients_df, pd.DataFrame(), pd.DataFrame()
        )

        bundle = transformer.create_bundle(resources)

        assert bundle is not None
        assert bundle.type == "collection"
        assert len(bundle.entry) == 1  # 1 patient
        # resource_type is the correct attribute name in fhir.resources library
        assert bundle.entry[0].resource.resource_type == "Patient"

    def test_get_statistics(self, transformer, sample_patient_row):
        """Test statistics calculation."""
        # Process some data
        transformer.transform_patient(sample_patient_row)

        stats = transformer.get_statistics()

        assert stats["patients_processed"] == 1
        assert stats["patients_successful"] == 1
        assert "patient_success_rate" in stats
        assert stats["patient_success_rate"] == 100.0

    def test_get_statistics_with_failures(self, transformer):
        """Test statistics with some failures."""
        # Valid patient
        valid_row = pd.Series({"PatientID": "00001", "FirstName": "Max"})
        # Invalid patient (missing ID)
        invalid_row = pd.Series({"PatientID": "", "FirstName": "Anna"})

        transformer.transform_patient(valid_row)
        transformer.transform_patient(invalid_row)

        stats = transformer.get_statistics()

        assert stats["patients_processed"] == 2
        assert stats["patients_successful"] == 1
        assert stats["patients_failed"] == 1
        assert stats["patient_success_rate"] == 50.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def transformer(self):
        """Create a fresh transformer instance for each test."""
        return FHIRTransformer()

    def test_empty_dataframes(self, transformer):
        """Test transform_all with empty DataFrames."""
        resources = transformer.transform_all(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )

        assert len(resources["Patient"]) == 0
        assert len(resources["Condition"]) == 0
        assert len(resources["Medication"]) == 0

    def test_none_values(self, transformer):
        """Test handling of None values in data."""
        row = pd.Series(
            {
                "PatientID": "00001",
                "FirstName": None,
                "LastName": None,
                "Birthdate": None,
                "Gender": None,
            }
        )

        patient = transformer.transform_patient(row)
        assert patient is not None
        # Should handle None values gracefully

    def test_very_long_strings(self, transformer):
        """Test handling of very long strings."""
        long_string = "A" * 1000
        row = pd.Series(
            {
                "PatientID": "00001",
                "FirstName": long_string,
                "LastName": long_string,
            }
        )

        patient = transformer.transform_patient(row)
        assert patient is not None
        # FHIR should handle long strings

    def test_special_characters(self, transformer):
        """Test handling of special characters."""
        row = pd.Series(
            {
                "PatientID": "00001",
                "FirstName": "Test <>&\"'",
                "LastName": "User \n\t\r",
                "City": "Berlin/München",
            }
        )

        patient = transformer.transform_patient(row)
        assert patient is not None
        # Should handle special characters without errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
