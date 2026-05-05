# AI Resume Screening System Using Guardrails

An AI-powered resume screening web application that automatically evaluates job applicants and decides who should be called for an interview — replacing manual HR screening.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite |
| Backend API | FastAPI + Uvicorn |
| Streamlit App | Python + Streamlit (alternative UI) |
| LLM | Llama 3.2 via Ollama (runs locally) |
| Embeddings | SentenceTransformer (all-MiniLM-L6-v2) |
| Vector Search | FAISS (Facebook AI Similarity Search) |
| Safety | Guardrails AI (ToxicLanguage, NSFWText, GuardrailsPII) |
| Data | Pandas, OpenPyXL |
| PDF Generation | FPDF |
| Resume Parsing | PyPDF2, python-docx |

---

## Project Structure

```
├── api.py                  # FastAPI backend (REST API for React frontend)
├── main.py                 # Streamlit app (alternative UI)
├── new_theme.py            # UI theme constants for Streamlit
├── spe_da_screening.py     # Standalone screening script
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit server config (1GB upload limit)
└── frontend/               # React + TypeScript UI
    ├── src/
    │   ├── App.tsx
    │   ├── api.ts           # API calls to FastAPI backend
    │   ├── types.ts         # TypeScript interfaces
    │   ├── index.css        # Global styles
    │   └── pages/
    │       ├── HomePage.tsx
    │       ├── UploadPage.tsx
    │       └── ResultsPage.tsx
    ├── index.html
    ├── vite.config.ts
    └── package.json
```

---

## Features

### 6-Stage Screening Pipeline
Each candidate goes through these checks in order — stops at first failure:

1. **Degree Validation** — BE/BTech/ME/MTech/MCA/MSc in tech field. Falls back to resume PDF if Excel is unclear.
2. **Specialisation Validation** — CSE/IT/ECE/Computer Application/Data Science/AI/ML. Falls back to resume PDF.
3. **Percentage Check** — Minimum 60% required.
4. **Experience Check** — Minimum 4 years required. Falls back to resume PDF.
5. **Organisation Rules** — Government employees and CDAC employees need NOC. CDAC employees need minimum 3 years at CDAC.
6. **Cosine Similarity** — Candidate skills/profile vs job requirements using FAISS vector search. Threshold: 0.2.

### AI Features (requires Ollama)
- **Degree Extraction** — Llama 3.2 reads raw resume text and extracts degree names
- **Org Check** — LLM determines if an organization is a government body in India
- **Candidate Introduction** — LLM generates a 2-paragraph professional summary per candidate

### Guardrails Safety
Every LLM output is validated before use:

| Validator | Checks | Action |
|---|---|---|
| **ToxicLanguage** | Hate speech, offensive language | Rejects output |
| **NSFWText** | Inappropriate content | Rejects output |
| **GuardrailsPII** | Phone numbers, email addresses | Auto-removes PII |

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/download) installed and running

### 1. Clone the repository
```bash
git clone https://github.com/thrisha1217/AI-Resume-Screening-Using-Guardrails.git
cd AI-Resume-Screening-Using-Guardrails
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Guardrails validators
```bash
guardrails hub install hub://guardrails/toxic_language
guardrails hub install hub://guardrails/nsfw_text
guardrails hub install hub://guardrails/guardrails_pii
```

### 4. Pull the LLM model
```bash
ollama pull llama3.2
```

### 5. Install frontend dependencies
```bash
cd frontend
npm install
```

---

## Running the Application

### Option A — React + FastAPI (Recommended)

**Terminal 1 — Start FastAPI backend:**
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Start React frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**

---

### Option B — Streamlit App

```bash
python -m streamlit run main.py
```

Open **http://localhost:8501**

---

## How to Use

1. **Home Page** — Click **"Analyze Resumes"**
2. **Upload Page** — Upload 3 files:
   - Requirements Document (PDF/DOCX/TXT) — job description
   - Candidate Excel (.xlsx) — candidate database
   - Resume Folder (.zip) — all candidate resume PDFs
3. Click **"Start Screening"**
4. **Results Page** — View:
   - Summary cards (Screened In / Out / Manual Check / Total)
   - Tabs to browse each group with candidate details
   - Click **View** on any candidate to see full profile, AI introduction, and guardrails log
   - **Guardrails Report** tab shows all validators used and activity log
   - Download ZIP with colour-coded Excel + candidate PDFs

---

## Input File Format

### Excel File
The system auto-detects column names. Supported variants:

| Field | Accepted column names |
|---|---|
| Applicant ID | applicantid, candidateid, applicationid |
| Full Name | fullname, name, candidatename |
| Degree | degree, qualification, education |
| Specialisation | specialisation, specialization, branch, stream |
| Percentage | percentage, percent, marks, cgpa, gpa |
| Experience | totalexperience, experience, experienceyears |
| Skills | skills, skill, technicalskills, expertise |
| Organization | organization, organisation, company, employer |

### Resume ZIP
Name resume files with the Applicant ID in the filename:
```
482845_Yogesh_Kumar.pdf
484764_Katravulapalli_Sravani.pdf
```

---

## Output

The downloaded ZIP contains:
- `screening_results.xlsx` — colour-coded Excel (🟢 green = in, 🔴 red = out, 🟡 yellow = manual)
- `full_data.xlsx` — complete raw data
- `profiles/` — PDF profile card per candidate

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/screen` | Submit files for screening, returns `job_id` |
| GET | `/api/status/{job_id}` | Poll screening progress |
| GET | `/api/results/{job_id}` | Get full screening results |
| GET | `/api/download/{job_id}` | Download results ZIP |
| GET | `/api/health` | Health check |

---

## License

MIT License
