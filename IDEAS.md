# Skillathon Ideas Analysis

## Where the Whitespace Is

Based on exploring all 6 repos (skillsbench, anthropic-skills, knowledge-work-plugins,
sundial-skills, awesome-openclaw-skills, harbor), here's where gaps and opportunities
converge:

### Domain Gap Map

| Domain | SkillsBench Delta | knowledge-work-plugins | Sundial (50k) | Verdict |
|--------|-------------------|----------------------|---------------|---------|
| Healthcare | **+51.9pp** | Bio-research only (preclinical) | 15 wellness skills | **MASSIVE GAP** |
| Manufacturing | **+41.9pp** | Zero coverage | Zero coverage | **MASSIVE GAP** |
| Energy | +17.9pp | Zero coverage | Zero coverage | Big gap |
| Cybersecurity | +23.2pp | Zero dedicated | 17 security skills | Moderate gap |
| Finance | +15.1pp | 6 accounting skills | 29 trading skills | Covered but narrow |
| Natural Science | +21.9pp | 5 bio-research skills | ~1 research skill | Gap in physics/chem |
| SWE | +4.5pp | 6 engineering skills | 178 dev tools | **SATURATED** |

---

## Top Ideas (Ranked by Judge Panel Appeal)

### Idea 1: Clinical Protocol Compliance (Healthcare)
**Domain**: Healthcare | **Predicted delta**: +40-50pp

**The task**: A nurse practitioner needs to review a patient's medication list against
current clinical guidelines (drug interactions, contraindications for their conditions,
dosing adjustments for renal function). Write the reconciliation report in a specific
clinical format.

**Why it wins**:
- Healthcare = +51.9pp delta (highest in SkillsBench data)
- Zero coverage in knowledge-work-plugins AND Sundial for clinical workflows
- Requires tacit knowledge models don't have (drug interaction databases, clinical
  decision rules, renal dosing adjustments)
- Deterministic verification: check specific drug flags, interaction warnings, dose calculations
- 2-3 skills: clinical-pharmacology, medication-reconciliation, clinical-documentation
- Security angle: HIPAA-aware data handling (Roey loves this)
- Physical world adjacent: hospital workflows (Grace interested)

**Risk**: Requires genuine clinical domain expertise to get right. Getting the
pharmacology wrong would be embarrassing.

---

### Idea 2: Manufacturing Quality Control (Manufacturing)
**Domain**: Manufacturing | **Predicted delta**: +35-45pp

**The task**: A quality engineer receives inspection data (measurements, defect photos
described as text, process parameters) from a production run. Determine if the batch
passes Statistical Process Control (SPC), identify root causes for any out-of-control
conditions, and generate the corrective action report per ISO 9001 format.

**Why it wins**:
- Manufacturing = +41.9pp delta (second highest)
- Literally zero skills in ANY repo for manufacturing operations
- SPC requires specific statistical knowledge (control charts, Cp/Cpk, Western Electric rules)
- Deterministic: check control chart calculations, correct rule violations identified,
  proper ISO 9001 report structure
- 2-3 skills: statistical-process-control, root-cause-analysis, iso9001-documentation
- Grace Zhang (physical world) would champion this
- Genuinely useful — every factory needs this

**Risk**: Manufacturing SPC is well-documented but niche. Need realistic sample data.

---

### Idea 3: Energy Grid Anomaly Response (Energy)
**Domain**: Energy | **Predicted delta**: +25-35pp

**The task**: A grid operator receives SCADA telemetry showing voltage anomalies across
multiple substations. Analyze the patterns, determine if it's equipment failure vs load
imbalance vs cyber attack, follow NERC reliability standards for incident classification,
and generate the required regulatory filing.

**Why it wins**:
- Energy = +17.9pp delta with room to go higher on a hard task
- Zero coverage everywhere
- Mixes cybersecurity (+23.2pp) with energy (+17.9pp) — double domain bonus
- NERC compliance is specialized knowledge models lack
- Deterministic: correct anomaly classification, proper NERC form fields, timeline accuracy
- Security angle: cyber vs physical attack differentiation (Roey + Grace both interested)

**Risk**: SCADA/grid domain is very specialized. Hard to verify without domain expert.

---

### Idea 4: Insurance Underwriting Decision (Finance × Healthcare)
**Domain**: Professional (Insurance) | **Predicted delta**: +30-40pp

**The task**: An underwriter receives an application for life insurance including medical
records, financial statements, and lifestyle questionnaire. Apply the company's
underwriting guidelines to classify risk, determine premium adjustments, identify
required exclusions, and produce the underwriting decision memo.

**Why it wins**:
- Cross-domain: finance (+15.1pp) × healthcare knowledge × legal compliance
- Insurance is explicitly listed as a hackathon sub-track but has zero existing coverage
- Requires composing domain knowledge: actuarial tables + medical risk assessment + policy language
- Deterministic: risk classification correctness, premium calculation, exclusion identification
- 3 skills: risk-classification, medical-underwriting, policy-documentation
- Reusable on Sundial (Belinda) — insurance industry would want this

**Risk**: Insurance underwriting guidelines are proprietary. Need to create realistic
but synthetic guidelines.

---

### Idea 5: Pharma Batch Record Review (Manufacturing × Healthcare)
**Domain**: Manufacturing | **Predicted delta**: +35-45pp

**The task**: A quality assurance specialist reviews a pharmaceutical batch production
record for FDA compliance. Check process parameters against validated ranges, verify
in-process test results, identify deviations, classify them per FDA severity guidelines,
and prepare the batch disposition recommendation (release/reject/investigate).

**Why it wins**:
- Combines manufacturing (+41.9pp) and healthcare (+51.9pp) — both top delta domains
- FDA compliance requires very specific procedural knowledge
- GMP (Good Manufacturing Practice) is pure tacit knowledge — exactly what skills are for
- Deterministic: parameter in/out of range, deviation classification, correct FDA references
- 2-3 skills: gmp-batch-review, deviation-management, fda-compliance
- Physical world (Grace) + security/compliance (Roey) + high delta (Xiangyi) + reusable (Belinda)
- Genuinely valuable to pharma industry

**Risk**: Needs realistic batch record data. FDA regulations are public but dense.

---

## Quick-Hit Ideas (Simpler, Lower Risk)

### Idea 6: OSHA Incident Investigation
Manufacturing safety incident → root cause analysis → OSHA 300 log entry.
Zero existing coverage. Deterministic (correct classification, proper form fields).

### Idea 7: Clinical Lab Result Interpretation
Given lab panels (CBC, CMP, lipids), flag abnormals, suggest differential diagnoses,
recommend follow-up tests per clinical guidelines. Highly deterministic.

### Idea 8: Building Energy Audit
Analyze utility bills + building specs → identify efficiency opportunities →
calculate ROI → generate ASHRAE-format audit report. Energy domain, deterministic.

---

## Recommendation

**Idea 5 (Pharma Batch Record Review)** is the sweet spot:
- Intersects the two highest-delta domains (manufacturing + healthcare)
- FDA/GMP knowledge is public but specialized — perfect for skills
- Highly deterministic verification (parameters are in-range or not)
- Every pharma company needs this (Belinda's reusability test)
- Physical world grounding (Grace), security/compliance angle (Roey)
- Clean Harbor format possible (Ryan), measurable delta (Xiangyi)
- Novel domain for skills (Bence)
- Could be built in a hackathon day with synthetic but realistic data

**Runner-up**: Idea 1 (Clinical Protocol Compliance) if we have medical domain expertise.
**Safe pick**: Idea 2 (Manufacturing QC/SPC) — simpler, well-documented domain knowledge.
