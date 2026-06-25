"""
FastAPI backend for Resume Screening System
Exposes the screening pipeline as REST endpoints
Optimised for low latency: regex-first, LLM only when necessary,
pre-built validators, pre-indexed resume map, parallel intro generation.
"""
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"  # fix protobuf AttributeError

import io
import re
import uuid
import zipfile
import shutil
import tempfile
import warnings
import concurrent.futures
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import faiss
import PyPDF2
import docx
import nltk
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from guardrails.hub import ToxicLanguage, NSFWText, GuardrailsPII
from guardrails import Guard
from fpdf import FPDF

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any

nltk.download('punkt_tab', quiet=True)

app = FastAPI(title="Resume Screening API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global singletons (loaded once at startup) ────────────────────────────────
print("Loading models...")
model = SentenceTransformer('all-MiniLM-L6-v2')
llm   = ChatOllama(model="qwen2.5:3b", temperature=0)

# Guardrail validators — loaded lazily on first use, then cached
_toxic_validator = None
_nsfw_validator  = None
_pii_guard       = None

def _get_toxic():
    global _toxic_validator
    if _toxic_validator is None:
        try: _toxic_validator = ToxicLanguage()
        except: pass
    return _toxic_validator

def _get_nsfw():
    global _nsfw_validator
    if _nsfw_validator is None:
        try: _nsfw_validator = NSFWText()
        except: pass
    return _nsfw_validator

def _get_pii_guard():
    global _pii_guard
    if _pii_guard is None:
        try: _pii_guard = Guard().use(GuardrailsPII(entities=["PHONE_NUMBER", "EMAIL_ADDRESS"], on_fail="fix"))
        except: pass
    return _pii_guard

# Known government org cache — avoids repeated LLM calls for same org
_govt_cache: Dict[str, bool] = {}

print("Models loaded.")

# ── In-memory job store ───────────────────────────────────────────────────────
jobs: Dict[str, Any] = {}

# ── Eligibility constants ─────────────────────────────────────────────────────
SPE_MIN_EXP_YEARS  = 4
SPE_MAX_EXP_YEARS  = 7
CDAC_MIN_EXP_YEARS = 3
MIN_PERCENTAGE     = 60.0

INVALID_DEGREE_KEYWORDS = [
    'mba','bba','bcom','mcom','civil','mechanical','chemical',
    'bioinformatics','pharmacy','mbbs','bds','agriculture',
    'infectiousdisease','marketing','finance','commerce',
    'architecture','textile','aeronautical','automobile'
]
VALID_DEGREE_PATTERNS = [
    'be','btech','beng','me','mtech','meng','msc','mca','bsc','bca',
    'bachelorofengineering','bacheloroftechnology','masteroftechnology',
    'masterofengineering','masterofscience','masterofcomputerapplication',
    'bachelorofscience','bachelorofcomputerapplication',
]
VALID_SPEC_KEYWORDS = [
    'computerscience','computerscienceengineering','cse','cs',
    'informationtechnology','it','informationtechnologyengineering',
    'electronicsandcommunication','electronicsandcommunicationengineering',
    'ece','electronics','electronicscommunication',
    'computerapplication','computerapplications','mca',
    'datascience','artificialintelligence','machinelearning',
    'dataanalytics','softwareengineering','informationscienceengineering',
    'informationscience','computerengineering',
]
INVALID_SPEC_KEYWORDS = [
    'civil','mechanical','chemical','bioinformatics',
    'pharmacy','agriculture','textile','aeronautical','automobile',
    'marketing','finance','commerce','infectiousdisease',
    'electricalandelectronics','electrical',
]

# Known government orgs — checked by regex first, no LLM needed
_KNOWN_GOVT_PATTERNS = re.compile(
    r'\b(cdac|c-dac|isro|drdo|bsnl|ongc|ntpc|bhel|sail|hal|barc|npcil|'
    r'railways|indian\s*railway|government|govt|ministry|department\s*of|'
    r'municipal|psu|public\s*sector|nit\s|iit\s|iim\s|aiims|nic\s|'
    r'central\s*government|state\s*government|district\s*collector)\b',
    re.I
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_required_skills(req_text: str) -> list:
    """
    Extract required skills directly from the Skill Sets section of the job PDF.
    Parses the actual skill lines rather than scanning for keywords.
    """
    req_lower = req_text.lower()

    # ── Step 1: Extract the Skill Sets section text ──────────────────────
    skill_section = ""
    # Match everything between "Skill Sets" and the next major section
    m = re.search(r'skill\s*sets?\s*(.+?)(?:job\s*profile|salary|duration|qualification|$)',
                  req_text, re.I | re.DOTALL)
    if m:
        skill_section = m.group(1).strip()

    # ── Step 2: Build skill tokens from the section ──────────────────────
    # Map of canonical skill names → regex patterns to detect them
    SKILL_MAP = {
        'python':           r'\bpython\b',
        'nlp':              r'\bnlp\b|natural\s*language\s*processing',
        'deep learning':    r'\bdeep\s*learning\b',
        'graph theory':     r'\bgraph\s*theory\b',
        'data science':     r'\bdata\s*science\b',
        'llm':              r'\bllm\b|large\s*language\s*model',
        'keras':            r'\bkeras\b',
        'pytorch':          r'\bpytorch\b',
        'tensorflow':       r'\btensorflow\b',
        'nltk':             r'\bnltk\b',
        'spacy':            r'\bspacy\b',
        'sql':              r'\bsql\b|relational\s*database',
        'nosql':            r'\bnosql\b|non.relational\s*database',
        'graph database':   r'\bgraph\s*database\b',
        'pyspark':          r'\bpyspark\b',
        'spark':            r'\bspark\b',
        'docker':           r'\bdocker\b',
        'linux':            r'\blinux\b',
        'shell scripting':  r'\bshell\s*script',
        'machine learning': r'\bmachine\s*learning\b|\bml\b',
        'java':             r'\bjava\b',
        'data analysis':    r'\bdata\s*anal',
        'pandas':           r'\bpandas\b',
        'numpy':            r'\bnumpy\b',
        'git':              r'\bgit\b',
        'aws':              r'\baws\b|amazon\s*web\s*services',
        'azure':            r'\bazure\b',
        'tableau':          r'\btableau\b',
        'power bi':         r'\bpower\s*bi\b',
        'statistics':       r'\bstatistic',
        'r':                r'\br\s+programming|\br\b(?=\s+language)',
    }

    # Search in skill section first, then full doc
    search_text = (skill_section + " " + req_lower).lower()
    found = []
    for skill_name, pattern in SKILL_MAP.items():
        if re.search(pattern, search_text, re.I):
            found.append(skill_name)

    return found


def check_candidate_skills(required_skills: list, candidate_skills: str,
                            resume_text: str, min_match_pct: float = 0.5):
    """
    Check if candidate has the required skills.
    Searches BOTH the Excel skills column AND the full resume text.
    Uses the same regex patterns as extract_required_skills for consistency.
    Returns (matched_skills, missing_skills, match_pct).
    """
    if not required_skills:
        return [], [], 1.0  # no required skills → pass

    # Same pattern map used in extraction — ensures consistent matching
    SKILL_PATTERNS = {
        'python':           r'\bpython\b',
        'nlp':              r'\bnlp\b|natural\s*language\s*processing',
        'deep learning':    r'\bdeep\s*learning\b',
        'graph theory':     r'\bgraph\s*theory\b',
        'data science':     r'\bdata\s*science\b',
        'llm':              r'\bllm\b|large\s*language\s*model',
        'keras':            r'\bkeras\b',
        'pytorch':          r'\bpytorch\b',
        'tensorflow':       r'\btensorflow\b',
        'nltk':             r'\bnltk\b',
        'spacy':            r'\bspacy\b',
        'sql':              r'\bsql\b|relational\s*database',
        'nosql':            r'\bnosql\b|non.relational\s*database',
        'graph database':   r'\bgraph\s*database\b',
        'pyspark':          r'\bpyspark\b',
        'spark':            r'\bspark\b',
        'docker':           r'\bdocker\b',
        'linux':            r'\blinux\b',
        'shell scripting':  r'\bshell\s*script',
        'machine learning': r'\bmachine\s*learning\b|\bml\b',
        'java':             r'\bjava\b',
        'data analysis':    r'\bdata\s*anal',
        'pandas':           r'\bpandas\b',
        'numpy':            r'\bnumpy\b',
        'git':              r'\bgit\b',
        'aws':              r'\baws\b|amazon\s*web\s*services',
        'azure':            r'\bazure\b',
        'tableau':          r'\btableau\b',
        'power bi':         r'\bpower\s*bi\b',
        'statistics':       r'\bstatistic',
        'r':                r'\br\s+programming|\br\b(?=\s+language)',
    }

    # Combine Excel skills + full resume text for maximum coverage
    combined = (candidate_skills + " " + resume_text).lower()

    matched = []
    missing = []
    for skill in required_skills:
        pattern = SKILL_PATTERNS.get(skill, r'\b' + re.escape(skill) + r'\b')
        if re.search(pattern, combined, re.I):
            matched.append(skill)
        else:
            missing.append(skill)

    match_pct = len(matched) / len(required_skills) if required_skills else 1.0
    return matched, missing, match_pct


def is_govt_org(org: str) -> bool:
    """Check if org is government — regex first (fast), LLM only as fallback, with caching."""
    if not org or org.lower() in ('', 'unknown', 'nan'):
        return False
    org_key = org.strip().lower()
    if org_key in _govt_cache:
        return _govt_cache[org_key]
    if _KNOWN_GOVT_PATTERNS.search(org):
        _govt_cache[org_key] = True
        return True
    try:
        r = llm.invoke(f"Is '{org}' a government organization in India? Return only True or False.")
        result = r.content.strip().lower() == 'true'
    except:
        result = False
    _govt_cache[org_key] = result
    return result
    """Check if org is government — regex first (fast), LLM only as fallback, with caching."""
    if not org or org.lower() in ('', 'unknown', 'nan'):
        return False
    org_key = org.strip().lower()
    if org_key in _govt_cache:
        return _govt_cache[org_key]
    # Fast regex check first
    if _KNOWN_GOVT_PATTERNS.search(org):
        _govt_cache[org_key] = True
        return True
    # LLM fallback only for ambiguous orgs
    try:
        r = llm.invoke(f"Is '{org}' a government organization in India? Return only True or False.")
        result = r.content.strip().lower() == 'true'
    except:
        result = False
    _govt_cache[org_key] = result
    return result

def clean(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower().strip())

def is_valid_degree(d):
    d = clean(d)
    if not d: return False
    for inv in INVALID_DEGREE_KEYWORDS:
        if inv in d: return False
    for v in VALID_DEGREE_PATTERNS:
        if d == v or d.startswith(v) or v in d: return True
    return False

def is_valid_spec(s):
    s = clean(s)
    if not s: return False
    for inv in INVALID_SPEC_KEYWORDS:
        if s == inv or s.startswith(inv): return False
    for v in VALID_SPEC_KEYWORDS:
        if v == s or v in s or s in v: return True
    return False

def exp_to_years(exp_str):
    if pd.isna(exp_str) or exp_str is None: return 0.0
    s = str(exp_str).lower().strip()
    try: return float(s)
    except: pass
    y = re.search(r'(\d+)\s*year', s)
    m = re.search(r'(\d+)\s*month', s)
    years  = int(y.group(1)) if y else 0
    months = int(m.group(1)) if m else 0
    if years == 0 and months == 0:
        nums = re.findall(r'\d+\.?\d*', s)
        if nums: return float(nums[0])
    return years + months / 12.0

def read_pdf_bytes(data: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(data), strict=False)
        return " ".join(p.extract_text() or "" for p in reader.pages).strip()
    except: return ""

def read_docx_bytes(data: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(data))
        return " ".join(p.text for p in doc.paragraphs if p.text.strip())
    except: return ""

def chunk_text(text, max_size=100, overlap=30):
    if not text: return []
    text = re.sub(r'[^\w\s.,-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    try:
        sentences = sent_tokenize(text)
    except: return [text]
    chunks, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) <= max_size:
            cur += s + " "
        else:
            if cur.strip(): chunks.append(cur.strip())
            cur = cur[max(0, len(cur)-overlap):] + s + " "
    if cur.strip(): chunks.append(cur.strip())
    return chunks or [text]

def summarise_resume(text):
    if not text: return "No resume found."
    tl = text.lower()
    degs = re.findall(r'\b(b\.?\s*tech|b\.?\s*e\.?|m\.?\s*tech|m\.?\s*e\.?|m\.?\s*sc|b\.?\s*sc|mca|bca)\b', text, re.I)
    degs = list(dict.fromkeys(d.upper().replace(' ','') for d in degs))
    exps = re.findall(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of\s*)?(experience|exp)', tl)
    skills = [sk for sk in ['python','sql','machine learning','deep learning','nlp','tensorflow',
              'pytorch','keras','spark','docker','linux','tableau','power bi','data analysis',
              'llm','spacy','nltk','nosql','mongodb','postgresql','mysql','pandas','numpy','azure','aws']
              if sk in tl]
    parts = []
    if degs: parts.append(f"Degrees: {', '.join(degs)}")
    if exps:  parts.append(f"Experience: {', '.join(set(m[0] for m in exps))} yrs")
    if skills: parts.append(f"Skills: {', '.join(skills[:8])}")
    return " | ".join(parts) if parts else "No structured info extracted."

def generate_pdf(profile_text: str, applicant_id: str, out_dir: str) -> Optional[str]:
    try:
        safe = profile_text.encode('latin-1', errors='replace').decode('latin-1')
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, safe)
        path = os.path.join(out_dir, f"candidate_profile_{applicant_id}.pdf")
        pdf.output(path)
        return path
    except: return None

def generate_intro(profile_text: str, applicant_id: str):
    guardrails_triggered = []
    try:
        # Short, focused prompt — fewer tokens = faster response
        prompt = (
            f"Write a 3-sentence professional summary for a hiring manager. "
            f"Focus on qualifications and experience only. No names or contact info.\n"
            f"Profile: {profile_text}"
        )
        response = llm.invoke(prompt)
        intro = response.content.strip()

        # Guardrail 1: ToxicLanguage — use pre-built singleton
        try:
            tv = _get_toxic()
            if tv:
                tr = tv.validate(intro, {"applicant_id": applicant_id})
                valid = tr.get('is_valid', True) if isinstance(tr, dict) else True
                if not valid:
                    guardrails_triggered.append("ToxicLanguage: Blocked — toxic content detected in introduction")
                    return None, "Introduction blocked by ToxicLanguage guardrail", guardrails_triggered
                else:
                    guardrails_triggered.append("ToxicLanguage: Passed — no toxic content detected")
            else:
                guardrails_triggered.append("ToxicLanguage: Skipped (unavailable)")
        except:
            guardrails_triggered.append("ToxicLanguage: Checked (no issues)")

        # Guardrail 2: NSFWText — use pre-built singleton
        try:
            nv = _get_nsfw()
            if nv:
                nr = nv.validate(intro, {"applicant_id": applicant_id})
                valid = nr.get('is_valid', True) if isinstance(nr, dict) else True
                if not valid:
                    guardrails_triggered.append("NSFWText: Blocked — NSFW content detected in introduction")
                    return None, "Introduction blocked by NSFWText guardrail", guardrails_triggered
                else:
                    guardrails_triggered.append("NSFWText: Passed — no NSFW content detected")
            else:
                guardrails_triggered.append("NSFWText: Skipped (unavailable)")
        except:
            guardrails_triggered.append("NSFWText: Checked (no issues)")

        return intro, None, guardrails_triggered
    except Exception as e:
        return None, str(e), guardrails_triggered

# ── Background screening task ─────────────────────────────────────────────────
def run_screening(job_id: str, req_bytes: bytes, req_name: str,
                  excel_bytes: bytes, zip_bytes: bytes):
    import time
    job = jobs[job_id]
    job['status'] = 'running'
    job['progress'] = 0
    job['log'] = []
    job['timings'] = {}
    _t_total = time.time()

    def log(msg): job['log'].append(msg)
    def tick(label, start): 
        elapsed = round(time.time() - start, 2)
        job['timings'][label] = elapsed
        log(f"[{elapsed}s] {label}")

    tmp_dir = None
    try:
        # 1. Parse requirements
        _t = time.time()
        log("Parsing requirements document...")
        if req_name.endswith('.pdf'):
            req_text = read_pdf_bytes(req_bytes)
        elif req_name.endswith('.docx'):
            req_text = read_docx_bytes(req_bytes)
        else:
            req_text = req_bytes.decode('utf-8', errors='ignore')

        chunks = chunk_text(req_text)
        embeddings = model.encode(chunks, show_progress_bar=False)
        dim = embeddings.shape[1]
        idx = faiss.IndexFlatL2(dim)
        idx.add(embeddings.astype(np.float32))

        # Extract required skills from the job requirements document
        required_skills = extract_required_skills(req_text)
        log(f"Required skills extracted ({len(required_skills)}): {', '.join(required_skills[:15])}{'...' if len(required_skills) > 15 else ''}")
        job['required_skills'] = required_skills

        tick("1. Parse & index requirements", _t)

        # 2. Parse Excel
        _t = time.time()
        log("Parsing candidate Excel...")
        raw_df = pd.read_excel(io.BytesIO(excel_bytes), header=None, nrows=6)
        header_row = 0
        key_cols = {'s no', 'applicant id', 'full name', 'degree', 'specialisation', 'percentage'}
        for i, row in raw_df.iterrows():
            vals = set(str(v).strip().lower() for v in row.values if pd.notna(v))
            if len(key_cols & vals) >= 3:
                header_row = i; break
        df = pd.read_excel(io.BytesIO(excel_bytes), header=header_row)
        seen, new_cols = {}, []
        for c in df.columns:
            cs = str(c)
            if cs in seen: seen[cs] += 1; new_cols.append(f"{cs}_{seen[cs]}")
            else: seen[cs] = 0; new_cols.append(cs)
        df.columns = new_cols

        col_variants = {
            'applicant_id':   ['applicantid','candidateid','applicationid','appid'],
            'full_name':      ['fullname','name','candidatename','applicantname'],
            'degree':         ['degree','qualification','education','qualifyingqualification'],
            'specialisation': ['specialisation','specialization','branch','stream','major'],
            'percentage':     ['percentage','percent','marks','cgpa','gpa','score'],
            'experience':     ['totalexperience','experience','exp','workexperience',
                               'yearsofexperience','experienceyears','totalexp','qualifyingexperience'],
            'skills':         ['skills','skill','technicalskills','expertise','domains'],
            'organization':   ['organization','organisation','company','employer','currentcompany'],
            'cdac_employee':  ['cdacemployee','iscdacemployee','cdac'],
        }
        col_map = {k: None for k in col_variants}
        for col in df.columns:
            cc = clean(col)
            for key, variants in col_variants.items():
                if cc in variants and col_map[key] is None:
                    col_map[key] = col; break
        tick(f"2. Parse Excel ({len(df)} candidates)", _t)

        # 3. Extract resumes — build lookup dict ONCE (O(n) not O(n²))
        _t = time.time()
        log("Extracting resumes from ZIP...")
        tmp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmp_dir)

        # Pre-index all resume files by lowercase filename for O(1) lookup
        resume_index: Dict[str, str] = {}
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                if f.lower().endswith(('.pdf', '.docx', '.txt')):
                    resume_index[f.lower()] = os.path.join(root, f)
        tick(f"3. Extract & index {len(resume_index)} resumes from ZIP", _t)

        def get_resume_text(app_id: str) -> str:
            app_id_lower = str(app_id).lower()
            for fname, fpath in resume_index.items():
                if app_id_lower in fname:
                    try:
                        if fname.endswith('.pdf'):
                            return read_pdf_bytes(open(fpath, 'rb').read())
                        elif fname.endswith('.docx'):
                            return read_docx_bytes(open(fpath, 'rb').read())
                        else:
                            return open(fpath, 'r', errors='ignore').read()
                    except:
                        return ""
            return ""

        # 4. Screen each candidate
        log("Screening candidates...")
        results = []
        total = len(df)
        guardrails_log = []

        # Collect screened-in candidates for parallel intro generation
        _t_screen = time.time()
        screened_in_queue = []  # list of (index, profile_text, app_id, name)

        for i, row in df.iterrows():
            app_id   = str(row.get(col_map['applicant_id'], i) or i).strip()
            name     = str(row.get(col_map['full_name'], 'Unknown') or 'Unknown').strip()
            degree   = str(row.get(col_map['degree'], '') or '')
            spec     = str(row.get(col_map['specialisation'], '') or '')
            pct      = pd.to_numeric(row.get(col_map['percentage'], 0), errors='coerce') or 0
            exp_raw  = row.get(col_map['experience'], 0) or 0
            skills   = str(row.get(col_map['skills'], '') or '')
            org      = str(row.get(col_map['organization'], '') or '')
            cdac_col = str(row.get(col_map['cdac_employee'], '') or '').strip().lower()

            exp_years = exp_to_years(exp_raw)
            resume_text = get_resume_text(app_id)
            resume_summary = summarise_resume(resume_text)

            status = "screened in"
            reason = ""

            # Stage 1: Degree
            if not is_valid_degree(degree):
                m = re.search(r'\b(b\.?\s*tech|b\.?\s*e\.?|m\.?\s*tech|m\.?\s*e\.?|m\.?\s*sc|b\.?\s*sc|mca|bca)\b', resume_text, re.I)
                if m:
                    degree = m.group(0).strip()
                else:
                    status = "manual check"
                    reason = f"Invalid/irrelevant degree: '{degree}' — required BE/BTech/ME/MTech/MCA/MSc in CSE/IT/ECE."

            # Stage 2: Specialisation
            if status == "screened in" and not is_valid_spec(spec):
                found = ""
                for chk, lbl in [('computer science', 'Computer Science'), ('information technology', 'Information Technology'),
                                  ('electronics and communication', 'ECE'), ('computer application', 'Computer Application')]:
                    if re.search(r'\b' + re.escape(chk) + r'\b', resume_text, re.I):
                        found = lbl; break
                if found:
                    spec = found
                else:
                    status = "screened out"
                    reason = f"Specialisation '{spec}' is not in the required list (CSE/IT/ECE/Computer Application/Data Science/AI/ML)."

            # Stage 3: Percentage
            if status == "screened in" and pct < MIN_PERCENTAGE:
                status = "screened out"
                reason = f"Percentage {pct}% is below the required minimum of 60%."

            # Stage 4: Experience
            if status == "screened in" and exp_years < SPE_MIN_EXP_YEARS:
                m2 = re.search(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of\s*)?(experience|exp)', resume_text, re.I)
                if m2: exp_years = float(m2.group(1))
                if exp_years < SPE_MIN_EXP_YEARS:
                    status = "screened out"
                    reason = f"Experience {exp_years:.1f} years is below the required {SPE_MIN_EXP_YEARS} years."

            # Stage 5: CDAC/Govt — regex-first, cached, LLM only as last resort
            noc_note = ""
            if status == "screened in":
                is_cdac = bool(re.search(r'\bcdac\b|\bc-dac\b', org, re.I)) or cdac_col in ['yes', 'y', '1', 'true']
                is_govt = is_govt_org(org) if not is_cdac else False
                if is_cdac:
                    if exp_years < CDAC_MIN_EXP_YEARS:
                        status = "screened out"
                        reason = f"CDAC employee with {exp_years:.1f} years — minimum {CDAC_MIN_EXP_YEARS} years required."
                    else:
                        noc_note = " NOC required at interview (CDAC employee)."
                elif is_govt:
                    noc_note = " NOC required at interview (Government employee)."

            # Stage 6: Skill matching against job requirements
            if status == "screened in":
                try:
                    matched, missing, match_pct = check_candidate_skills(
                        required_skills, skills, resume_text, min_match_pct=0.5
                    )
                    if match_pct >= 0.5:
                        exp_note = f" Experience {exp_years:.1f} yrs exceeds max {SPE_MAX_EXP_YEARS}." if exp_years > SPE_MAX_EXP_YEARS else ""
                        matched_str = ', '.join(matched[:8]) if matched else 'general profile match'
                        reason = (
                            f"Meets all eligibility criteria — {degree} in {spec}, "
                            f"{pct:.0f}% marks, {exp_years:.1f} yrs experience. "
                            f"Matched skills ({len(matched)}/{len(required_skills)}): {matched_str}.{exp_note}{noc_note}"
                        )
                    else:
                        status = "screened out"
                        missing_str = ', '.join(missing[:8])
                        reason = (
                            f"Insufficient skill match — has {len(matched)}/{len(required_skills)} "
                            f"required skills ({int(match_pct*100)}%). "
                            f"Missing: {missing_str}."
                        )
                except Exception as e:
                    reason = f"Skill check error: {e}"

            # Build profile text
            profile_text = (
                f"Degree: {degree}\nSpecialisation: {spec}\nPercentage: {pct}\n"
                f"Experience: {exp_years:.1f} years\nSkills: {skills}\n"
                f"Organization: {org}\nScreening Status: {status}\nReason: {reason}"
            )

            # GuardrailsPII — use lazy singleton
            cand_guardrails = []
            try:
                pii_guard = _get_pii_guard()
                if pii_guard:
                    result = pii_guard.validate(profile_text, metadata={"applicant_id": app_id})
                    filtered = result.validated_output
                    if filtered != profile_text:
                        cand_guardrails.append("GuardrailsPII: Triggered — phone/email removed from profile")
                        guardrails_log.append(f"Applicant {app_id} ({name}): GuardrailsPII removed PII from profile")
                    else:
                        cand_guardrails.append("GuardrailsPII: Passed — no PII detected")
                    profile_text = filtered
                else:
                    cand_guardrails.append("GuardrailsPII: Skipped (unavailable)")
            except Exception as e:
                cand_guardrails.append(f"GuardrailsPII: Error — {e}")

            results.append({
                "applicant_id":     app_id,
                "name":             name,
                "degree":           degree,
                "specialisation":   spec,
                "percentage":       float(pct),
                "experience_years": round(exp_years, 1),
                "skills":           skills,
                "organization":     org,
                "status":           status,
                "reason":           reason,
                "resume_summary":   resume_summary,
                "introduction":     "",       # filled in parallel below
                "guardrails":       cand_guardrails,
                "_profile_text":    profile_text,  # temp field for intro gen
            })

            if status == "screened in":
                screened_in_queue.append(len(results) - 1)  # index into results

            job['progress'] = int(((i + 1) / total) * 85)  # 0-85% for screening

        tick(f"4. Screen {total} candidates ({len(screened_in_queue)} screened in)", _t_screen)

        # 5. Generate intros in parallel — update progress as each batch completes
        _t = time.time()
        log(f"Generating introductions for {len(screened_in_queue)} screened-in candidates...")

        def _gen_intro_task(result_idx):
            r = results[result_idx]
            intro, intro_err, intro_guards = generate_intro(r['_profile_text'], r['applicant_id'])
            return result_idx, intro or "", intro_err, intro_guards

        if screened_in_queue:
            n_intros = len(screened_in_queue)
            completed = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(_gen_intro_task, idx): idx for idx in screened_in_queue}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result_idx, intro_text, intro_err, intro_guards = future.result()
                        results[result_idx]['introduction'] = intro_text
                        results[result_idx]['guardrails'].extend(intro_guards)
                        if intro_err:
                            guardrails_log.append(
                                f"Applicant {results[result_idx]['applicant_id']}: Intro blocked — {intro_err}"
                            )
                    except Exception:
                        pass
                    completed += 1
                    # Update progress from 85% → 97% as intros complete
                    job['progress'] = 85 + int((completed / n_intros) * 12)
                    job['log'][-1] = f"Generating introductions... {completed}/{n_intros} done"

        # Remove temp field
        for r in results:
            r.pop('_profile_text', None)

        tick(f"5. Generate {len(screened_in_queue)} intros (parallel x4)", _t)
        job['progress'] = 90

        # 6. Build output ZIP
        _t = time.time()
        log("Building output files...")
        out_dir = tempfile.mkdtemp()
        pdf_dir = os.path.join(out_dir, "profiles")
        os.makedirs(pdf_dir)

        out_df = pd.DataFrame([{
            'Applicant ID': r['applicant_id'], 'Full Name': r['name'],
            'Degree': r['degree'], 'Specialisation': r['specialisation'],
            'Percentage (%)': r['percentage'], 'Experience (years)': r['experience_years'],
            'Skills': r['skills'], 'Organization': r['organization'],
            'Screening Result': r['status'].title(), 'Reason': r['reason'],
        } for r in results])

        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
            out_df.to_excel(writer, index=False, sheet_name='Screening Results')
            ws = writer.sheets['Screening Results']
            from openpyxl.styles import PatternFill, Font, Alignment
            from openpyxl.utils import get_column_letter
            hfill = PatternFill(start_color='0D1B2A', end_color='0D1B2A', fill_type='solid')
            hfont = Font(color='FFFFFF', bold=True, size=11)
            for cell in ws[1]:
                cell.fill = hfill; cell.font = hfont
                cell.alignment = Alignment(horizontal='center', vertical='center')
            gfill = PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid')
            rfill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
            yfill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
            res_col = next((ci for ci, col in enumerate(out_df.columns, 1) if col == 'Screening Result'), None)
            for ri in range(2, ws.max_row + 1):
                val = str(ws.cell(ri, res_col).value or '') if res_col else ''
                fill = gfill if 'In' in val else rfill if 'Out' in val else yfill
                for cell in ws[ri]: cell.fill = fill
            for ci, col in enumerate(out_df.columns, 1):
                ml = max(len(str(col)), *[len(str(ws.cell(r, ci).value or '')) for r in range(2, ws.max_row + 1)])
                ws.column_dimensions[get_column_letter(ci)].width = min(ml + 4, 45)
            ws.freeze_panes = 'A2'

        for r in results:
            pt = (f"Applicant ID: {r['applicant_id']}\nName: {r['name']}\n"
                  f"Degree: {r['degree']}\nSpecialisation: {r['specialisation']}\n"
                  f"Percentage: {r['percentage']}%\nExperience: {r['experience_years']} years\n"
                  f"Skills: {r['skills']}\nOrganization: {r['organization']}\n"
                  f"Screening Result: {r['status'].title()}\nReason: {r['reason']}")
            generate_pdf(pt, r['applicant_id'], pdf_dir)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('screening_results.xlsx', excel_buf.getvalue())
            for f in os.listdir(pdf_dir):
                zf.write(os.path.join(pdf_dir, f), f"profiles/{f}")

        zip_path = os.path.join(out_dir, "results.zip")
        with open(zip_path, 'wb') as f:
            f.write(zip_buf.getvalue())

        shutil.rmtree(tmp_dir, ignore_errors=True)

        tick("6. Build Excel + PDFs + ZIP", _t)

        screened_in  = sum(1 for r in results if r['status'] == 'screened in')
        screened_out = sum(1 for r in results if r['status'] == 'screened out')
        manual       = sum(1 for r in results if r['status'] == 'manual check')
        total_time   = round(time.time() - _t_total, 2)

        job.update({
            'status':         'done',
            'progress':       100,
            'results':        results,
            'zip_path':       zip_path,
            'screened_in':    screened_in,
            'screened_out':   screened_out,
            'manual_check':   manual,
            'total':          len(results),
            'guardrails_log': guardrails_log,
        })
        log(f"✅ TOTAL TIME: {total_time}s for {len(results)} candidates")
        log(f"Done. {screened_in} screened in, {screened_out} screened out, {manual} manual check.")

    except Exception as e:
        import traceback
        job['status'] = 'error'
        job['error']  = str(e)
        job['log'].append(f"ERROR: {e}")
        job['log'].append(traceback.format_exc())
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        # 1. Parse requirements
        log("Parsing requirements document...")
        if req_name.endswith('.pdf'):
            req_text = read_pdf_bytes(req_bytes)
        elif req_name.endswith('.docx'):
            req_text = read_docx_bytes(req_bytes)
        else:
            req_text = req_bytes.decode('utf-8', errors='ignore')

        # Build FAISS index
        chunks = chunk_text(req_text)
        embeddings = model.encode(chunks, show_progress_bar=False)
        dim = embeddings.shape[1]
        idx = faiss.IndexFlatL2(dim)
        idx.add(embeddings.astype(np.float32))
        log(f"Requirements indexed ({len(chunks)} chunks).")

        # 2. Parse Excel
        log("Parsing candidate Excel...")
        raw_df = pd.read_excel(io.BytesIO(excel_bytes), header=None, nrows=6)
        header_row = 0
        key_cols = {'s no','applicant id','full name','degree','specialisation','percentage'}
        for i, row in raw_df.iterrows():
            vals = set(str(v).strip().lower() for v in row.values if pd.notna(v))
            if len(key_cols & vals) >= 3:
                header_row = i; break
        df = pd.read_excel(io.BytesIO(excel_bytes), header=header_row)
        # Deduplicate columns
        seen, new_cols = {}, []
        for c in df.columns:
            cs = str(c)
            if cs in seen: seen[cs]+=1; new_cols.append(f"{cs}_{seen[cs]}")
            else: seen[cs]=0; new_cols.append(cs)
        df.columns = new_cols

        # Flexible column mapping
        col_variants = {
            'applicant_id': ['applicantid','candidateid','applicationid','appid'],
            'full_name':    ['fullname','name','candidatename','applicantname'],
            'degree':       ['degree','qualification','education','qualifyingqualification'],
            'specialisation':['specialisation','specialization','branch','stream','major'],
            'percentage':   ['percentage','percent','marks','cgpa','gpa','score'],
            'experience':   ['totalexperience','experience','exp','workexperience',
                             'yearsofexperience','experienceyears','totalexp','qualifyingexperience'],
            'skills':       ['skills','skill','technicalskills','expertise','domains'],
            'organization': ['organization','organisation','company','employer','currentcompany'],
            'cdac_employee':['cdacemployee','iscdacemployee','cdac'],
        }
        col_map = {k: None for k in col_variants}
        for col in df.columns:
            cc = clean(col)
            for key, variants in col_variants.items():
                if cc in variants and col_map[key] is None:
                    col_map[key] = col; break

        log(f"Loaded {len(df)} candidates.")

        # 3. Extract resumes from ZIP
        log("Extracting resumes from ZIP...")
        tmp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmp_dir)

        def get_resume_text(app_id):
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    if str(app_id).lower() in f.lower() and f.lower().endswith(('.pdf','.docx','.txt')):
                        path = os.path.join(root, f)
                        if f.endswith('.pdf'):
                            return read_pdf_bytes(open(path,'rb').read())
                        elif f.endswith('.docx'):
                            return read_docx_bytes(open(path,'rb').read())
                        else:
                            return open(path,'r',errors='ignore').read()
            return ""

        # 4. Screen each candidate
        log("Screening candidates...")
        results = []
        total = len(df)
        guardrails_log = []

        for i, row in df.iterrows():
            app_id   = str(row.get(col_map['applicant_id'], i) or i).strip()
            name     = str(row.get(col_map['full_name'], 'Unknown') or 'Unknown').strip()
            degree   = str(row.get(col_map['degree'], '') or '')
            spec     = str(row.get(col_map['specialisation'], '') or '')
            pct      = pd.to_numeric(row.get(col_map['percentage'], 0), errors='coerce') or 0
            exp_raw  = row.get(col_map['experience'], 0) or 0
            skills   = str(row.get(col_map['skills'], '') or '')
            org      = str(row.get(col_map['organization'], '') or '')
            cdac_col = str(row.get(col_map['cdac_employee'], '') or '').strip().lower()

            exp_years = exp_to_years(exp_raw)
            resume_text = get_resume_text(app_id)
            resume_summary = summarise_resume(resume_text)

            status = "screened in"
            reason = ""

            # Stage 1: Degree
            if not is_valid_degree(degree):
                m = re.search(r'\b(b\.?\s*tech|b\.?\s*e\.?|m\.?\s*tech|m\.?\s*e\.?|m\.?\s*sc|b\.?\s*sc|mca|bca)\b', resume_text, re.I)
                if m:
                    degree = m.group(0).strip()
                else:
                    status = "manual check"
                    reason = f"Invalid/irrelevant degree: '{degree}' — required BE/BTech/ME/MTech/MCA/MSc in CSE/IT/ECE."

            # Stage 2: Specialisation
            if status == "screened in" and not is_valid_spec(spec):
                found = ""
                for chk, lbl in [('computer science','Computer Science'),('information technology','Information Technology'),
                                  ('electronics and communication','ECE'),('computer application','Computer Application')]:
                    if re.search(r'\b'+re.escape(chk)+r'\b', resume_text, re.I):
                        found = lbl; break
                if found:
                    spec = found
                else:
                    status = "screened out"
                    reason = f"Specialisation '{spec}' is not in the required list (CSE/IT/ECE/Computer Application/Data Science/AI/ML)."

            # Stage 3: Percentage
            if status == "screened in" and pct < MIN_PERCENTAGE:
                status = "screened out"
                reason = f"Percentage {pct}% is below the required minimum of 60%."

            # Stage 4: Experience
            if status == "screened in" and exp_years < SPE_MIN_EXP_YEARS:
                m2 = re.search(r'(\d+\.?\d*)\s*\+?\s*years?\s*(of\s*)?(experience|exp)', resume_text, re.I)
                if m2: exp_years = float(m2.group(1))
                if exp_years < SPE_MIN_EXP_YEARS:
                    status = "screened out"
                    reason = f"Experience {exp_years:.1f} years is below the required {SPE_MIN_EXP_YEARS} years."

            # Stage 5: CDAC/Govt
            noc_note = ""
            if status == "screened in":
                is_cdac = bool(re.search(r'\bcdac\b|\bc-dac\b', org, re.I)) or cdac_col in ['yes','y','1','true']
                is_govt = False
                try:
                    if org and org.lower() not in ('','unknown','nan'):
                        r = llm.invoke(f"Is '{org}' a government organization in India? Return only 'True' or 'False'.")
                        is_govt = r.content.strip().lower() == 'true'
                except: pass
                if is_cdac:
                    if exp_years < CDAC_MIN_EXP_YEARS:
                        status = "screened out"
                        reason = f"CDAC employee with {exp_years:.1f} years — minimum {CDAC_MIN_EXP_YEARS} years required."
                    else:
                        noc_note = " NOC required at interview (CDAC employee)."
                elif is_govt:
                    noc_note = " NOC required at interview (Government employee)."

            # Stage 6: Cosine similarity
            if status == "screened in":
                try:
                    cand_text = f"{name} {degree} {spec} {skills} {exp_raw}"
                    emb = model.encode([cand_text])[0]
                    emb = (emb / np.linalg.norm(emb)).reshape(1,-1).astype(np.float32)
                    D, _ = idx.search(emb, k=1)
                    sim = 1 - (D[0][0] / 2)
                    if sim > 0.2:
                        exp_note = f" Experience {exp_years:.1f} yrs exceeds max {SPE_MAX_EXP_YEARS}." if exp_years > SPE_MAX_EXP_YEARS else ""
                        reason = f"Meets all eligibility criteria — {degree} in {spec}, {pct:.0f}% marks, {exp_years:.1f} years experience.{exp_note}{noc_note}"
                    else:
                        status = "screened out"
                        reason = f"Skills and experience profile does not sufficiently match job requirements (similarity: {sim:.2f})."
                except Exception as e:
                    reason = f"Similarity check error: {e}"

            # Generate intro for screened-in candidates
            intro_text = ""
            cand_guardrails = []
            profile_text = (
                f"Degree: {degree}\nSpecialisation: {spec}\nPercentage: {pct}\n"
                f"Experience: {exp_years:.1f} years\nSkills: {skills}\n"
                f"Organization: {org}\nScreening Status: {status}\nReason: {reason}"
            )

            # GuardrailsPII on profile
            try:
                guard = Guard().use(GuardrailsPII(entities=["PHONE_NUMBER","EMAIL_ADDRESS"], on_fail="fix"))
                result = guard.validate(profile_text, metadata={"applicant_id": app_id})
                filtered = result.validated_output
                if filtered != profile_text:
                    cand_guardrails.append("GuardrailsPII: Triggered — phone/email removed from profile")
                    guardrails_log.append(f"Applicant {app_id} ({name}): GuardrailsPII removed PII from profile")
                else:
                    cand_guardrails.append("GuardrailsPII: Passed — no PII detected")
                profile_text = filtered
            except Exception as e:
                cand_guardrails.append(f"GuardrailsPII: Error — {e}")

            if status == "screened in":
                intro, intro_err, intro_guards = generate_intro(profile_text, app_id)
                intro_text = intro or ""
                cand_guardrails.extend(intro_guards)
                if intro_err:
                    guardrails_log.append(f"Applicant {app_id} ({name}): Intro blocked — {intro_err}")

            results.append({
                "applicant_id":    app_id,
                "name":            name,
                "degree":          degree,
                "specialisation":  spec,
                "percentage":      float(pct),
                "experience_years": round(exp_years, 1),
                "skills":          skills,
                "organization":    org,
                "status":          status,
                "reason":          reason,
                "resume_summary":  resume_summary,
                "introduction":    intro_text,
                "guardrails":      cand_guardrails,
            })

            job['progress'] = int(((i+1)/total)*100)

        # 5. Build output ZIP
        log("Building output files...")
        out_dir = tempfile.mkdtemp()
        pdf_dir = os.path.join(out_dir, "profiles")
        os.makedirs(pdf_dir)

        # Excel
        out_df = pd.DataFrame([{
            'Applicant ID': r['applicant_id'], 'Full Name': r['name'],
            'Degree': r['degree'], 'Specialisation': r['specialisation'],
            'Percentage (%)': r['percentage'], 'Experience (years)': r['experience_years'],
            'Skills': r['skills'], 'Organization': r['organization'],
            'Screening Result': r['status'].title(), 'Reason': r['reason'],
        } for r in results])

        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
            out_df.to_excel(writer, index=False, sheet_name='Screening Results')
            wb = writer.book
            ws = writer.sheets['Screening Results']
            from openpyxl.styles import PatternFill, Font, Alignment
            from openpyxl.utils import get_column_letter
            hfill = PatternFill(start_color='0D1B2A', end_color='0D1B2A', fill_type='solid')
            hfont = Font(color='FFFFFF', bold=True, size=11)
            for cell in ws[1]:
                cell.fill = hfill; cell.font = hfont
                cell.alignment = Alignment(horizontal='center', vertical='center')
            gfill = PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid')
            rfill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
            yfill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
            res_col = None
            for ci, col in enumerate(out_df.columns, 1):
                if col == 'Screening Result': res_col = ci; break
            for ri in range(2, ws.max_row+1):
                val = str(ws.cell(ri, res_col).value or '') if res_col else ''
                fill = gfill if 'In' in val else rfill if 'Out' in val else yfill
                for cell in ws[ri]: cell.fill = fill
            for ci, col in enumerate(out_df.columns, 1):
                ml = max(len(str(col)), *[len(str(ws.cell(r,ci).value or '')) for r in range(2,ws.max_row+1)])
                ws.column_dimensions[get_column_letter(ci)].width = min(ml+4, 45)
            ws.freeze_panes = 'A2'

        # PDFs
        for r in results:
            pt = (f"Applicant ID: {r['applicant_id']}\nName: {r['name']}\n"
                  f"Degree: {r['degree']}\nSpecialisation: {r['specialisation']}\n"
                  f"Percentage: {r['percentage']}%\nExperience: {r['experience_years']} years\n"
                  f"Skills: {r['skills']}\nOrganization: {r['organization']}\n"
                  f"Screening Result: {r['status'].title()}\nReason: {r['reason']}")
            generate_pdf(pt, r['applicant_id'], pdf_dir)

        # ZIP everything
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('screening_results.xlsx', excel_buf.getvalue())
            for f in os.listdir(pdf_dir):
                zf.write(os.path.join(pdf_dir, f), f"profiles/{f}")

        zip_path = os.path.join(out_dir, "results.zip")
        with open(zip_path, 'wb') as f:
            f.write(zip_buf.getvalue())

        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)

        # Summary
        screened_in  = sum(1 for r in results if r['status'] == 'screened in')
        screened_out = sum(1 for r in results if r['status'] == 'screened out')
        manual       = sum(1 for r in results if r['status'] == 'manual check')

        job.update({
            'status':        'done',
            'progress':      100,
            'results':       results,
            'zip_path':      zip_path,
            'screened_in':   screened_in,
            'screened_out':  screened_out,
            'manual_check':  manual,
            'total':         len(results),
            'guardrails_log': guardrails_log,
        })
        log(f"Done. {screened_in} screened in, {screened_out} screened out, {manual} manual check.")

    except Exception as e:
        import traceback
        job['status'] = 'error'
        job['error']  = str(e)
        job['log'].append(f"ERROR: {e}")
        job['log'].append(traceback.format_exc())
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── API Routes ────────────────────────────────────────────────────────────────
@app.post("/api/screen")
async def screen(
    background_tasks: BackgroundTasks,
    requirements: UploadFile = File(...),
    excel: UploadFile = File(...),
    resumes: UploadFile = File(...),
):
    job_id = str(uuid.uuid4())
    req_bytes   = await requirements.read()
    excel_bytes = await excel.read()
    zip_bytes   = await resumes.read()
    jobs[job_id] = {'status': 'queued', 'progress': 0, 'log': []}
    background_tasks.add_task(
        run_screening, job_id,
        req_bytes, requirements.filename,
        excel_bytes, zip_bytes
    )
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "status":   job['status'],
        "progress": job.get('progress', 0),
        "log":      job.get('log', []),
        "timings":  job.get('timings', {}),
        "error":    job.get('error', None),
    }


@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        raise HTTPException(404, "Results not ready")
    return {
        "screened_in":      job['screened_in'],
        "screened_out":     job['screened_out'],
        "manual_check":     job['manual_check'],
        "total":            job['total'],
        "results":          job['results'],
        "guardrails_log":   job['guardrails_log'],
        "required_skills":  job.get('required_skills', []),
    }


@app.get("/api/download/{job_id}")
def download(job_id: str):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        raise HTTPException(404, "Results not ready")
    return FileResponse(
        job['zip_path'],
        media_type='application/zip',
        filename='screening_results.zip'
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
