#!/usr/bin/env python3
"""
Validation Against Original FHIR - Medical Data Integration Pipeline

Compares transformed FHIR resources against original MII FHIR bundles
to validate the accuracy of our "reverse engineering" approach.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Configuration
ORIGINAL_FHIR_DIR = Path(
    "data/POLAR_WP_1.1_v2-POLAR_WP1.1_00001-POLAR_WP1.1_01650.json"
)
TRANSFORMED_BUNDLE = Path("data/processed/fhir_resources/fhir_bundle.json")
NUM_TO_VALIDATE = 200  # Should match what we processed


def load_original_bundle(filepath: Path) -> Dict:
    """Load original FHIR bundle."""
    with open(filepath, "r") as f:
        return json.load(f)


def extract_patient_from_bundle(bundle: Dict) -> Dict:
    """Extract Patient resource from bundle."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return {}


def extract_conditions_from_bundle(bundle: Dict) -> List[Dict]:
    """Extract Condition resources from bundle."""
    conditions = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Condition":
            conditions.append(resource)
    return conditions


def normalize_patient_id(id_value: str) -> str:
    """Normalize patient ID for comparison."""
    # Extract just the number portion
    import re

    numbers = re.findall(r"\d+", id_value)
    if numbers:
        return numbers[-1].zfill(5)
    return id_value


def compare_patients(original: Dict, transformed: Dict) -> Dict:
    """
    Compare original and transformed Patient resources.

    Returns dict with comparison results.
    """
    results = {
        "id_match": False,
        "gender_match": False,
        "birthdate_match": False,
        "name_match": False,
        "issues": [],
    }

    # Compare IDs
    orig_id = normalize_patient_id(original.get("id", ""))
    trans_id = transformed.get("id", "")
    results["id_match"] = orig_id == trans_id

    # Compare gender
    results["gender_match"] = original.get("gender") == transformed.get("gender")
    if not results["gender_match"]:
        results["issues"].append(
            f"Gender mismatch: {original.get('gender')} vs {transformed.get('gender')}"
        )

    # Compare birthdate
    orig_bd = original.get("birthDate", "")
    trans_bd = transformed.get("birthDate", "")
    results["birthdate_match"] = orig_bd == trans_bd
    if (
        not results["birthdate_match"] and trans_bd
    ):  # Only flag if we have a transformed date
        results["issues"].append(f"Birthdate mismatch: {orig_bd} vs {trans_bd}")

    # Compare name (family name)
    orig_name = original.get("name", [{}])[0].get("family", "")
    trans_name = (
        transformed.get("name", [{}])[0].get("family", "")
        if transformed.get("name")
        else ""
    )
    results["name_match"] = orig_name == trans_name
    if not results["name_match"] and trans_name:
        results["issues"].append(f"Name mismatch: {orig_name} vs {trans_name}")

    return results


def compare_conditions(original_list: List[Dict], transformed_list: List[Dict]) -> Dict:
    """
    Compare original and transformed Condition resources.

    Returns dict with comparison results.
    """
    results = {
        "count_match": False,
        "codes_match": 0,
        "total_conditions": len(original_list),
        "issues": [],
    }

    # Check if counts match
    results["count_match"] = len(original_list) == len(transformed_list)
    if not results["count_match"]:
        results["issues"].append(
            f"Condition count mismatch: {len(original_list)} vs {len(transformed_list)}"
        )

    # Extract codes from original
    orig_codes = set()
    for cond in original_list:
        code = cond.get("code", {}).get("coding", [{}])[0].get("code")
        if code:
            orig_codes.add(code)

    # Extract codes from transformed
    trans_codes = set()
    for cond in transformed_list:
        code = cond.get("code", {}).get("coding", [{}])[0].get("code")
        if code:
            trans_codes.add(code)

    # Check how many codes match
    matching_codes = orig_codes & trans_codes
    results["codes_match"] = len(matching_codes)
    results["orig_codes"] = orig_codes
    results["trans_codes"] = trans_codes

    if orig_codes != trans_codes:
        missing = orig_codes - trans_codes
        if missing:
            results["issues"].append(f"Missing codes: {missing}")
        extra = trans_codes - orig_codes
        if extra:
            results["issues"].append(f"Extra codes: {extra}")

    return results


def main():
    """
    Main validation process.
    """
    print("=" * 70)
    print("Validation Against Original FHIR")
    print("=" * 70)
    print()

    # Load transformed bundle
    print(f"Loading transformed bundle: {TRANSFORMED_BUNDLE}")
    with open(TRANSFORMED_BUNDLE, "r") as f:
        transformed_bundle = json.load(f)

    # Index transformed resources by patient ID
    transformed_patients = {}
    transformed_conditions_by_patient = defaultdict(list)

    for entry in transformed_bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        if resource_type == "Patient":
            patient_id = resource.get("id")
            transformed_patients[patient_id] = resource

        elif resource_type == "Condition":
            # Extract patient reference
            subject_ref = resource.get("subject", {}).get("reference", "")
            patient_id = subject_ref.split("/")[-1] if "/" in subject_ref else ""
            if patient_id:
                transformed_conditions_by_patient[patient_id].append(resource)

    print(f"✓ Loaded {len(transformed_patients)} transformed patients")
    print(
        f"✓ Loaded {sum(len(v) for v in transformed_conditions_by_patient.values())} transformed conditions"
    )
    print()

    # Load and compare original bundles
    print(f"Comparing against {NUM_TO_VALIDATE} original FHIR bundles...")
    print()

    original_files = sorted(ORIGINAL_FHIR_DIR.glob("*.json"))[:NUM_TO_VALIDATE]

    # Validation statistics
    stats = {
        "total_patients": 0,
        "patients_found": 0,
        "gender_matches": 0,
        "birthdate_matches": 0,
        "name_matches": 0,
        "total_conditions": 0,
        "condition_count_matches": 0,
        "condition_code_matches": 0,
        "total_condition_codes": 0,
    }

    issues_by_patient = {}

    for orig_file in original_files:
        # Load original bundle
        orig_bundle = load_original_bundle(orig_file)

        # Extract original patient
        orig_patient = extract_patient_from_bundle(orig_bundle)
        if not orig_patient:
            continue

        stats["total_patients"] += 1

        # Find corresponding transformed patient
        orig_patient_id = normalize_patient_id(orig_patient.get("id", ""))
        trans_patient = transformed_patients.get(orig_patient_id)

        if not trans_patient:
            issues_by_patient[orig_patient_id] = [
                "Patient not found in transformed data"
            ]
            continue

        stats["patients_found"] += 1

        # Compare patients
        patient_results = compare_patients(orig_patient, trans_patient)

        if patient_results["gender_match"]:
            stats["gender_matches"] += 1
        if patient_results["birthdate_match"]:
            stats["birthdate_matches"] += 1
        if patient_results["name_match"]:
            stats["name_matches"] += 1

        if patient_results["issues"]:
            issues_by_patient[orig_patient_id] = patient_results["issues"]

        # Compare conditions
        orig_conditions = extract_conditions_from_bundle(orig_bundle)
        trans_conditions = transformed_conditions_by_patient.get(orig_patient_id, [])

        if orig_conditions:
            stats["total_conditions"] += len(orig_conditions)

            condition_results = compare_conditions(orig_conditions, trans_conditions)

            if condition_results["count_match"]:
                stats["condition_count_matches"] += 1

            stats["condition_code_matches"] += condition_results["codes_match"]
            stats["total_condition_codes"] += len(
                condition_results.get("orig_codes", set())
            )

    # Print results
    print("=" * 70)
    print("Validation Results")
    print("=" * 70)
    print()

    print(f"PATIENTS ({stats['total_patients']} total)")
    print("-" * 70)
    print(
        f"  Found in transformed data:  {stats['patients_found']}/{stats['total_patients']} ({stats['patients_found']/stats['total_patients']*100:.1f}%)"
    )
    print(
        f"  Gender matches:             {stats['gender_matches']}/{stats['patients_found']} ({stats['gender_matches']/stats['patients_found']*100:.1f}%)"
    )
    print(
        f"  Birthdate matches:          {stats['birthdate_matches']}/{stats['patients_found']} ({stats['birthdate_matches']/stats['patients_found']*100:.1f}%)"
    )
    print(
        f"  Name matches:               {stats['name_matches']}/{stats['patients_found']} ({stats['name_matches']/stats['patients_found']*100:.1f}%)"
    )
    print()

    print(f"CONDITIONS ({stats['total_conditions']} total)")
    print("-" * 70)
    print(
        f"  Count matches per patient:  {stats['condition_count_matches']}/{stats['total_patients']} ({stats['condition_count_matches']/stats['total_patients']*100:.1f}%)"
    )
    print(
        f"  ICD-10 code matches:        {stats['condition_code_matches']}/{stats['total_condition_codes']} ({stats['condition_code_matches']/stats['total_condition_codes']*100:.1f}%)"
    )
    print()

    # Calculate overall accuracy
    total_checks = (
        stats["patients_found"]
        + stats["gender_matches"]
        + stats["birthdate_matches"]
        + stats["name_matches"]
        + stats["condition_code_matches"]
    )
    total_possible = (
        stats["total_patients"]
        + stats["patients_found"] * 3  # gender, birthdate, name
        + stats["total_condition_codes"]
    )

    overall_accuracy = (
        (total_checks / total_possible * 100) if total_possible > 0 else 0
    )

    print("OVERALL ASSESSMENT")
    print("-" * 70)
    print(f"  Overall Accuracy:           {overall_accuracy:.1f}%")
    print(
        f"  Data Recovery Score:        {total_checks}/{total_possible} fields matched"
    )
    print()

    # Show sample issues
    if issues_by_patient:
        print("SAMPLE ISSUES (first 5 patients with issues)")
        print("-" * 70)
        for patient_id, issues in list(issues_by_patient.items())[:5]:
            print(f"  Patient {patient_id}:")
            for issue in issues[:3]:  # First 3 issues
                print(f"    - {issue}")
        print()

    print("=" * 70)
    print("✅ Validation complete!")
    print("=" * 70)
    print()
    print("CONCLUSION:")
    print(
        f"  The transformation pipeline successfully recovered {overall_accuracy:.1f}% of the"
    )
    print("  original FHIR data from the intentionally 'broken' CSV format.")
    print()
    if overall_accuracy >= 85:
        print("  🎯 EXCELLENT: >85% accuracy demonstrates robust ETL capabilities")
    elif overall_accuracy >= 70:
        print("  ✅ GOOD: >70% accuracy shows solid data transformation")
    else:
        print("  ⚠️  FAIR: Some data loss during transformation")
    print()


if __name__ == "__main__":
    main()
