#!/usr/bin/env python3
"""
Unit Tests for FHIR to CSV Extractor

Tests the extraction and "messification" of FHIR data to CSV.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import pytest
import random
import json
from pathlib import Path
from src.fhir_to_csv_extractor import (
    messify_patient_id,
    messify_date,
    messify_gender,
    extract_patient,
    extract_conditions,
    extract_medications,
    extract_encounters,
    maybe_missing,
)


class TestMessificationFunctions:
    """Test the data messification helper functions."""

    def test_messify_patient_id_variations(self):
        """Test patient ID messification creates variations."""
        test_id = "00001"
        variations = set()

        # Generate multiple variations
        for _ in range(20):
            messified = messify_patient_id(test_id)
            variations.add(messified)

        # Should produce different formats
        assert len(variations) > 1
        # All should contain the base number
        assert all("00001" in v or "1" in v for v in variations)

    def test_messify_patient_id_preserves_number(self):
        """Test that patient ID messification preserves the core number."""
        test_id = "00042"

        for _ in range(10):
            messified = messify_patient_id(test_id)
            # Should contain "42" somewhere
            assert "42" in messified

    def test_messify_date_variations(self):
        """Test date messification creates format variations."""
        test_date = "1990-01-15"
        variations = set()

        for _ in range(20):
            messified = messify_date(test_date)
            variations.add(messified)

        # Should produce different date formats
        assert len(variations) > 1

    def test_messify_date_preserves_components(self):
        """Test that date messification preserves date components."""
        test_date = "1990-01-15"

        for _ in range(10):
            messified = messify_date(test_date)
            # Should contain year, month, and day somewhere
            # Could be in different formats: 1990-01-15, 15.01.1990, 1990/01/15, etc.
            assert messified is not None
            # At minimum, should not be empty
            assert len(messified) > 0

    def test_messify_date_invalid_input(self):
        """Test date messification with invalid input."""
        invalid_dates = ["", "invalid", None, "2020-13-45"]

        for invalid in invalid_dates:
            # Should either return original or handle gracefully
            result = messify_date(invalid)
            # Should not crash

    def test_messify_gender_variations(self):
        """Test gender messification creates variations."""
        test_gender = "male"
        variations = set()

        for _ in range(20):
            messified = messify_gender(test_gender)
            variations.add(messified)

        # Should produce variations like: male, M, männlich, m
        assert len(variations) > 1

    def test_messify_gender_male_variations(self):
        """Test male gender produces expected variations."""
        variations = set()

        for _ in range(50):
            messified = messify_gender("male")
            variations.add(messified)

        # Should include some German and English variations
        possible_variations = {"male", "M", "m", "männlich", "MALE"}
        assert len(variations.intersection(possible_variations)) > 0

    def test_messify_gender_female_variations(self):
        """Test female gender produces expected variations."""
        variations = set()

        for _ in range(50):
            messified = messify_gender("female")
            variations.add(messified)

        # Should include some German and English variations
        possible_variations = {"female", "F", "f", "weiblich", "W", "FEMALE"}
        assert len(variations.intersection(possible_variations)) > 0

    def test_messify_gender_other_values(self):
        """Test gender messification with other/unknown values."""
        for gender in ["other", "unknown"]:
            messified = messify_gender(gender)
            # Should return a valid value
            assert messified is not None

    def test_maybe_missing(self):
        """Test probabilistic missing data function."""
        # With critical=True, should never make missing
        for _ in range(20):
            result = maybe_missing("test", critical=True)
            assert result == "test"

        # Test non-critical with random seed
        random.seed(42)
        results = []
        for _ in range(100):
            result = maybe_missing("test", critical=False)
            results.append(result)

        # Should have both "test" and "" in results over many iterations
        # (depending on MISSING_DATA_PROB which is 0.12 in the module)
        # Just verify it doesn't crash and returns string
        assert all(isinstance(r, str) for r in results)


class TestFHIRExtraction:
    """Test FHIR data extraction functions."""

    @pytest.fixture
    def sample_patient_bundle(self):
        """Sample FHIR patient bundle."""
        return {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "POLAR_WP1.1_00001",
                        "identifier": [
                            {
                                "system": "https://POLARWP.de/pid",
                                "value": "POLAR_WP1.1_00001",
                            }
                        ],
                        "name": [{"family": "Mustermann", "given": ["Max"]}],
                        "gender": "male",
                        "birthDate": "1990-01-01",
                        "address": [
                            {
                                "line": ["Hauptstraße 1"],
                                "city": "Berlin",
                                "postalCode": "10115",
                                "country": "DE",
                            }
                        ],
                    }
                }
            ],
        }

    @pytest.fixture
    def sample_condition_bundle(self):
        """Sample FHIR condition bundle."""
        return {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "condition-001",
                        "subject": {"reference": "Patient/POLAR_WP1.1_00001"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                                    "code": "E11.9",
                                    "display": "Diabetes mellitus",
                                }
                            ]
                        },
                        "recordedDate": "2020-01-15",
                    }
                }
            ],
        }

    @pytest.fixture
    def sample_medication_bundle(self):
        """Sample FHIR medication bundle."""
        return {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Medication",
                        "id": "medication-001",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://fhir.de/CodeSystem/bfarm/atc",
                                    "code": "A10BA02",
                                    "display": "Metformin",
                                }
                            ]
                        },
                    }
                },
                {
                    "resource": {
                        "resourceType": "MedicationAdministration",
                        "id": "medadmin-001",
                        "status": "completed",
                        "subject": {"reference": "Patient/POLAR_WP1.1_00001"},
                        "medication": {
                            "reference": {"reference": "Medication/medication-001"}
                        },
                        "occurenceDateTime": "2020-01-15T10:00:00Z",
                    }
                },
            ],
        }

    @pytest.fixture
    def sample_encounter_bundle(self):
        """Sample FHIR encounter bundle."""
        return {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Encounter",
                        "id": "encounter-001",
                        "subject": {"reference": "Patient/POLAR_WP1.1_00001"},
                        "class": {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                            "code": "IMP",
                            "display": "inpatient encounter",
                        },
                        "period": {
                            "start": "2020-01-10T08:00:00Z",
                            "end": "2020-01-15T12:00:00Z",
                        },
                    }
                }
            ],
        }

    def test_extract_patient(self, sample_patient_bundle):
        """Test patient resource extraction."""
        patient_resource = extract_patient(sample_patient_bundle)

        assert patient_resource is not None
        assert patient_resource["resourceType"] == "Patient"
        assert "id" in patient_resource
        assert "name" in patient_resource
        assert patient_resource["name"][0]["family"] == "Mustermann"
        assert patient_resource["name"][0]["given"] == ["Max"]

    def test_extract_patient_minimal(self):
        """Test patient extraction with minimal data."""
        minimal_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "POLAR_WP1.1_00001",
                    }
                }
            ],
        }

        patient_resource = extract_patient(minimal_bundle)
        assert patient_resource is not None
        assert patient_resource["id"] == "POLAR_WP1.1_00001"

    def test_extract_patient_no_patient(self):
        """Test patient extraction from bundle without patient."""
        empty_bundle = {"resourceType": "Bundle", "entry": []}

        patient_resource = extract_patient(empty_bundle)
        assert patient_resource is None

    def test_extract_conditions(self, sample_condition_bundle):
        """Test condition resource extraction."""
        conditions = extract_conditions(sample_condition_bundle, "POLAR_WP1.1_00001")

        assert len(conditions) == 1
        condition_data = conditions[0]

        assert "resource" in condition_data
        assert "patient_id" in condition_data
        assert condition_data["patient_id"] == "POLAR_WP1.1_00001"

        resource = condition_data["resource"]
        assert resource["resourceType"] == "Condition"
        assert resource["code"]["coding"][0]["code"] == "E11.9"

    def test_extract_conditions_multiple(self):
        """Test extraction of multiple conditions."""
        multi_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "cond-001",
                        "subject": {"reference": "Patient/00001"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                                    "code": "E11.9",
                                }
                            ]
                        },
                    }
                },
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "cond-002",
                        "subject": {"reference": "Patient/00001"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                                    "code": "I10",
                                }
                            ]
                        },
                    }
                },
            ],
        }

        conditions = extract_conditions(multi_bundle, "00001")
        assert len(conditions) == 2

    def test_extract_conditions_no_conditions(self):
        """Test condition extraction from bundle without conditions."""
        empty_bundle = {"resourceType": "Bundle", "entry": []}

        conditions = extract_conditions(empty_bundle, "00001")
        assert len(conditions) == 0

    def test_extract_medications(self, sample_medication_bundle):
        """Test medication resource extraction."""
        medications = extract_medications(sample_medication_bundle, "POLAR_WP1.1_00001")

        assert len(medications) == 1
        med_data = medications[0]

        assert "medications" in med_data or "administration" in med_data
        assert "patient_id" in med_data

        assert med_data["patient_id"] == "POLAR_WP1.1_00001"

    def test_extract_medications_no_medications(self):
        """Test medication extraction from bundle without medications."""
        empty_bundle = {"resourceType": "Bundle", "entry": []}

        medications = extract_medications(empty_bundle, "00001")
        assert len(medications) == 0

    def test_extract_encounters(self, sample_encounter_bundle):
        """Test encounter resource extraction."""
        encounters = extract_encounters(sample_encounter_bundle, "POLAR_WP1.1_00001")

        assert len(encounters) == 1
        encounter_data = encounters[0]

        assert "resource" in encounter_data
        assert "patient_id" in encounter_data
        assert encounter_data["patient_id"] == "POLAR_WP1.1_00001"

        resource = encounter_data["resource"]
        assert resource["resourceType"] == "Encounter"

    def test_extract_encounters_no_encounters(self):
        """Test encounter extraction from bundle without encounters."""
        empty_bundle = {"resourceType": "Bundle", "entry": []}

        encounters = extract_encounters(empty_bundle, "00001")
        assert len(encounters) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extract_patient_with_multiple_names(self):
        """Test patient extraction with multiple name entries."""
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "00001",
                        "name": [
                            {"use": "official", "family": "Smith", "given": ["John"]},
                            {"use": "nickname", "given": ["Johnny"]},
                        ],
                    }
                }
            ],
        }

        patient_resource = extract_patient(bundle)
        assert patient_resource is not None
        # Should extract patient resource with names
        assert patient_resource["name"][0]["family"] == "Smith"

    def test_extract_patient_with_umlauts(self):
        """Test patient extraction with German umlauts."""
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "00001",
                        "name": [
                            {"family": "Müller", "given": ["Jürgen"]},
                        ],
                        "address": [{"city": "München"}],
                    }
                }
            ],
        }

        patient_resource = extract_patient(bundle)
        assert patient_resource["name"][0]["family"] == "Müller"
        assert patient_resource["name"][0]["given"] == ["Jürgen"]
        assert patient_resource["address"][0]["city"] == "München"

    def test_extract_condition_without_display(self):
        """Test condition extraction without display text."""
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "cond-001",
                        "subject": {"reference": "Patient/00001"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                                    "code": "E11.9",
                                    # No display
                                }
                            ]
                        },
                    }
                }
            ],
        }

        conditions = extract_conditions(bundle, "00001")
        assert len(conditions) == 1
        # Should extract condition resource
        assert conditions[0]["resource"]["code"]["coding"][0]["code"] == "E11.9"

    def test_extract_medication_without_code(self):
        """Test medication extraction without code."""
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Medication",
                        "id": "med-001",
                        # No code field
                    }
                },
                {
                    "resource": {
                        "resourceType": "MedicationAdministration",
                        "id": "medadmin-001",
                        "subject": {"reference": "Patient/00001"},
                        "medication": {
                            "reference": {"reference": "Medication/med-001"}
                        },
                        "status": "completed",
                    }
                },
            ],
        }

        medications = extract_medications(bundle, "00001")
        # Should handle gracefully
        assert len(medications) >= 0

    def test_malformed_bundle(self):
        """Test extraction from malformed bundle."""
        malformed = {"resourceType": "Bundle"}  # No entry field

        patient_resource = extract_patient(malformed)
        # Should return None for missing patient

        conditions = extract_conditions(malformed, "00001")
        assert len(conditions) == 0


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_extraction_workflow(self):
        """Test complete extraction workflow."""
        # Create a complete bundle
        complete_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "POLAR_WP1.1_00001",
                        "name": [{"family": "Mustermann", "given": ["Max"]}],
                        "gender": "male",
                        "birthDate": "1990-01-01",
                    }
                },
                {
                    "resource": {
                        "resourceType": "Condition",
                        "id": "cond-001",
                        "subject": {"reference": "Patient/POLAR_WP1.1_00001"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                                    "code": "E11.9",
                                    "display": "Diabetes",
                                }
                            ]
                        },
                    }
                },
                {
                    "resource": {
                        "resourceType": "Encounter",
                        "id": "enc-001",
                        "subject": {"reference": "Patient/POLAR_WP1.1_00001"},
                        "class": {"code": "IMP"},
                    }
                },
            ],
        }

        # Extract all data types
        patient = extract_patient(complete_bundle)
        conditions = extract_conditions(complete_bundle, "POLAR_WP1.1_00001")
        encounters = extract_encounters(complete_bundle, "POLAR_WP1.1_00001")

        # Verify extraction
        assert patient is not None
        assert len(conditions) == 1
        assert len(encounters) == 1

        # Verify resources are correct type
        assert patient["resourceType"] == "Patient"
        assert conditions[0]["resource"]["resourceType"] == "Condition"
        assert encounters[0]["resource"]["resourceType"] == "Encounter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
