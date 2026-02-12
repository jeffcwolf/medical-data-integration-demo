#!/usr/bin/env python3
"""
Medical Data Integration Pipeline - Main Execution Script

Orchestrates the complete ETL pipeline:
1. Load messy CSV data
2. Validate data quality
3. Transform to FHIR R4 resources
4. Save FHIR bundle
5. Generate quality reports

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.data_validator import DataQualityValidator
from src.fhir_transformer import FHIRTransformer

# Configuration
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed" / "fhir_resources"
OUTPUTS_DIR = Path("outputs")

# Ensure output directories exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def load_csv_data():
    """
    Load all CSV files from raw data directory.

    Returns:
        Tuple of (patients_df, conditions_df, medications_df, encounters_df)
    """
    print("Step 1: Loading CSV data...")
    print(f"  Source: {RAW_DIR}/")

    patients_df = pd.read_csv(RAW_DIR / "patients.csv")
    conditions_df = pd.read_csv(RAW_DIR / "conditions.csv")
    medications_df = pd.read_csv(RAW_DIR / "medications.csv")
    encounters_df = pd.read_csv(RAW_DIR / "encounters.csv")

    print(f"  ✓ Loaded {len(patients_df)} patients")
    print(f"  ✓ Loaded {len(conditions_df)} conditions")
    print(f"  ✓ Loaded {len(medications_df)} medications")
    print(f"  ✓ Loaded {len(encounters_df)} encounters")
    print()

    return patients_df, conditions_df, medications_df, encounters_df


def validate_data(patients_df, conditions_df, medications_df, encounters_df):
    """
    Run data quality validation checks.

    Args:
        patients_df: Patients DataFrame
        conditions_df: Conditions DataFrame
        medications_df: Medications DataFrame
        encounters_df: Encounters DataFrame

    Returns:
        Validation report dict
    """
    print("Step 2: Validating data quality...")

    validator = DataQualityValidator()

    # Validate each table
    patient_results = validator.validate_patient_data(patients_df)
    condition_results = validator.validate_condition_data(conditions_df)
    medication_results = validator.validate_medication_data(medications_df)

    # Check referential integrity
    integrity_results = validator.validate_referential_integrity(
        conditions_df, medications_df, encounters_df, patients_df
    )

    # Generate comprehensive report
    report = validator.generate_report(
        patient_results, condition_results, medication_results, integrity_results
    )

    # Print summary
    summary = report["summary"]
    print(f"  Quality Score: {summary['quality_score']}/100")
    print(f"  Errors: {summary['total_errors']}")
    print(f"  Warnings: {summary['total_warnings']}")

    if summary["total_errors"] > 0:
        print(f"\n  ⚠️  Found {summary['total_errors']} data quality errors")
        print("     (These will be handled during transformation)")

    print()

    return report


def transform_to_fhir(patients_df, conditions_df, medications_df):
    """
    Transform CSV data to FHIR resources.

    Args:
        patients_df: Patients DataFrame
        conditions_df: Conditions DataFrame
        medications_df: Medications DataFrame

    Returns:
        Tuple of (fhir_resources dict, transformer instance)
    """
    print("Step 3: Transforming to FHIR R4 resources...")

    transformer = FHIRTransformer()

    # Transform all data
    fhir_resources = transformer.transform_all(
        patients_df, conditions_df, medications_df
    )

    print(f"  ✓ Created {len(fhir_resources['Patient'])} Patient resources")
    print(f"  ✓ Created {len(fhir_resources['Condition'])} Condition resources")
    print(f"  ✓ Created {len(fhir_resources['Medication'])} Medication resources")
    print(
        f"  ✓ Created {len(fhir_resources['MedicationAdministration'])} MedicationAdministration resources"
    )
    print()

    return fhir_resources, transformer


def save_fhir_resources(fhir_resources, transformer):
    """
    Save FHIR resources to files.

    Args:
        fhir_resources: Dict of FHIR resource lists
        transformer: FHIRTransformer instance
    """
    print("Step 4: Saving FHIR resources...")

    # Create bundle
    bundle = transformer.create_bundle(fhir_resources)

    # Save bundle as JSON
    bundle_path = PROCESSED_DIR / "fhir_bundle.json"
    with open(bundle_path, "w", encoding="utf-8") as f:
        f.write(bundle.json(indent=2))

    print(f"  ✓ Saved FHIR Bundle: {bundle_path}")
    print(f"    Total resources: {len(bundle.entry)}")

    # Also save individual resource types for easy browsing
    for resource_type, resources in fhir_resources.items():
        if resources:
            type_dir = PROCESSED_DIR / resource_type
            type_dir.mkdir(exist_ok=True)

            for resource in resources[:10]:  # Save first 10 as examples
                resource_path = type_dir / f"{resource.id}.json"
                with open(resource_path, "w", encoding="utf-8") as f:
                    f.write(resource.json(indent=2))

            print(
                f"  ✓ Saved {min(10, len(resources))} example {resource_type} resources to {type_dir}/"
            )

    print()


def save_quality_report(validation_report, transformation_stats):
    """
    Save comprehensive quality report.

    Args:
        validation_report: Validation results
        transformation_stats: Transformation statistics
    """
    print("Step 5: Generating quality report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_version": "1.0.0",
        "data_quality": validation_report,
        "transformation": transformation_stats,
    }

    # Save as JSON
    report_path = OUTPUTS_DIR / "quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"  ✓ Saved quality report: {report_path}")

    # Save human-readable summary
    summary_path = OUTPUTS_DIR / "pipeline_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("Medical Data Integration Pipeline - Execution Summary\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Execution Time: {report['timestamp']}\n\n")

        # Data Quality Summary
        f.write("DATA QUALITY SUMMARY\n")
        f.write("-" * 70 + "\n")
        summary = validation_report["summary"]
        f.write(f"Total Patients:    {summary['total_patients']}\n")
        f.write(f"Total Conditions:  {summary['total_conditions']}\n")
        f.write(f"Total Medications: {summary['total_medications']}\n")
        f.write(f"Quality Score:     {summary['quality_score']}/100\n")
        f.write(f"Errors:            {summary['total_errors']}\n")
        f.write(f"Warnings:          {summary['total_warnings']}\n\n")

        # Transformation Summary
        f.write("TRANSFORMATION SUMMARY\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Patients Transformed:  {transformation_stats['patients_successful']}/{transformation_stats['patients_processed']} "
        )
        if "patient_success_rate" in transformation_stats:
            f.write(f"({transformation_stats['patient_success_rate']}%)\n")
        else:
            f.write("\n")

        f.write(
            f"Conditions Transformed: {transformation_stats['conditions_successful']}/{transformation_stats['conditions_processed']} "
        )
        if "condition_success_rate" in transformation_stats:
            f.write(f"({transformation_stats['condition_success_rate']}%)\n")
        else:
            f.write("\n")

        f.write(
            f"Medications Transformed: {transformation_stats['medications_successful']}/{transformation_stats['medications_processed']} "
        )
        if "medication_success_rate" in transformation_stats:
            f.write(f"({transformation_stats['medication_success_rate']}%)\n")
        else:
            f.write("\n")

        f.write(f"\nTransformation Errors: {len(transformation_stats['errors'])}\n")

        # Issues
        if validation_report["all_issues"]:
            f.write("\nDATA QUALITY ISSUES\n")
            f.write("-" * 70 + "\n")
            for issue in validation_report["all_issues"][:20]:  # First 20
                severity = issue["severity"]
                f.write(f"[{severity}] ")
                if "field" in issue:
                    f.write(f"{issue['field']}: ")
                elif "table" in issue:
                    f.write(f"{issue['table']}: ")
                f.write(f"{issue['message']}\n")

    print(f"  ✓ Saved summary: {summary_path}")
    print()


def main():
    """
    Main pipeline execution.
    """
    print("\n" + "=" * 70)
    print("Medical Data Integration Pipeline")
    print("ETL: Messy CSV → Clean FHIR R4 Resources")
    print("=" * 70)
    print()

    try:
        # Step 1: Load data
        patients_df, conditions_df, medications_df, encounters_df = load_csv_data()

        # Step 2: Validate data quality
        validation_report = validate_data(
            patients_df, conditions_df, medications_df, encounters_df
        )

        # Step 3: Transform to FHIR
        fhir_resources, transformer = transform_to_fhir(
            patients_df, conditions_df, medications_df
        )

        # Step 4: Save FHIR resources
        save_fhir_resources(fhir_resources, transformer)

        # Step 5: Generate reports
        transformation_stats = transformer.get_statistics()
        save_quality_report(validation_report, transformation_stats)

        # Print final summary
        transformer.print_summary()

        print("\n" + "=" * 70)
        print("✅ Pipeline completed successfully!")
        print("=" * 70)
        print("\nOutputs:")
        print(f"  - FHIR Bundle: {PROCESSED_DIR}/fhir_bundle.json")
        print(f"  - Quality Report: {OUTPUTS_DIR}/quality_report.json")
        print(f"  - Summary: {OUTPUTS_DIR}/pipeline_summary.txt")
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ Pipeline failed!")
        print("=" * 70)
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
