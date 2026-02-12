# 🏥 Medical Data Integration Pipeline

**ETL Demonstration: Transforming Messy Hospital Data → Clean HL7 FHIR R4 Resources**

[![FHIR R4](https://img.shields.io/badge/FHIR-R4-blue)](http://hl7.org/fhir/R4/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![MII Kerndatensatz](https://img.shields.io/badge/MII-Kerndatensatz-green)](https://www.medizininformatik-initiative.de/)

---

## 📋 Overview

This project demonstrates a complete ETL (Extract, Transform, Load) pipeline that transforms messy hospital data into HL7 FHIR R4 compliant resources, using **official German MII (Medizininformatik-Initiative) test data**.

**Purpose:** Created as a demonstration project for the **Data Engineer/Data Scientist position at BIH@Charité Datenintegrationszentrum**, showcasing capabilities in medical data transformation, FHIR standards, and data quality assurance.

### 🎯 Key Achievement

**87.7% data recovery** from intentionally "broken" CSV files with realistic quality issues (format inconsistencies, missing values, German terminology variations).

---

## ✨ Features

- ✅ **"Reverse Engineering" Approach** - Clean FHIR → Messy CSV → Clean FHIR → Validation
- ✅ **Comprehensive Data Quality Validation** - Completeness, consistency, referential integrity
- ✅ **FHIR R4 Compliance** - Patient, Condition, Medication, MedicationAdministration resources
- ✅ **German Medical Context** - ICD-10-GM codes, ATC codes, German terminology
- ✅ **MII Kerndatensatz Profile Compliance** - Uses official German test data infrastructure
- ✅ **Robust Data Normalization** - ID formats, dates, gender values, code systems
- ✅ **Interactive HTML Dashboard** - Visual presentation of results (GitHub Pages ready)
- ✅ **Zero Transformation Errors** - 100% success rate on all resource types

---

## 📊 Results Summary

| Metric | Value |
|--------|-------|
| **Patients Transformed** | 200/200 (100%) |
| **Conditions Transformed** | 400/400 (100%) |
| **Medications Transformed** | 181/181 (100%) |
| **Total FHIR Resources** | 896 |
| **Data Recovery Accuracy** | 87.7% |
| **Transformation Errors** | 0 |
| **Quality Score** | 100/100 |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- ~2GB disk space for test data
- ~5 minutes execution time

### Installation

```bash
# 1. Clone the repository
git clone https://codeberg.org/YOUR-USERNAME/YOUR-REPO
# Or: git clone https://github.com/YOUR-USERNAME/YOUR-REPO
cd YOUR-REPO

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download MII test data
# Download from: https://github.com/medizininformatik-initiative/kerndatensatz-testdaten
# Extract to: data/POLAR_WP_1.1_v2-POLAR_WP1.1_00001-POLAR_WP1.1_01650.json/
```

### Running the Pipeline

```bash
# Phase 1: Extract FHIR → CSV (with intentional quality issues)
python3 src/fhir_to_csv_extractor.py

# Phase 2-3: Validate & Transform CSV → FHIR
PYTHONPATH=. python3 src/pipeline.py

# Phase 4: Validate against original FHIR
PYTHONPATH=. python3 src/validate_against_original.py

# View the dashboard
open dashboard/index.html
```

---

## 🏗️ Architecture

### Pipeline Overview

```
MII FHIR Bundles (1,650 files)
        ↓
   [EXTRACTION]  → Introduce quality issues
        ↓
    Messy CSV (patients.csv, conditions.csv, medications.csv)
        ↓
   [VALIDATION]  → Quality checks, integrity validation
        ↓
 [TRANSFORMATION] → Normalize & clean data
        ↓
    Clean FHIR R4 Resources (896 resources)
        ↓
   [VALIDATION]  → Compare against original (87.7% recovery)
```

### Technology Stack

- **Language:** Python 3.11
- **FHIR Library:** fhir.resources 7.1.0 (FHIR R4)
- **Data Processing:** pandas, pydantic
- **Standards:** HL7 FHIR R4, ICD-10-GM, ATC
- **Visualization:** HTML + Chart.js

---

## 📁 Project Structure

```
medical-data-integration-demo/
├── src/                              # Source code
│   ├── fhir_to_csv_extractor.py      # Phase 1: FHIR → CSV
│   ├── utils.py                      # Normalization helpers
│   ├── data_validator.py             # Phase 2: Quality validation
│   ├── fhir_transformer.py           # Phase 3: CSV → FHIR
│   ├── pipeline.py                   # Main orchestration
│   └── validate_against_original.py  # Phase 4: Accuracy validation
│
├── tests/                            # Unit tests (pytest)
│   ├── test_extractor.py
│   ├── test_validator.py
│   └── test_transformer.py
│
├── data/                             # Data files (gitignored)
│   ├── POLAR_WP_1.1_v2-.../         # Original MII FHIR (1,650 files)
│   ├── raw/                          # Messy CSV (generated)
│   └── processed/                    # Clean FHIR (output)
│
├── docs/                             # Documentation
│   ├── mapping_documentation.md      # FHIR field mappings
│   ├── data_protection.md            # Privacy & GDPR considerations
│   └── technical_documentation.md    # Architecture & design
│
├── dashboard/                        # Interactive HTML dashboard
│   └── index.html                    # GitHub Pages ready
│
├── outputs/                          # Generated reports
│   ├── quality_report.json
│   └── pipeline_summary.txt
│
├── requirements.txt
└── README.md                         # This file
```

---

## 🔍 Data Quality Issues Handled

The pipeline successfully handles realistic hospital data quality issues:

| Issue | Input Example | Output (FHIR) | Status |
|-------|---------------|---------------|--------|
| **ID Format Variations** | `P-00001`, `PAT00002`, `00003` | `00001`, `00002`, `00003` | ✅ Normalized |
| **Date Format Variations** | `01.01.1950`, `1950/01/01` | `1950-01-01` (ISO 8601) | ✅ Normalized |
| **Gender Inconsistencies** | `M`, `male`, `männlich`, `W` | `male`, `female` (FHIR valueSet) | ✅ Normalized |
| **Missing Data** | ~12% random missing values | Handled with defaults/omit | ⚠️ Partial |
| **German Characters** | `Müller`, `Schröder`, `Weiß` | UTF-8 preserved | ✅ Preserved |
| **ICD-10-GM Codes** | German diagnosis codes | `http://fhir.de/CodeSystem/bfarm/icd-10-gm` | ✅ Standardized |
| **ATC Codes** | Medication codes | `http://fhir.de/CodeSystem/bfarm/atc` | ✅ Standardized |

---

## 📈 Validation Results

Compared transformed FHIR resources against original MII FHIR bundles:

### Patient Demographics
- ✅ **100%** patients found in transformed data
- ✅ **89.0%** gender values match
- ✅ **86.5%** names match
- ⚠️ **67.5%** birthdates match (intentionally broken dates)

### Diagnosis Codes (ICD-10-GM)
- ✅ **100%** condition count per patient matches
- ✅ **91.5%** ICD-10-GM codes match

### Overall
- 🎯 **87.7% data recovery** - Excellent for messy real-world data
- 📊 **1,052/1,200 fields** successfully matched

---

## 🎨 Interactive Dashboard

View the live demonstration dashboard:

**Features:**
- 📊 Interactive charts (success rates, validation metrics)
- 📋 Sample FHIR resources with syntax highlighting
- 📈 Data quality metrics visualization
- 📄 Before/after transformation comparison

**Deployment:**
- **GitHub Pages:** Host at `https://YOUR-USERNAME.github.io/YOUR-REPO/`
- **Vercel:** One-click deployment
- **Local:** `open dashboard/index.html`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_transformer.py -v

# Code quality
black src/ tests/          # Format
flake8 src/ tests/         # Lint
```

---

## 📚 Documentation

Comprehensive documentation available in `/docs`:

- **[FHIR Mapping Documentation](docs/mapping_documentation.md)** - Detailed field-by-field mapping rules
- **[Data Protection Considerations](docs/data_protection.md)** - GDPR, MII consent, pseudonymization
- **[Technical Documentation](docs/technical_documentation.md)** - Architecture, design decisions, scaling

---

## 🌟 Key Highlights for BIH@Charité

### Why This Project is Relevant

1. **German Medical Informatics Context**
   - Uses official MII test data infrastructure
   - ICD-10-GM and ATC coding systems
   - German terminology handling (ä, ö, ü, ß)
   - MII Kerndatensatz profile compliance

2. **Real-World Data Challenges**
   - Handles messy hospital source systems
   - Data quality validation and reporting
   - Referential integrity checks
   - Robust error handling

3. **FHIR R4 Expertise**
   - Patient, Condition, Medication resources
   - FHIR bundle creation
   - Profile compliance
   - Validation against standards

4. **Data Protection Awareness**
   - Pseudonymization strategies
   - GDPR compliance considerations
   - MII consent framework understanding
   - Documented privacy-by-design

5. **ETL Pipeline Development**
   - Complete extraction, transformation, loading
   - Quality assurance at every step
   - Validation against ground truth
   - Performance considerations

---

## 🔄 Workflow

### "Reverse Engineering" Approach

This project demonstrates a unique validation approach:

1. **Start with Clean FHIR** - Official MII test data (gold standard)
2. **Extract to CSV** - Intentionally introduce realistic quality issues
3. **Transform back to FHIR** - Apply normalization and cleaning
4. **Validate** - Compare output against original (87.7% recovery)

**Advantage:** Proves the pipeline works because we have ground truth to validate against.

---

## ⚙️ Configuration

Key settings in `src/fhir_to_csv_extractor.py`:

```python
NUM_PATIENTS = 200              # Number of patients to process
MISSING_DATA_PROB = 0.12        # 12% missing data
ID_VARIATION_ENABLED = True     # Introduce ID format variations
DATE_VARIATION_ENABLED = True   # Introduce date format variations
GENDER_VARIATION_ENABLED = True # Introduce gender value variations
```

---

## 🚧 Known Limitations

**Intentional Simplifications (for demo):**

- **Dosage Details:** MedicationAdministration dosage simplified (no `doseAndRate` structure)
  - Production would include full dosage/timing/route details

- **Dataset Size:** 200 patients (demo scale)
  - Production would process 10,000+ patients using Spark/multiprocessing

- **Resource Types:** Limited to Patient, Condition, Medication
  - Production would include Encounter, Procedure, Observation, etc.

**These simplifications focus the demonstration on core ETL capabilities rather than comprehensive FHIR implementation.**

---

## 🔮 Future Enhancements

**Technical:**
- [ ] Multiprocessing for parallel transformation
- [ ] Apache Spark integration for scale
- [ ] Full dosage implementation (doseAndRate)
- [ ] Additional FHIR resources (Encounter, Observation)
- [ ] FHIR server integration (HAPI)
- [ ] REST API for on-demand transformation

**Operational:**
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Automated FHIR validation
- [ ] Prometheus metrics
- [ ] Docker containerization
- [ ] Kubernetes deployment

---

## 📖 References

### Standards & Specifications

- [HL7 FHIR R4](http://hl7.org/fhir/R4/)
- [MII Kerndatensatz](https://www.medizininformatik-initiative.de/)
- [ICD-10-GM](https://www.bfarm.de/EN/Code-systems/Classifications/ICD/ICD-10-GM/_node.html)
- [ATC Classification](https://www.whocc.no/atc_ddd_index/)

### Data Source

- [MII Test Data Repository](https://github.com/medizininformatik-initiative/kerndatensatz-testdaten)
- [MII FHIR Profiles](https://simplifier.net/organization/koordinationsstellemii)

### Related Documentation

- [German FHIR Implementation Guides](https://simplifier.net/guide/medizininformatikinitiative-modulpatientende-implementationguide)
- [GDPR & Medical Data](https://www.medizininformatik-initiative.de/de/datenschutz)

---

## 👤 Author

**Created for:** BIH@Charité Datenintegrationszentrum Position Application

**Demonstration of:**
- Medical data ETL pipeline development
- FHIR R4 transformation expertise
- German medical informatics ecosystem knowledge
- Data quality assurance capabilities
- Privacy-aware data engineering

---

## 📄 License

This is a demonstration project using synthetic test data from the Medizininformatik-Initiative.

**Data Source License:** MII test data is publicly available for testing purposes.

**Code:** Available for review and demonstration purposes.

---

## 🙏 Acknowledgments

- **Medizininformatik-Initiative** for providing official test data
- **HL7 FHIR** for the interoperability standard
- **fhir.resources** Python library maintainers

---

## 📞 Contact

For questions or discussion about this demonstration project, please open an issue in the repository.

---

**Built with ❤️ for advancing medical data interoperability in Germany**
