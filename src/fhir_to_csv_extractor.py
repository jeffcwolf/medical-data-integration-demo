#!/usr/bin/env python3
"""
FHIR to CSV Extractor - Phase 1 of Medical Data Integration Pipeline

This script extracts data from official MII (Medizininformatik-Initiative) FHIR
bundles and intentionally introduces realistic data quality issues to simulate
real-world hospital source systems.

Purpose: Demonstrate understanding of real-world data quality challenges before
showing transformation and cleaning capabilities in Phase 2.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

# Configuration
FHIR_DATA_DIR = Path("data/POLAR_WP_1.1_v2-POLAR_WP1.1_00001-POLAR_WP1.1_01650.json")
OUTPUT_DIR = Path("data/raw")
NUM_PATIENTS = 200  # Start with 200 for testing, can increase to 1650 later

# Data quality issue probability settings
MISSING_DATA_PROB = 0.12  # 12% chance of missing non-critical data
ID_VARIATION_ENABLED = True
DATE_VARIATION_ENABLED = True
GENDER_VARIATION_ENABLED = True

# Set random seed for reproducibility
random.seed(42)


def load_fhir_bundle(filepath: Path) -> Dict:
    """
    Load a FHIR bundle JSON file.

    Args:
        filepath: Path to FHIR bundle JSON file

    Returns:
        Dict containing the FHIR bundle
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_patient(bundle: Dict) -> Optional[Dict]:
    """
    Extract Patient resource from FHIR bundle.

    Args:
        bundle: FHIR Transaction Bundle

    Returns:
        Patient resource dict or None if not found
    """
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return None


def extract_conditions(bundle: Dict, patient_id: str) -> List[Dict]:
    """
    Extract all Condition resources from FHIR bundle.

    Args:
        bundle: FHIR Transaction Bundle
        patient_id: Patient ID for reference

    Returns:
        List of Condition resource dicts
    """
    conditions = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Condition":
            conditions.append({"resource": resource, "patient_id": patient_id})
    return conditions


def extract_medications(bundle: Dict, patient_id: str) -> List[Dict]:
    """
    Extract Medication and MedicationAdministration resources from FHIR bundle.

    Args:
        bundle: FHIR Transaction Bundle
        patient_id: Patient ID for reference

    Returns:
        List of medication data dicts
    """
    medications = {}  # Store Medication resources by ID
    administrations = []

    # First pass: collect Medication resources
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Medication":
            med_id = resource.get("id")
            medications[med_id] = resource

    # Second pass: collect MedicationAdministration and link to Medication
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "MedicationAdministration":
            administrations.append(
                {
                    "administration": resource,
                    "patient_id": patient_id,
                    "medications": medications,
                }
            )

    return administrations


def extract_encounters(bundle: Dict, patient_id: str) -> List[Dict]:
    """
    Extract Encounter resources from FHIR bundle.

    Args:
        bundle: FHIR Transaction Bundle
        patient_id: Patient ID for reference

    Returns:
        List of Encounter resource dicts
    """
    encounters = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Encounter":
            encounters.append({"resource": resource, "patient_id": patient_id})
    return encounters


# ============================================================================
# Data "Breaking" Functions - Introduce Realistic Quality Issues
# ============================================================================


def messify_patient_id(original_id: str) -> str:
    """
    Introduce ID format inconsistencies.

    Original format: "Polar-WP1.1-00001"
    Messy variations: "P-00001", "PAT00001", "00001", etc.

    Args:
        original_id: Clean FHIR patient ID

    Returns:
        Messified patient ID
    """
    if not ID_VARIATION_ENABLED:
        return original_id

    # Extract the numeric portion
    number = original_id.split("-")[-1]

    formats = [
        lambda x: f"P-{x}",  # P-00001
        lambda x: f"PAT{x}",  # PAT00001
        lambda x: x,  # 00001 (just number)
        lambda x: f"WP1-{x}",  # WP1-00001
        lambda x: original_id,  # Keep original (20% of time)
    ]

    # Weighted choice - keep original 20% of the time
    weights = [0.2, 0.2, 0.2, 0.2, 0.2]
    return random.choices(formats, weights=weights)[0](number)


def messify_date(iso_date: str) -> str:
    """
    Introduce date format variations.

    Original format: "2019-01-01" (ISO)
    Messy variations: "01.01.2019", "2019/01/01", "01-01-2019"

    Args:
        iso_date: Clean ISO date string

    Returns:
        Messified date string or empty string if missing
    """
    if not iso_date or random.random() < MISSING_DATA_PROB:
        return ""

    if not DATE_VARIATION_ENABLED:
        return iso_date

    # Parse ISO date
    try:
        parts = iso_date.split("T")[0].split("-")  # Handle datetime, get date part
        year, month, day = parts[0], parts[1], parts[2]

        formats = [
            lambda: f"{day}.{month}.{year}",  # DD.MM.YYYY (German)
            lambda: f"{year}/{month}/{day}",  # YYYY/MM/DD
            lambda: f"{day}-{month}-{year}",  # DD-MM-YYYY
            lambda: iso_date.split("T")[0],  # Keep ISO (YYYY-MM-DD)
        ]

        return random.choice(formats)()
    except (IndexError, ValueError):
        return iso_date  # Return original if parsing fails


def messify_gender(gender: str) -> str:
    """
    Introduce gender value inconsistencies.

    Original format: "male", "female"
    Messy variations: "M", "m", "männlich", "W", "w", "weiblich"

    Args:
        gender: Clean FHIR gender value

    Returns:
        Messified gender value or empty string if missing
    """
    if not gender or random.random() < MISSING_DATA_PROB:
        return ""

    if not GENDER_VARIATION_ENABLED:
        return gender

    mappings = {
        "male": ["M", "m", "male", "männlich", "Male"],
        "female": ["F", "w", "female", "weiblich", "W", "Female"],
        "other": ["divers", "d", "other", "Other"],
    }

    options = mappings.get(gender, [gender])
    return random.choice(options)


def maybe_missing(value: str, critical: bool = False) -> str:
    """
    Randomly make non-critical fields missing.

    Args:
        value: Original value
        critical: If True, never make missing

    Returns:
        Original value or empty string
    """
    if critical:
        return value

    if random.random() < MISSING_DATA_PROB:
        return ""

    return value


# ============================================================================
# CSV Row Building Functions
# ============================================================================


def patient_to_csv_row(patient: Dict, messy_id: str) -> Dict:
    """
    Convert FHIR Patient resource to CSV row with quality issues.

    Args:
        patient: FHIR Patient resource
        messy_id: Already messified patient ID

    Returns:
        Dict representing a CSV row
    """
    # Extract name
    name_obj = patient.get("name", [{}])[0]
    family_name = name_obj.get("family", "")
    given_name = name_obj.get("given", [""])[0]

    # Extract address
    address_obj = patient.get("address", [{}])[0]
    street = address_obj.get("line", [""])[0] if address_obj.get("line") else ""
    city = address_obj.get("city", "")
    postal_code = address_obj.get("postalCode", "")
    country = address_obj.get("country", "")

    return {
        "PatientID": messy_id,  # Critical - always present
        "FirstName": maybe_missing(given_name),
        "LastName": maybe_missing(family_name),
        "Birthdate": messify_date(patient.get("birthDate", "")),
        "Gender": messify_gender(patient.get("gender", "")),
        "Street": maybe_missing(street),
        "City": maybe_missing(city),
        "PostalCode": maybe_missing(postal_code),
        "Country": maybe_missing(country),
    }


def condition_to_csv_row(condition_data: Dict, messy_patient_id: str) -> Dict:
    """
    Convert FHIR Condition resource to CSV row with quality issues.

    Args:
        condition_data: Dict with 'resource' and 'patient_id'
        messy_patient_id: Already messified patient ID

    Returns:
        Dict representing a CSV row
    """
    condition = condition_data["resource"]
    condition_id = condition.get("id", "")

    # Extract ICD-10-GM code
    code_obj = condition.get("code", {})
    coding = code_obj.get("coding", [{}])[0]
    code = coding.get("code", "")
    system = coding.get("system", "")
    display = code_obj.get("text", "")

    # Messify the condition ID similarly
    messy_condition_id = messify_patient_id(condition_id)

    return {
        "ConditionID": messy_condition_id,  # Critical - always present
        "PatientID": messy_patient_id,  # Critical - always present
        "Code": maybe_missing(code),
        "CodeSystem": maybe_missing(system),
        "Display": maybe_missing(display),
        "RecordedDate": messify_date(condition.get("recordedDate", "")),
    }


def medication_to_csv_row(med_data: Dict, messy_patient_id: str) -> Dict:
    """
    Convert FHIR Medication/MedicationAdministration to CSV row with quality issues.

    Args:
        med_data: Dict with 'administration', 'patient_id', 'medications'
        messy_patient_id: Already messified patient ID

    Returns:
        Dict representing a CSV row
    """
    administration = med_data["administration"]
    medications = med_data["medications"]

    # Get medication reference
    med_ref = administration.get("medicationReference", {}).get("reference", "")
    med_id = med_ref.split("/")[-1] if "/" in med_ref else med_ref

    # Look up medication details
    medication = medications.get(med_id, {})

    # Extract medication code and name
    code_obj = medication.get("code", {})
    coding = code_obj.get("coding", [{}])[0]
    med_code = coding.get("code", "")
    med_name = code_obj.get("text", "")

    # Extract dosage
    dosage = administration.get("dosage", {})
    dose = dosage.get("dose", {})
    dose_value = dose.get("value", "")
    dose_unit = dose.get("unit", "")

    # Status
    status = administration.get("status", "")

    # Effective date
    effective_date = administration.get("effectiveDateTime", "")

    # Messify medication ID
    messy_med_id = messify_patient_id(administration.get("id", ""))

    return {
        "MedicationID": messy_med_id,  # Critical - always present
        "PatientID": messy_patient_id,  # Critical - always present
        "MedicationCode": maybe_missing(med_code),
        "MedicationName": maybe_missing(med_name),
        "DoseValue": maybe_missing(str(dose_value)),
        "DoseUnit": maybe_missing(dose_unit),
        "Status": maybe_missing(status),
        "EffectiveDate": messify_date(effective_date),
    }


def encounter_to_csv_row(encounter_data: Dict, messy_patient_id: str) -> Dict:
    """
    Convert FHIR Encounter resource to CSV row with quality issues.

    Args:
        encounter_data: Dict with 'resource' and 'patient_id'
        messy_patient_id: Already messified patient ID

    Returns:
        Dict representing a CSV row
    """
    encounter = encounter_data["resource"]
    encounter_id = encounter.get("id", "")

    # Extract encounter details
    encounter_class = encounter.get("class", {}).get("code", "")
    status = encounter.get("status", "")

    # Extract period
    period = encounter.get("period", {})
    start_date = period.get("start", "")
    end_date = period.get("end", "")

    # Extract department (serviceType)
    service_type = encounter.get("serviceType", {})
    dept_coding = service_type.get("coding", [{}])[0]
    department = dept_coding.get("display", "")

    # Messify encounter ID
    messy_encounter_id = messify_patient_id(encounter_id)

    return {
        "EncounterID": messy_encounter_id,  # Critical - always present
        "PatientID": messy_patient_id,  # Critical - always present
        "Class": maybe_missing(encounter_class),
        "Status": maybe_missing(status),
        "StartDate": messify_date(start_date),
        "EndDate": messify_date(end_date),
        "Department": maybe_missing(department),
    }


# ============================================================================
# Main Extraction Logic
# ============================================================================


def main():
    """
    Main extraction process: Load FHIR bundles, extract data, introduce
    quality issues, and save to CSV files.
    """
    print("=" * 70)
    print("FHIR to CSV Extractor - Medical Data Integration Pipeline")
    print("=" * 70)
    print()
    print(f"Source: {FHIR_DATA_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Processing: {NUM_PATIENTS} patients")
    print(f"Missing data probability: {MISSING_DATA_PROB * 100}%")
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    # Initialize data containers
    patients_data = []
    conditions_data = []
    medications_data = []
    encounters_data = []

    # Get list of FHIR bundle files
    bundle_files = sorted(FHIR_DATA_DIR.glob("*.json"))[:NUM_PATIENTS]

    print(f"Found {len(bundle_files)} FHIR bundle files")
    print()
    print("Processing bundles...")

    # Process each bundle
    for i, bundle_file in enumerate(bundle_files, 1):
        # Load bundle
        bundle = load_fhir_bundle(bundle_file)

        # Extract patient
        patient = extract_patient(bundle)
        if not patient:
            print(f"⚠️  Warning: No patient found in {bundle_file.name}")
            continue

        # Get original patient ID and messify it
        original_patient_id = patient.get("id", "")
        messy_patient_id = messify_patient_id(original_patient_id)

        # Convert patient to CSV row
        patients_data.append(patient_to_csv_row(patient, messy_patient_id))

        # Extract and convert conditions
        conditions = extract_conditions(bundle, original_patient_id)
        for condition_data in conditions:
            conditions_data.append(
                condition_to_csv_row(condition_data, messy_patient_id)
            )

        # Extract and convert medications
        medications = extract_medications(bundle, original_patient_id)
        for med_data in medications:
            medications_data.append(medication_to_csv_row(med_data, messy_patient_id))

        # Extract and convert encounters
        encounters = extract_encounters(bundle, original_patient_id)
        for encounter_data in encounters:
            encounters_data.append(
                encounter_to_csv_row(encounter_data, messy_patient_id)
            )

        # Progress indicator
        if i % 50 == 0 or i == len(bundle_files):
            print(f"  Processed {i}/{len(bundle_files)} bundles...")

    print()
    print("Extraction complete! Saving to CSV files...")
    print()

    # Save to CSV files
    df_patients = pd.DataFrame(patients_data)
    df_conditions = pd.DataFrame(conditions_data)
    df_medications = pd.DataFrame(medications_data)
    df_encounters = pd.DataFrame(encounters_data)

    df_patients.to_csv(OUTPUT_DIR / "patients.csv", index=False)
    df_conditions.to_csv(OUTPUT_DIR / "conditions.csv", index=False)
    df_medications.to_csv(OUTPUT_DIR / "medications.csv", index=False)
    df_encounters.to_csv(OUTPUT_DIR / "encounters.csv", index=False)

    # Print summary statistics
    print("✅ Data extracted successfully!")
    print()
    print("=" * 70)
    print("Summary Statistics")
    print("=" * 70)
    print(f"  patients.csv:     {len(df_patients):,} rows")
    print(f"  conditions.csv:   {len(df_conditions):,} rows")
    print(f"  medications.csv:  {len(df_medications):,} rows")
    print(f"  encounters.csv:   {len(df_encounters):,} rows")
    print()

    # Data quality report
    print("=" * 70)
    print("Data Quality Issues Introduced (Intentional)")
    print("=" * 70)

    # Calculate missing data percentages
    for name, df in [
        ("patients.csv", df_patients),
        ("conditions.csv", df_conditions),
        ("medications.csv", df_medications),
        ("encounters.csv", df_encounters),
    ]:
        print(f"\n{name}:")
        for col in df.columns:
            missing_pct = (df[col] == "").sum() / len(df) * 100
            if missing_pct > 0:
                print(f"  {col}: {missing_pct:.1f}% missing")

    print()
    print("=" * 70)
    print("Next Steps:")
    print("  1. Review CSV files in data/raw/")
    print("  2. Build transformation pipeline (Phase 2)")
    print("  3. Transform back to clean FHIR resources")
    print("=" * 70)


if __name__ == "__main__":
    main()
