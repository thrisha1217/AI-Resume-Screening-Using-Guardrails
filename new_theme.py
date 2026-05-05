THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; font-size: 16px; }

header[data-testid="stHeader"], #MainMenu, footer,
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }

.stApp { background: #F0F4F8; }
.main { padding: 0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

.topbar {
    background: #0D1B2A; height: 68px;
    display: flex; align-items: center;
    padding: 0 2.5rem; gap: 0.9rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.topbar-icon {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #10B981, #059669);
    border-radius: 10px; display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; box-shadow: 0 4px 12px rgba(16,185,129,0.4); flex-shrink: 0;
}
.topbar-title { font-size: 1.15rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.2px; }
.topbar-sub { font-size: 0.78rem; color: rgba(255,255,255,0.4); margin-top: 1px; }
.topbar-divider { flex: 1; }
.topbar-status {
    display: flex; align-items: center; gap: 0.45rem;
    background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25);
    border-radius: 20px; padding: 0.3rem 0.9rem;
    font-size: 0.8rem; color: #6EE7B7; font-weight: 500;
}
.status-dot { width: 7px; height: 7px; background: #10B981; border-radius: 50%; box-shadow: 0 0 5px #10B981; }

.hero-banner {
    background: #0D1B2A; padding: 3rem 2.5rem 2.8rem;
    position: relative; overflow: hidden;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.hero-banner::before {
    content: ''; position: absolute; top: -80px; right: -80px;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 65%);
    border-radius: 50%;
}
.hero-tag {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.25);
    color: #6EE7B7; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 1.8px; text-transform: uppercase;
    padding: 0.3rem 0.85rem; border-radius: 20px; margin-bottom: 1.2rem;
}
.hero-h1 { font-size: 2.4rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.6px; line-height: 1.15; margin-bottom: 0.8rem; }
.hero-h1 span { color: #10B981; }
.hero-p { font-size: 1rem; color: rgba(255,255,255,0.5); max-width: 500px; line-height: 1.75; margin-bottom: 2rem; }
.hero-chips { display: flex; gap: 0.7rem; flex-wrap: wrap; margin-bottom: 2rem; }
.hero-chip {
    display: flex; align-items: center; gap: 0.45rem;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 0.55rem 1rem;
    font-size: 0.85rem; color: rgba(255,255,255,0.7); font-weight: 500;
}
.chip-num {
    width: 22px; height: 22px;
    background: linear-gradient(135deg, #10B981, #059669);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 0.68rem; font-weight: 700; color: #FFFFFF;
    box-shadow: 0 2px 6px rgba(16,185,129,0.4);
}

.stButton > button {
    background: linear-gradient(135deg, #059669, #10B981) !important;
    color: #FFFFFF !important; border: none !important;
    padding: 0.85rem 2.5rem !important; border-radius: 10px !important;
    font-size: 1.05rem !important; font-weight: 700 !important;
    box-shadow: 0 4px 16px rgba(16,185,129,0.45) !important;
    transition: all 0.25s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #047857, #059669) !important;
    box-shadow: 0 8px 24px rgba(16,185,129,0.55) !important;
    transform: translateY(-3px) !important;
}
.stDownloadButton > button {
    background: #FFFFFF !important; color: #059669 !important;
    border: 1.5px solid #10B981 !important;
    padding: 0.7rem 1.8rem !important; border-radius: 10px !important;
    font-size: 1rem !important; font-weight: 600 !important;
    width: 100% !important; transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: #F0FDF4 !important;
    box-shadow: 0 4px 14px rgba(16,185,129,0.2) !important;
    transform: translateY(-1px) !important;
}

.stFileUploader {
    background: #FFFFFF !important; border: 1.5px solid #E2E8F0 !important;
    border-radius: 14px !important; padding: 1.25rem !important;
    transition: all 0.25s ease !important; box-shadow: 0 1px 6px rgba(0,0,0,0.06) !important;
}
.stFileUploader:hover {
    border-color: #10B981 !important;
    box-shadow: 0 0 0 3px rgba(16,185,129,0.1), 0 6px 20px rgba(0,0,0,0.08) !important;
    transform: translateY(-2px) !important;
}
.stFileUploader label { color: #1E293B !important; font-size: 1rem !important; font-weight: 600 !important; }
.stFileUploader button {
    background: linear-gradient(135deg, #059669, #10B981) !important;
    color: #FFFFFF !important; border: none !important;
    padding: 0.5rem 1.2rem !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 0.9rem !important;
    box-shadow: 0 3px 8px rgba(16,185,129,0.4) !important; transition: all 0.2s !important;
}
.stFileUploader button:hover {
    background: linear-gradient(135deg, #047857, #059669) !important;
    box-shadow: 0 5px 14px rgba(16,185,129,0.5) !important; transform: translateY(-1px) !important;
}
.stFileUploader section { border: 1.5px dashed #CBD5E1 !important; background: #F8FAFC !important; border-radius: 10px !important; }
.stFileUploader section:hover { border-color: #10B981 !important; background: #F0FDF4 !important; }
.stFileUploader small, .stFileUploader p { color: #94A3B8 !important; font-size: 0.85rem !important; }

.stTabs [data-baseweb="tab-list"] {
    background: #FFFFFF !important; border-radius: 12px 12px 0 0 !important;
    border: 1px solid #E2E8F0 !important; border-bottom: none !important;
    padding: 0.6rem 0.6rem 0 !important; gap: 0.3rem !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border-radius: 8px 8px 0 0 !important;
    color: #64748B !important; font-size: 0.95rem !important;
    font-weight: 500 !important; padding: 0.7rem 1.4rem !important;
    border: none !important; transition: all 0.2s !important;
}
.stTabs [data-baseweb="tab"]:hover { background: #F0FDF4 !important; color: #059669 !important; }
.stTabs [aria-selected="true"] {
    background: #F0FDF4 !important; color: #059669 !important;
    font-weight: 700 !important; border-bottom: 2.5px solid #10B981 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
    border-top: none !important; border-radius: 0 0 12px 12px !important;
    padding: 2rem !important; box-shadow: 0 4px 16px rgba(0,0,0,0.05) !important;
}

.stDataFrame { border: 1px solid #E2E8F0 !important; border-radius: 10px !important; overflow: hidden !important; box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important; }

.stTextInput > div > div > input {
    background: #FFFFFF !important; border: 1.5px solid #E2E8F0 !important;
    border-radius: 9px !important; color: #0F172A !important;
    font-size: 1rem !important; padding: 0.65rem 1rem !important; transition: all 0.2s !important;
}
.stTextInput > div > div > input:focus { border-color: #10B981 !important; box-shadow: 0 0 0 3px rgba(16,185,129,0.12) !important; }

.stSuccess > div { background: #F0FDF4 !important; border: 1px solid #A7F3D0 !important; border-left: 4px solid #10B981 !important; border-radius: 9px !important; color: #065F46 !important; font-size: 1rem !important; }
.stInfo > div { background: #EFF6FF !important; border: 1px solid #BFDBFE !important; border-left: 4px solid #3B82F6 !important; border-radius: 9px !important; color: #1D4ED8 !important; font-size: 1rem !important; }
.stWarning > div { background: #FFFBEB !important; border: 1px solid #FDE68A !important; border-left: 4px solid #F59E0B !important; border-radius: 9px !important; color: #92400E !important; font-size: 1rem !important; }
.stError > div { background: #FEF2F2 !important; border: 1px solid #FECACA !important; border-left: 4px solid #EF4444 !important; border-radius: 9px !important; color: #991B1B !important; font-size: 1rem !important; }

.stProgress > div > div > div { background: linear-gradient(90deg, #059669, #34D399) !important; border-radius: 6px !important; }
.stProgress > div > div { background: #E2E8F0 !important; border-radius: 6px !important; height: 10px !important; }

h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; font-size: 1.6rem !important; }
h4, h5, h6 { color: #1E293B !important; font-weight: 600 !important; font-size: 1.15rem !important; }
p, .stMarkdown p { color: #475569; font-size: 1rem; line-height: 1.7; }
.stMarkdown strong { color: #1E293B; }
.stMarkdown table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
.stMarkdown th { background: #F8FAFC; color: #374151; font-weight: 600; padding: 0.75rem 1rem; border: 1px solid #E2E8F0; text-align: left; }
.stMarkdown td { padding: 0.7rem 1rem; border: 1px solid #E2E8F0; color: #374151; }
.stMarkdown tr:nth-child(even) td { background: #F8FAFC; }

hr { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #F1F5F9; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #10B981; }
.stSpinner > div { border-top-color: #10B981 !important; }
.element-container p { color: #475569 !important; font-size: 1rem !important; }
</style>
"""

NAVBAR_HTML = """
<div class='topbar'>
    <div class='topbar-icon'>&#128269;</div>
    <div>
        <div class='topbar-title'>Resume Screening System</div>
        <div class='topbar-sub'>AI-Powered Candidate Evaluation Platform</div>
    </div>
    <div class='topbar-divider'></div>
    <div class='topbar-status'>
        <div class='status-dot'></div>
        System Online
    </div>
</div>
<div class='hero-banner'>
    <div class='hero-tag'>&#9889; Automated AI Screening</div>
    <div class='hero-h1'>Smart <span>Resume Screening</span><br>Powered by AI</div>
    <div class='hero-p'>Upload your job requirements, candidate data, and resumes. The system automatically screens all candidates using eligibility rules and semantic skill matching.</div>
    <div class='hero-chips'>
        <div class='hero-chip'><div class='chip-num'>1</div>Upload Requirements</div>
        <div class='hero-chip'><div class='chip-num'>2</div>Upload Candidate Excel</div>
        <div class='hero-chip'><div class='chip-num'>3</div>Upload Resume ZIP</div>
        <div class='hero-chip'><div class='chip-num'>4</div>Click Analyze Resumes</div>
        <div class='hero-chip'><div class='chip-num'>5</div>View Results</div>
    </div>
</div>
"""
