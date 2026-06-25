"""
Test script — submits a screening job and polls until done, then prints results.
"""
import requests
import time
import json

BASE = "http://localhost:8000"

REQ_FILE   = r"D:\Guardrails\All Required Files\Applications Screening - Senior Project Engineers for Sinkhole Traffic Project - (JIT_01_2026-HY (JIT-XII)\SPE(Data Analyst) 1 position.pdf"
EXCEL_FILE = r"D:\Guardrails\All Required Files\SPE-I-DA-Screening.xlsx"
ZIP_FILE   = r"D:\Guardrails\All Required Files\SPE-DA I-Profiles.zip"

import os
# fallback excel if first not found
if not os.path.exists(EXCEL_FILE):
    EXCEL_FILE = r"D:\Guardrails\All Required Files\PE-DA-Screening (2).xlsx"

print("=" * 60)
print("RESUME SCREENING SYSTEM — TEST RUN")
print("=" * 60)
print(f"Requirements : {os.path.basename(REQ_FILE)}")
print(f"Excel        : {os.path.basename(EXCEL_FILE)}")
print(f"Resumes ZIP  : {os.path.basename(ZIP_FILE)}")
print()

# 1. Submit job
print("Submitting job...")
t_start = time.time()
with open(REQ_FILE, 'rb') as r, open(EXCEL_FILE, 'rb') as e, open(ZIP_FILE, 'rb') as z:
    resp = requests.post(f"{BASE}/api/screen", files={
        "requirements": (os.path.basename(REQ_FILE),   r, "application/pdf"),
        "excel":        (os.path.basename(EXCEL_FILE), e, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "resumes":      (os.path.basename(ZIP_FILE),   z, "application/zip"),
    }, timeout=60)

job_id = resp.json()["job_id"]
print(f"Job ID: {job_id}")
print()

# 2. Poll until done
last_msg = ""
while True:
    s = requests.get(f"{BASE}/api/status/{job_id}").json()
    status   = s["status"]
    progress = s["progress"]
    logs     = s.get("log", [])
    msg      = logs[-1] if logs else ""

    if msg != last_msg:
        elapsed = round(time.time() - t_start, 1)
        print(f"  [{elapsed:6.1f}s] {progress:3d}%  {msg}")
        last_msg = msg

    if status == "done":
        break
    elif status == "error":
        print(f"\nERROR: {s.get('error')}")
        exit(1)
    time.sleep(1)

t_total = round(time.time() - t_start, 1)

# 3. Fetch results
r = requests.get(f"{BASE}/api/results/{job_id}").json()

print()
print("=" * 60)
print(f"COMPLETED IN {t_total}s  |  {r['total']} candidates")
print("=" * 60)
print(f"  ✅ Screened In  : {r['screened_in']}")
print(f"  ❌ Screened Out : {r['screened_out']}")
print(f"  ⚠️  Manual Check : {r['manual_check']}")
print()

# Timings
timings = s.get("timings", {})
if timings:
    print("─── STAGE TIMINGS ───────────────────────────────────")
    for stage, secs in timings.items():
        bar = "█" * int(secs / 2)
        print(f"  {stage:<45} {secs:6.2f}s  {bar}")
    print()

# Screened In
print("─── SCREENED IN ─────────────────────────────────────")
for c in r["results"]:
    if c["status"] == "screened in":
        print(f"  [{c['applicant_id']}] {c['name']:<35} {c['degree'][:15]:<15} {c['specialisation'][:20]:<20} {c['percentage']}%  {c['experience_years']}yrs")

print()
print("─── SCREENED OUT ────────────────────────────────────")
for c in r["results"]:
    if c["status"] == "screened out":
        print(f"  [{c['applicant_id']}] {c['name']:<35} {c['reason'][:70]}")

print()
print("─── MANUAL CHECK ────────────────────────────────────")
for c in r["results"]:
    if c["status"] == "manual check":
        print(f"  [{c['applicant_id']}] {c['name']:<35} {c['reason'][:70]}")

print()
print("─── SAMPLE AI INTRODUCTION (first screened-in) ──────")
for c in r["results"]:
    if c["status"] == "screened in" and c.get("introduction"):
        print(f"  Candidate: {c['name']} [{c['applicant_id']}]")
        print(f"  {c['introduction'][:400]}...")
        break

print()
print("─── GUARDRAILS SUMMARY ──────────────────────────────")
if r.get("guardrails_log"):
    for entry in r["guardrails_log"]:
        print(f"  ⚠️  {entry}")
else:
    print("  ✅ All candidates passed ToxicLanguage, NSFWText & PII checks")

print()
print(f"✅ TOTAL TIME: {t_total}s for {r['total']} candidates")
print("=" * 60)
