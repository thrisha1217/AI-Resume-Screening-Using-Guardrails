import pandas as pd
import sys
import re

if len(sys.argv) < 2:
    print("Usage: python check_excel_columns.py <path_to_excel_file>")
    sys.exit(1)

excel_file = sys.argv[1]

try:
    df = pd.read_excel(excel_file, header=0)
    
    print("\n" + "="*60)
    print("ORIGINAL COLUMN NAMES:")
    print("="*60)
    for i, col in enumerate(df.columns, 1):
        print(f"{i}. '{col}'")
    
    print("\n" + "="*60)
    print("CLEANED COLUMN NAMES (lowercase, no special chars):")
    print("="*60)
    cleaned_cols = [re.sub(r'[^a-z0-9]', '', col.lower()) for col in df.columns]
    for i, col in enumerate(cleaned_cols, 1):
        print(f"{i}. '{col}'")
    
    print("\n" + "="*60)
    print("REQUIRED COLUMNS:")
    print("="*60)
    required = ['sno', 'fullname', 'age', 'email', 'mobilenumber', 'degree',
                'specialisation', 'percentage', 'totalexperience', 'skills', 'applicantid']
    for col in required:
        print(f"  - {col}")
    
    print("\n" + "="*60)
    print("COLUMN MATCHING RESULTS:")
    print("="*60)
    
    column_variants = {
        'sno': ['sno', 'serialno', 'serialnumber', 'srno', 'slno', 'number', 'no', 'id'],
        'fullname': ['fullname', 'name', 'candidatename', 'applicantname'],
        'age': ['age'],
        'email': ['email', 'emailid', 'emailaddress', 'mail'],
        'mobilenumber': ['mobilenumber', 'mobile', 'phone', 'phonenumber', 'contact', 'contactnumber'],
        'degree': ['degree', 'qualification', 'education'],
        'specialisation': ['specialisation', 'specialization', 'branch', 'stream', 'major'],
        'percentage': ['percentage', 'percent', 'marks', 'cgpa', 'gpa', 'score'],
        'totalexperience': ['totalexperience', 'experience', 'exp', 'workexperience', 'yearsofexperience'],
        'skills': ['skills', 'skill', 'technicalskills', 'expertise'],
        'applicantid': ['applicantid', 'candidateid', 'applicationid', 'appid'],
    }
    
    column_mappings = {key: None for key in column_variants.keys()}
    
    for col in df.columns:
        col_clean = re.sub(r'[^a-z0-9]', '', col.lower())
        for key, variants in column_variants.items():
            if col_clean in variants and column_mappings[key] is None:
                column_mappings[key] = col
                break
    
    for key, value in column_mappings.items():
        status = "✓ FOUND" if value else "✗ MISSING"
        print(f"{status:12} {key:20} -> {value if value else 'N/A'}")
    
    missing = [k for k, v in column_mappings.items() if v is None and k in required]
    if missing:
        print("\n" + "="*60)
        print("⚠ MISSING REQUIRED COLUMNS:")
        print("="*60)
        for col in missing:
            print(f"  - {col}")
            print(f"    Accepted variants: {', '.join(column_variants[col])}")
    else:
        print("\n✓ All required columns found!")
    
    print("\n" + "="*60)
    print(f"Total rows: {len(df)}")
    print("="*60)
    
except Exception as e:
    print(f"Error reading Excel file: {e}")
    import traceback
    traceback.print_exc()
