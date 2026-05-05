"""
SPE (Data Analyst) - Position 1 Screening Script
Based on: SPE(Data Analyst) 1 position.pdf eligibility criteria
Input:  - Excel: SPE-II-DA-Screening.xlsx (candidate data)
        - PDFs:  SPE-DA I-Profiles folder (resumes)
Output: - Printed screening results with reasons
        - spe_da_screening_output.xlsx
"""

import os
import re
import pandas as pd
import PyPDF2
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# ELIGIBILITY CRITERIA (from SPE(Data Analyst) 1 position.pdf)
# ─────────────────────────────────────────────
VALID_DEGREES = [
    'be', 'btech', 'beng', 'me', 'mtech', 'meng',
    'msc', 'mca', 'bsc', 'bca', 'pgdiploma',
    'bachelorofengineering', 'bacheloroftechnology',
    'masteroftechnology', 'masterofengineering',
    'masterofscience', 'masterofcomputerapplication',
    'bachelorofscience', 'bachelorofcomputerapplication',
    'bacheloroftech', 'masteroftech',
]

# Degrees that are clearly NOT valid (used to catch misclassified entries)
INVALID_DEGREE_KEYWORDS = [
    'mba', 'bba', 'bcom', 'mcom', 'civil', 'mechanical', 'chemical',
    'bioinformatics', 'pharmacy', 'mbbs', 'bds', 'agriculture',
    'infectiousdisease', 'marketing', 'finance', 'commerce',
    'architecture', 'textile', 'aeronautical', 'automobile'
]

VALID_SPECIALISATIONS = [
    # CSE variants
    'computerscience', 'computerscienceengineering', 'cse', 'cs',
    'computerscience&engineering', 'computerscienceandinformationtechnology',
    'computerscience&informationtechnology',
    # IT variants
    'informationtechnology', 'it', 'informationtechnologyengineering',
    # ECE variants
    'electronicsandcommunication', 'electronicsandcommunicationengineering',
    'ece', 'electronics&communicationengineering', 'electronics&communication',
    'electronicscommunicationengineering',
    # MCA/MSc CS
    'computerapplication', 'computerapplications', 'mca',
    'computerscience', 'msccomputerscience',
    # Data Science / AI / ML
    'datascience', 'artificialintelligence', 'machinelearning',
    'dataanalytics', 'computerscience&dataanalytics',
    # Other accepted
    'softwareengineering', 'informationscienceengineering',
    'informationscience', 'computerengineering',
    'electronicsandinstrumentation', 'electricalandelectronics',
]

MIN_PERCENTAGE   = 60.0
MIN_EXPERIENCE   = 4      # years (from PDF: 4-7 years)
MAX_EXPERIENCE   = 7      # years
CDAC_MIN_EXP     = 3      # CDAC employees need min 3 years at CDAC

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
EXCEL_PATH   = r"All Required Files/SPE-DA I-Profiles/SPE-II-DA-Screening.xlsx"
PROFILES_DIR = r"All Required Files/SPE-DA I-Profiles/SPE-DA I-Profiles"
OUTPUT_PATH  = "spe_da_screening_output.xlsx"

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def clean(text):
    if pd.isna(text) or text is None:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower().strip())

def read_pdf(path):
    try:
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f, strict=False)
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        return text.strip()
    except Exception as e:
        return f"[PDF READ ERROR: {e}]"

def experience_to_years(exp_str):
    """Convert experience string like '4 years 3 months' or '4.5' to float years."""
    if pd.isna(exp_str) or exp_str is None:
        return 0.0
    s = str(exp_str).lower().strip()
    # Already a number
    try:
        return float(s)
    except:
        pass
    years = months = 0
    y = re.search(r'(\d+)\s*year', s)
    m = re.search(r'(\d+)\s*month', s)
    if y: years  = int(y.group(1))
    if m: months = int(m.group(1))
    if years == 0 and months == 0:
        # try plain number
        nums = re.findall(r'\d+\.?\d*', s)
        if nums:
            return float(nums[0])
    return years + months / 12.0

def is_valid_degree(degree_str):
    d = clean(degree_str)
    if not d:
        return False
    # Explicitly invalid degrees
    for inv in INVALID_DEGREE_KEYWORDS:
        if inv in d:
            return False
    # Check valid degree patterns
    for v in VALID_DEGREES:
        if d == v or d.startswith(v) or v in d:
            return True
    return False

def is_valid_specialisation(spec_str):
    s = clean(spec_str)
    if not s:
        return False
    # Explicitly invalid specialisations
    invalid_specs = ['civil', 'mechanical', 'chemical', 'bioinformatics',
                     'electrical', 'electricalandelectronics', 'pharmacy',
                     'agriculture', 'textile', 'aeronautical', 'automobile',
                     'marketing', 'finance', 'commerce', 'infectiousdisease']
    for inv in invalid_specs:
        if s == inv or s.startswith(inv):
            return False
    for v in VALID_SPECIALISATIONS:
        if v == s or v in s or s in v:
            return True
    return False

def summarise_resume(pdf_text, candidate_name):
    """Extract key info from resume text as a summary."""
    if not pdf_text or "[PDF READ ERROR" in pdf_text:
        return "Resume could not be read."

    lines = [l.strip() for l in pdf_text.split('\n') if l.strip()]
    text_lower = pdf_text.lower()

    # Extract degree mentions
    degree_patterns = [
        r'\b(b\.?tech|b\.?e\.?|m\.?tech|m\.?e\.?|m\.?sc|b\.?sc|mca|bca|ph\.?d|diploma)\b',
    ]
    degrees_found = []
    for pat in degree_patterns:
        degrees_found += re.findall(pat, pdf_text, re.IGNORECASE)
    degrees_found = list(dict.fromkeys([d.upper() for d in degrees_found]))

    # Extract experience years
    exp_matches = re.findall(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of\s*)?(experience|exp)', text_lower)
    exp_years = [m[0] for m in exp_matches]

    # Extract skills keywords
    skill_keywords = [
        'python', 'sql', 'machine learning', 'deep learning', 'nlp', 'tensorflow',
        'pytorch', 'keras', 'spark', 'pyspark', 'docker', 'linux', 'tableau',
        'power bi', 'data analysis', 'data science', 'llm', 'nlp', 'spacy', 'nltk',
        'nosql', 'mongodb', 'postgresql', 'mysql', 'r ', 'scala', 'hadoop',
        'azure', 'aws', 'gcp', 'git', 'flask', 'fastapi', 'pandas', 'numpy'
    ]
    found_skills = [sk for sk in skill_keywords if sk in text_lower]

    # Build summary
    summary_parts = []
    if degrees_found:
        summary_parts.append(f"Degrees found in resume: {', '.join(degrees_found)}")
    if exp_years:
        summary_parts.append(f"Experience mentioned: {', '.join(set(exp_years))} years")
    if found_skills:
        summary_parts.append(f"Key skills found: {', '.join(found_skills[:10])}")

    if not summary_parts:
        # Fallback: first 3 meaningful lines
        summary_parts.append("Resume summary: " + " | ".join(lines[:5]))

    return " | ".join(summary_parts)

# ─────────────────────────────────────────────
# MAIN SCREENING LOGIC
# ─────────────────────────────────────────────
def screen_candidate(row, pdf_text, resume_summary):
    reasons = []
    status  = "Screened In"

    # ── 1. DEGREE CHECK ──────────────────────
    degree = str(row.get('Degree', '') or '')
    if not is_valid_degree(degree):
        # Try to find degree in resume
        resume_degree_match = re.search(
            r'\b(b\.?tech|b\.?e\.?|m\.?tech|m\.?e\.?|m\.?sc|b\.?sc|mca|bca|ph\.?d)\b',
            pdf_text, re.IGNORECASE
        )
        if resume_degree_match:
            degree = resume_degree_match.group(0)
            reasons.append(f"Degree '{row.get('Degree','')}' in Excel unclear — found '{degree}' in resume")
        else:
            status = "Screened Out"
            reasons.append(f"Invalid/irrelevant degree: '{row.get('Degree','')}' — required BE/BTech/ME/MTech/MCA/MSc in CSE/IT/ECE")
            return status, " | ".join(reasons), resume_summary

    # ── 2. SPECIALISATION CHECK ──────────────
    spec = str(row.get('Specialisation', '') or '')
    if not is_valid_specialisation(spec):
        # Try resume with word boundaries
        resume_spec = ""
        for valid_s in [('computer science', 'cse'), ('information technology', 'it'),
                        ('electronics and communication', 'ece'), ('computer application', 'mca')]:
            pattern = r'\b' + re.escape(valid_s[0]) + r'\b'
            if re.search(pattern, pdf_text, re.IGNORECASE):
                resume_spec = valid_s[0]
                break
        if resume_spec:
            reasons.append(f"Specialisation '{spec}' in Excel unclear — found '{resume_spec}' in resume")
        else:
            status = "Screened Out"
            reasons.append(f"Invalid specialisation: '{spec}' — required CSE/IT/ECE or equivalent")
            return status, " | ".join(reasons), resume_summary

    # ── 3. PERCENTAGE CHECK ──────────────────
    try:
        pct = float(str(row.get('Percentage', 0) or 0))
        if pct < MIN_PERCENTAGE:
            status = "Screened Out"
            reasons.append(f"Percentage {pct}% is below required 60%")
            return status, " | ".join(reasons), resume_summary
    except:
        reasons.append("Percentage could not be verified")

    # ── 4. EXPERIENCE CHECK ──────────────────
    exp_raw = row.get('Total Experience', '') or row.get('Qualifying Experience', '') or ''
    exp_years = experience_to_years(exp_raw)

    if exp_years < MIN_EXPERIENCE:
        # Try resume
        resume_exp = re.search(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of\s*)?(experience|exp)', pdf_text, re.IGNORECASE)
        if resume_exp:
            exp_years = float(resume_exp.group(1))
            reasons.append(f"Experience in Excel unclear — found {exp_years} years in resume")
        if exp_years < MIN_EXPERIENCE:
            status = "Screened Out"
            reasons.append(f"Experience {exp_years:.1f} years is below required {MIN_EXPERIENCE} years")
            return status, " | ".join(reasons), resume_summary

    if exp_years > MAX_EXPERIENCE:
        reasons.append(f"Note: Experience {exp_years:.1f} years exceeds max {MAX_EXPERIENCE} years (still considered)")

    # ── 5. CDAC EMPLOYEE RULES ───────────────
    is_cdac = str(row.get('CDAC Employee', '') or '').strip().lower() in ['yes', 'y', '1', 'true']
    org = str(row.get('Organization', '') or '').lower()
    if 'cdac' in org or 'c-dac' in org:
        is_cdac = True

    if is_cdac:
        cdac_exp = experience_to_years(row.get('Qualifying Experience', '') or exp_raw)
        if cdac_exp < CDAC_MIN_EXP:
            status = "Screened Out"
            reasons.append(f"CDAC employee with only {cdac_exp:.1f} years at CDAC — minimum {CDAC_MIN_EXP} years required")
            return status, " | ".join(reasons), resume_summary
        else:
            reasons.append(f"CDAC employee — NOC required at time of interview (has {cdac_exp:.1f} years at CDAC)")

    # ── 6. GOVT EMPLOYEE CHECK ───────────────
    is_govt = str(row.get('Government Employee', '') or '').strip().lower() in ['yes', 'y', '1', 'true']
    if is_govt and not is_cdac:
        reasons.append("Government employee — NOC required at time of interview")

    # ── ALL CHECKS PASSED ────────────────────
    if not reasons:
        reasons.append(f"Valid degree ({degree}), specialisation ({spec}), {pct:.0f}%, {exp_years:.1f} years experience")
    else:
        reasons.insert(0, f"Valid: degree ({degree}), specialisation ({spec}), {exp_years:.1f} yrs exp")

    return status, " | ".join(reasons), resume_summary


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
def main():
    print("\n" + "="*70)
    print("  SPE (Data Analyst) - Position 1 — Candidate Screening")
    print("="*70)

    # Load Excel
    df = pd.read_excel(EXCEL_PATH, header=2)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"\nLoaded {len(df)} candidates from Excel\n")

    # Build PDF map: applicant_id -> pdf_path
    pdf_map = {}
    if os.path.exists(PROFILES_DIR):
        for fname in os.listdir(PROFILES_DIR):
            if fname.endswith('.pdf'):
                app_id = fname.split('_')[0]
                pdf_map[app_id] = os.path.join(PROFILES_DIR, fname)

    results = []

    for _, row in df.iterrows():
        app_id   = str(row.get('Applicant ID', '') or row.get('Candidate ID', '') or '').strip()
        name     = str(row.get('Full Name', '') or '').strip()

        print(f"Processing: {app_id} — {name}")

        # Read resume PDF
        pdf_text = ""
        pdf_path = pdf_map.get(app_id, "")
        if pdf_path:
            pdf_text = read_pdf(pdf_path)
        else:
            # Try matching by name
            for pid, ppath in pdf_map.items():
                if name.split()[0].lower() in ppath.lower():
                    pdf_text = read_pdf(ppath)
                    break

        resume_summary = summarise_resume(pdf_text, name)
        status, reason, summary = screen_candidate(row, pdf_text, resume_summary)

        icon = "✅" if status == "Screened In" else "❌"
        print(f"  {icon} {status}")
        print(f"     Reason : {reason}")
        print(f"     Resume : {summary[:120]}...")
        print()

        results.append({
            'Applicant ID'    : app_id,
            'Full Name'       : name,
            'Degree'          : row.get('Degree', ''),
            'Specialisation'  : row.get('Specialisation', ''),
            'Percentage'      : row.get('Percentage', ''),
            'Total Experience': row.get('Total Experience', ''),
            'Organization'    : row.get('Organization', ''),
            'CDAC Employee'   : row.get('CDAC Employee', ''),
            'Govt Employee'   : row.get('Government Employee', ''),
            'Screening Status': status,
            'Reason'          : reason,
            'Resume Summary'  : summary,
        })

    # Save output
    out_df = pd.DataFrame(results)
    out_df.to_excel(OUTPUT_PATH, index=False)

    # Summary
    screened_in  = sum(1 for r in results if r['Screening Status'] == 'Screened In')
    screened_out = sum(1 for r in results if r['Screening Status'] == 'Screened Out')

    print("="*70)
    print(f"  TOTAL     : {len(results)}")
    print(f"  ✅ Screened In  : {screened_in}")
    print(f"  ❌ Screened Out : {screened_out}")
    print(f"\n  Output saved to: {OUTPUT_PATH}")
    print("="*70)

if __name__ == "__main__":
    main()
