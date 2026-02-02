valid_home_health_examples = [
    {
        "name": "Basic Home Health",
        "payload": {
            "clinicalContext": "Post-hospitalization patients - Patients recently discharged from hospital\nHigh-risk for readmission - Patients with multiple risk factors\nComplex chronic conditions - Multiple comorbidities and ongoing management",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Medication management in home setting",
            "role": "Clinical Supervisor",
            "topic": "Safe medication administration at home"
        }
    },
    {
        "name": "Post-Acute Care Transition",
        "payload": {
            "clinicalContext": "Patients transitioning from hospital to home",
            "discipline": "PT - Physical Therapist",
            "learningFocus": "Mobility assessment and safety",
            "role": "Therapist",
            "topic": "Fall prevention strategies in home environment"
        }
    },
    {
        "name": "Chronic Disease Management",
        "payload": {
            "clinicalContext": "Diabetic patients requiring ongoing monitoring",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Blood glucose monitoring and education",
            "role": "Case Manager",
            "topic": "Home-based diabetes care protocols"
        }
    },
    {
        "name": "Wound Care at Home",
        "payload": {
            "clinicalContext": "Post-surgical patients with healing incisions",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Wound assessment and dressing changes",
            "role": "Wound Care Specialist",
            "topic": "Sterile technique in home environment"
        }
    },
    {
        "name": "Hospice Care",
        "payload": {
            "clinicalContext": "End-of-life patients in home setting",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Pain management and comfort care",
            "role": "Hospice Nurse",
            "topic": "Palliative care techniques at home"
        }
    }
]

# 2. INVALID NON-HOME HEALTH EXAMPLES (should be rejected)
invalid_examples = [
    {
        "name": "Hospital Emergency Department",
        "payload": {
            "clinicalContext": "Emergency department trauma patients",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Rapid assessment and triage",
            "role": "Emergency Nurse",
            "topic": "Advanced cardiac life support protocols"
        }
    },
    {
        "name": "Operating Room Procedures",
        "payload": {
            "clinicalContext": "Surgical patients in operating theater",
            "discipline": "Surgical Technician",
            "learningFocus": "Sterile technique and instrument handling",
            "role": "OR Tech",
            "topic": "Surgical instrument sterilization"
        }
    },
    {
        "name": "Intensive Care Unit",
        "payload": {
            "clinicalContext": "Critically ill patients on ventilators",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Ventilator management and monitoring",
            "role": "ICU Nurse",
            "topic": "Mechanical ventilation parameters"
        }
    },
    {
        "name": "School Nursing",
        "payload": {
            "clinicalContext": "Elementary school children with minor injuries",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Pediatric first aid and health screening",
            "role": "School Nurse",
            "topic": "Managing childhood allergic reactions"
        }
    },
    {
        "name": "Corporate Wellness",
        "payload": {
            "clinicalContext": "Office workers participating in health screenings",
            "discipline": "Health Coach",
            "learningFocus": "Preventive health and wellness education",
            "role": "Wellness Coordinator",
            "topic": "Workplace ergonomics and injury prevention"
        }
    }
]

# 3. EDGE CASES (borderline examples to test validation logic)
edge_case_examples = [
    {
        "name": "Outpatient Clinic with Home Follow-up",
        "payload": {
            "clinicalContext": "Outpatient clinic visits with home health follow-up",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Continuity of care between settings",
            "role": "Care Coordinator",
            "topic": "Transitional care planning"
        }
    },
    {
        "name": "Telehealth for Home Patients",
        "payload": {
            "clinicalContext": "Remote monitoring of home health patients",
            "discipline": "RN - Registered Nurse",
            "learningFocus": "Technology-assisted care delivery",
            "role": "Telehealth Coordinator",
            "topic": "Virtual patient assessment techniques"
        }
    },
    {
        "name": "Assisted Living with Home Health Services",
        "payload": {
            "clinicalContext": "Assisted living residents receiving additional home health services",
            "discipline": "HHA - Home Health Aide",
            "learningFocus": "Personal care and medication reminders",
            "role": "Home Health Aide",
            "topic": "Coordinating care in assisted living settings"
        }
    }
]