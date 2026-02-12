# FHIR Bundle Structure Analysis

**Date:** 2026-02-12
**Data Source:** MII Kerndatensatz Test Data (1,650 bundles)

## Bundle Overview

Each FHIR bundle is a **Transaction Bundle** containing official MII (Medizininformatik-Initiative) test data.

### Structure per Bundle

Each bundle contains **8 entries** with the following resource types:

| Resource Type | Count | Purpose |
|---------------|-------|---------|
| Patient | 1 | Patient demographics |
| Encounter | 2 | Hospital encounters (1 main, 1 department) |
| Condition | 2 | Diagnoses (ICD-10-GM) |
| Medication | 1 | Medication definition (ATC codes) |
| MedicationAdministration | 1 | Medication administration event |
| Consent | 1 | Research consent (MII consent framework) |

**Note:** No Observation resources found in sampled bundles. Focus extraction on available resource types.

## Key Findings

### Patient Resource
- **ID format:** `Polar-WP1.1-XXXXX` (5-digit number)
- **Names:** German test names (e.g., "Mustermann, Max_01")
- **Gender:** "male" or "female" (FHIR standard values)
- **Birthdate:** ISO format `YYYY-MM-DD` (e.g., "1950-01-01")
- **Address:** German addresses
  - Street: "Musterstraße 1"
  - City: "Bonn"
  - Postal Code: "53121"
  - Country: "DE"
- **MII Profile:** `https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/Patient`

### Encounter Resource
- **Two encounters per patient:**
  1. Main inpatient encounter (`IMP` class)
  2. Department-level encounter (e.g., "Unfallchirurgie" - Trauma Surgery)
- **Status:** "finished"
- **Period:** Date range with timezone (`2019-01-01T00:00:00+01:00`)
- **References:** Links to Patient and Condition resources
- **German Context:** Department codes use `http://fhir.de/CodeSystem/dkgev/Fachabteilungsschluessel`

### Condition Resource
- **Coding System:** ICD-10-GM (German modification)
  - System: `http://fhir.de/CodeSystem/bfarm/icd-10-gm`
  - Version: "2020"
- **Examples:**
  - Code: "M80.00" → Text: "Osteroporose"
  - Code: "S02.0" → Text: "Sturz" (Fall)
- **Recorded Date:** ISO datetime format with timezone
- **MII Profile:** `https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose`

### Medication Resources
- **Medication Resource:**
  - ATC coding: `http://fhir.de/CodeSystem/bfarm/atc`
  - Example: "N06AA09" → "ATC_AMITRYPTILIN"
  - Strength: 10 mg per "Filmtabletten" (film-coated tablet)
  - Units: UCUM standard (`http://unitsofmeasure.org`)

- **MedicationAdministration:**
  - Status: "completed"
  - Links to Medication, Patient, and Encounter
  - Dosage information with UCUM units
  - Effective datetime with timezone

### Consent Resource
- MII research consent framework
- Structured provisions (IDAT_erheben, MDAT_speichern, etc.)
- German GDPR context
- Period-based permissions

## Extraction Strategy

### Phase 1: "Breaking" FHIR → CSV

Based on this analysis, we'll extract to 4 CSV files:

1. **patients.csv**
   - PatientID, FirstName, LastName, Birthdate, Gender, Street, City, PostalCode, Country

2. **conditions.csv**
   - ConditionID, PatientID, Code, CodeSystem, Display, RecordedDate

3. **medications.csv**
   - MedicationID, PatientID, MedicationCode, MedicationName, Strength, Unit, Status, EffectiveDate

4. **encounters.csv** (optional - for completeness)
   - EncounterID, PatientID, Class, Status, StartDate, EndDate, Department

### Data Quality Issues to Introduce

When extracting, we'll intentionally introduce:

1. **ID format variations:**
   - Original: `Polar-WP1.1-00001`
   - Variations: `P-00001`, `PAT00001`, `00001`, `WP1-1`

2. **Date format inconsistencies:**
   - Original: `2019-01-01`
   - Variations: `01.01.2019`, `2019/01/01`, `01-01-2019`

3. **Gender variations:**
   - Original: `male`, `female`
   - Variations: `M`, `m`, `männlich`, `W`, `w`, `weiblich`

4. **Missing data:** Randomly remove 10-15% of non-critical fields

5. **German special characters:** Preserve ä, ö, ü, ß to test UTF-8 handling

## Statistics

- **Total bundles:** 1,650
- **Bundle size:** ~629 lines JSON (formatted)
- **Consistency:** Very high - all sampled bundles have identical structure
- **MII Compliance:** All resources reference official MII profiles

## Next Steps

1. ✅ Exploration complete
2. → Set up project directories
3. → Write extraction script (`src/fhir_to_csv_extractor.py`)
4. → Test on 100-200 bundles
5. → Build transformation pipeline
