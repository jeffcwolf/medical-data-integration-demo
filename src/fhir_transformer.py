#!/usr/bin/env python3
"""
FHIR Transformer - Medical Data Integration Pipeline

Transforms messy CSV data into clean HL7 FHIR R4 compliant resources.
Uses fhir.resources library for FHIR R4 model validation.

Author: Medical Data Integration Demo
Date: 2026-02-12
"""

from typing import List, Optional, Dict
import pandas as pd
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.medicationadministration import MedicationAdministration
from fhir.resources.medication import Medication
from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.address import Address
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.dosage import Dosage
from fhir.resources.quantity import Quantity
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.codeablereference import CodeableReference

from src.utils import (
    clean_patient_id,
    normalize_date,
    normalize_gender,
    normalize_code_system,
    clean_string,
    validate_date_range
)


class FHIRTransformer:
    """
    Transforms hospital data to FHIR R4 resources.

    Handles:
    - Patient demographics
    - Condition/diagnosis records (ICD-10-GM)
    - Medication administration records (ATC codes)
    """

    def __init__(self):
        """Initialize transformer with empty statistics."""
        self.stats = {
            'patients_processed': 0,
            'patients_successful': 0,
            'patients_failed': 0,
            'conditions_processed': 0,
            'conditions_successful': 0,
            'conditions_failed': 0,
            'medications_processed': 0,
            'medications_successful': 0,
            'medications_failed': 0,
            'errors': []
        }

        # Cache for created Medication resources (to avoid duplicates)
        self.medication_cache: Dict[str, Medication] = {}

    def transform_patient(self, patient_row: pd.Series) -> Optional[Patient]:
        """
        Transform patient CSV row to FHIR Patient resource.

        Args:
            patient_row: Pandas Series with patient data

        Returns:
            FHIR Patient resource or None if transformation fails
        """
        self.stats['patients_processed'] += 1

        try:
            # Clean and normalize data
            patient_id = clean_patient_id(str(patient_row.get('PatientID', '')))
            if not patient_id:
                raise ValueError("Missing PatientID")

            # Normalize names
            family_name = clean_string(str(patient_row.get('LastName', '')))
            given_name = clean_string(str(patient_row.get('FirstName', '')))

            # Normalize gender
            gender = normalize_gender(str(patient_row.get('Gender', '')))

            # Normalize birthdate
            birthdate = normalize_date(str(patient_row.get('Birthdate', '')))

            # Build FHIR Patient resource
            patient = Patient(
                id=patient_id,
                identifier=[
                    Identifier(
                        system="https://POLARWP.de/pid",
                        value=patient_id
                    )
                ]
            )

            # Add name (if available)
            if family_name or given_name:
                given_names = [given_name] if given_name else []
                patient.name = [
                    HumanName(
                        use="official",
                        family=family_name if family_name else None,
                        given=given_names if given_names else None
                    )
                ]

            # Add gender
            patient.gender = gender

            # Add birthdate (if valid)
            if birthdate and validate_date_range(birthdate, min_year=1900, max_year=2020):
                patient.birthDate = birthdate

            # Add address (if available)
            street = clean_string(str(patient_row.get('Street', '')))
            city = clean_string(str(patient_row.get('City', '')))
            postal_code = clean_string(str(patient_row.get('PostalCode', '')))
            country = clean_string(str(patient_row.get('Country', '')))

            if any([street, city, postal_code, country]):
                address = Address(type="both")

                if street:
                    address.line = [street]
                if city:
                    address.city = city
                if postal_code:
                    address.postalCode = postal_code
                if country:
                    address.country = country

                patient.address = [address]

            self.stats['patients_successful'] += 1
            return patient

        except Exception as e:
            self.stats['patients_failed'] += 1
            self.stats['errors'].append({
                'resource_type': 'Patient',
                'id': str(patient_row.get('PatientID', 'unknown')),
                'error': str(e)
            })
            return None

    def transform_condition(self, condition_row: pd.Series) -> Optional[Condition]:
        """
        Transform condition CSV row to FHIR Condition resource.

        Args:
            condition_row: Pandas Series with condition data

        Returns:
            FHIR Condition resource or None if transformation fails
        """
        self.stats['conditions_processed'] += 1

        try:
            # Clean and normalize data
            condition_id = clean_patient_id(str(condition_row.get('ConditionID', '')))
            patient_id = clean_patient_id(str(condition_row.get('PatientID', '')))

            if not condition_id or not patient_id:
                raise ValueError("Missing ConditionID or PatientID")

            # Extract code information
            code = clean_string(str(condition_row.get('Code', '')))
            code_system = normalize_code_system(
                str(condition_row.get('CodeSystem', ''))
            )
            display = clean_string(str(condition_row.get('Display', '')))

            # Normalize recorded date
            recorded_date = normalize_date(str(condition_row.get('RecordedDate', '')))

            # Build FHIR Condition resource
            # clinicalStatus is required in FHIR R4
            condition = Condition(
                id=condition_id,
                subject=Reference(reference=f"Patient/{patient_id}"),
                clinicalStatus=CodeableConcept(
                    coding=[Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                        code="active"
                    )]
                )
            )

            # Add identifier
            condition.identifier = [
                Identifier(value=condition_id)
            ]

            # Add code (if available)
            if code and code_system:
                coding = Coding(
                    system=code_system,
                    code=code
                )
                if display:
                    coding.display = display

                condition.code = CodeableConcept(coding=[coding])
                if display:
                    condition.code.text = display
            elif code:
                # Code without system - use text only
                condition.code = CodeableConcept(text=code)

            # Add recorded date (if valid)
            if recorded_date and validate_date_range(recorded_date, min_year=2000, max_year=2030):
                condition.recordedDate = recorded_date

            self.stats['conditions_successful'] += 1
            return condition

        except Exception as e:
            self.stats['conditions_failed'] += 1
            self.stats['errors'].append({
                'resource_type': 'Condition',
                'id': str(condition_row.get('ConditionID', 'unknown')),
                'error': str(e)
            })
            return None

    def transform_medication_administration(
        self,
        medication_row: pd.Series
    ) -> Optional[tuple[Optional[Medication], Optional[MedicationAdministration]]]:
        """
        Transform medication CSV row to FHIR Medication and MedicationAdministration resources.

        Args:
            medication_row: Pandas Series with medication data

        Returns:
            Tuple of (Medication, MedicationAdministration) or (None, None) if transformation fails
        """
        self.stats['medications_processed'] += 1

        try:
            # Clean and normalize data
            med_admin_id = clean_patient_id(str(medication_row.get('MedicationID', '')))
            patient_id = clean_patient_id(str(medication_row.get('PatientID', '')))

            if not med_admin_id or not patient_id:
                raise ValueError("Missing MedicationID or PatientID")

            # Extract medication information
            med_code = clean_string(str(medication_row.get('MedicationCode', '')))
            med_name = clean_string(str(medication_row.get('MedicationName', '')))
            dose_value = clean_string(str(medication_row.get('DoseValue', '')))
            dose_unit = clean_string(str(medication_row.get('DoseUnit', '')))
            status = clean_string(str(medication_row.get('Status', 'completed')))
            effective_date = normalize_date(str(medication_row.get('EffectiveDate', '')))

            # Create or retrieve Medication resource
            medication = None
            if med_code:
                # Check cache first
                if med_code in self.medication_cache:
                    medication = self.medication_cache[med_code]
                else:
                    # Create new Medication resource
                    medication = Medication(
                        id=f"Medication-{med_code}",
                        identifier=[Identifier(value=f"Medication-{med_code}")]
                    )

                    # Add code (ATC or other)
                    code_system = "http://fhir.de/CodeSystem/bfarm/atc"
                    if med_code.startswith('PZN_') or med_code.isdigit():
                        code_system = "http://fhir.de/CodeSystem/ifa/pzn"
                        med_code = med_code.replace('PZN_', '')

                    coding = Coding(
                        system=code_system,
                        code=med_code
                    )

                    medication.code = CodeableConcept(coding=[coding])
                    if med_name:
                        medication.code.text = med_name

                    # Cache it
                    self.medication_cache[med_code] = medication

            # Create MedicationAdministration resource
            # Normalize status to FHIR valueSet
            fhir_status = status.lower().replace('-', '') if status else 'completed'
            if fhir_status not in ['inprogress', 'notdone', 'onhold', 'completed', 'enteredinerror', 'stopped', 'unknown']:
                fhir_status = 'completed'

            # Determine occurenceDateTime value
            if effective_date and validate_date_range(effective_date, min_year=2000, max_year=2030):
                occurence_dt = effective_date
            else:
                occurence_dt = "2020-01-01"  # Default

            # Determine medication field (required - must be Reference or CodeableConcept)
            med_admin_params = {
                'id': med_admin_id,
                'status': fhir_status,
                'subject': Reference(reference=f"Patient/{patient_id}"),
                'occurenceDateTime': occurence_dt
            }

            if medication:
                med_admin_params['medication'] = CodeableReference(
                    reference=Reference(reference=f"Medication/{medication.id}")
                )
            elif med_name:
                med_admin_params['medication'] = CodeableReference(
                    concept=CodeableConcept(text=med_name)
                )
            else:
                med_admin_params['medication'] = CodeableReference(
                    concept=CodeableConcept(text="Unknown Medication")
                )

            med_admin = MedicationAdministration(**med_admin_params)

            # Note: Dosage structure in FHIR R4 is complex (uses doseAndRate)
            # Simplified for this demo - focus on core transformation
            # In production, would implement full dosage structure

            self.stats['medications_successful'] += 1
            return (medication, med_admin)

        except Exception as e:
            self.stats['medications_failed'] += 1
            self.stats['errors'].append({
                'resource_type': 'MedicationAdministration',
                'id': str(medication_row.get('MedicationID', 'unknown')),
                'error': str(e)
            })
            return (None, None)

    def transform_all(
        self,
        patients_df: pd.DataFrame,
        conditions_df: pd.DataFrame,
        medications_df: pd.DataFrame
    ) -> Dict[str, List]:
        """
        Transform all CSV data to FHIR resources.

        Args:
            patients_df: Patients DataFrame
            conditions_df: Conditions DataFrame
            medications_df: Medications DataFrame

        Returns:
            Dict with lists of FHIR resources by type
        """
        fhir_resources = {
            'Patient': [],
            'Condition': [],
            'Medication': [],
            'MedicationAdministration': []
        }

        print("Transforming patients...")
        for _, row in patients_df.iterrows():
            patient = self.transform_patient(row)
            if patient:
                fhir_resources['Patient'].append(patient)

        print("Transforming conditions...")
        for _, row in conditions_df.iterrows():
            condition = self.transform_condition(row)
            if condition:
                fhir_resources['Condition'].append(condition)

        print("Transforming medications...")
        for _, row in medications_df.iterrows():
            medication, med_admin = self.transform_medication_administration(row)
            if medication and medication.id not in [m.id for m in fhir_resources['Medication']]:
                fhir_resources['Medication'].append(medication)
            if med_admin:
                fhir_resources['MedicationAdministration'].append(med_admin)

        return fhir_resources

    def create_bundle(self, resources: Dict[str, List]) -> Bundle:
        """
        Create FHIR Bundle (collection) from all resources.

        Args:
            resources: Dict of resource lists by type

        Returns:
            FHIR Bundle resource
        """
        entries = []

        # Add all resources to bundle
        for resource_type, resource_list in resources.items():
            for resource in resource_list:
                entry = BundleEntry(
                    fullUrl=f"{resource_type}/{resource.id}",
                    resource=resource
                )
                entries.append(entry)

        bundle = Bundle(
            type="collection",
            entry=entries
        )

        return bundle

    def get_statistics(self) -> Dict:
        """
        Get transformation statistics.

        Returns:
            Dict with transformation stats and success rates
        """
        stats = self.stats.copy()

        # Calculate success rates
        if stats['patients_processed'] > 0:
            stats['patient_success_rate'] = round(
                (stats['patients_successful'] / stats['patients_processed']) * 100, 2
            )

        if stats['conditions_processed'] > 0:
            stats['condition_success_rate'] = round(
                (stats['conditions_successful'] / stats['conditions_processed']) * 100, 2
            )

        if stats['medications_processed'] > 0:
            stats['medication_success_rate'] = round(
                (stats['medications_successful'] / stats['medications_processed']) * 100, 2
            )

        return stats

    def print_summary(self):
        """Print transformation summary to console."""
        stats = self.get_statistics()

        print("\n" + "=" * 70)
        print("Transformation Summary")
        print("=" * 70)

        print(f"\nPatients:")
        print(f"  Processed: {stats['patients_processed']}")
        print(f"  Successful: {stats['patients_successful']}")
        print(f"  Failed: {stats['patients_failed']}")
        if 'patient_success_rate' in stats:
            print(f"  Success Rate: {stats['patient_success_rate']}%")

        print(f"\nConditions:")
        print(f"  Processed: {stats['conditions_processed']}")
        print(f"  Successful: {stats['conditions_successful']}")
        print(f"  Failed: {stats['conditions_failed']}")
        if 'condition_success_rate' in stats:
            print(f"  Success Rate: {stats['condition_success_rate']}%")

        print(f"\nMedications:")
        print(f"  Processed: {stats['medications_processed']}")
        print(f"  Successful: {stats['medications_successful']}")
        print(f"  Failed: {stats['medications_failed']}")
        if 'medication_success_rate' in stats:
            print(f"  Success Rate: {stats['medication_success_rate']}%")

        print(f"\nTotal Errors: {len(stats['errors'])}")

        if stats['errors'] and len(stats['errors']) <= 10:
            print("\nError Details:")
            for error in stats['errors'][:10]:
                print(f"  {error['resource_type']} ({error['id']}): {error['error']}")
        elif stats['errors']:
            print(f"\n(Showing first 10 of {len(stats['errors'])} errors)")
            for error in stats['errors'][:10]:
                print(f"  {error['resource_type']} ({error['id']}): {error['error']}")

        print("=" * 70)
