#!/usr/bin/env python3
import pandas as pd
import requests

# Create a test Excel file with multiple sheets
test_file = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard\test_multi_sheet.xlsx"

# Sheet1 - Sample data
sheet1_data = {
    'id': [1, 2, 3],
    'name': ['A', 'B', 'C'],
    'value': [10, 20, 30]
}

# B2B Sheet - Offline sites data
b2b_data = {
    'site_id': ['SITE001', 'SITE002', 'SITE003'],
    'site_name': ['PSU Bank', 'State Bank', 'Central Bank'],
    'state': ['Maharashtra', 'Karnataka', 'Tamil Nadu'],
    'segment': ['PSU', 'PSU', 'PSU'],
    'last_online_date': ['2026-04-01', '2026-03-15', '2026-02-28'],
    'offline_duration_days': [45, 60, 75],
    'priority': ['HIGH', 'HIGH', 'MEDIUM']
}

with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
    pd.DataFrame(sheet1_data).to_excel(writer, sheet_name='Sheet1', index=False)
    pd.DataFrame(b2b_data).to_excel(writer, sheet_name='B2B', index=False)

print("✅ Created test file with 2 sheets")
print()

# Test listing sheets
print("1. Testing sheet listing...")
print("=" * 60)

with open(test_file, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/sheets', files=files)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Available sheets: {data['sheets']}")
    print(f"   Default sheet: {data['default_sheet']}")
else:
    print(f"❌ Error: {response.status_code}")

# Test preview from B2B sheet
print()
print("2. Testing preview from B2B sheet...")
print("=" * 60)

with open(test_file, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/preview?rows=10&sheet=B2B', files=files)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Preview from sheet: {data.get('sheet_name')}")
    print(f"   Columns: {', '.join(data['columns'])}")
    print(f"   Total rows: {data['total_rows']}")
    print(f"   First row: {data['preview_data'][0] if data['preview_data'] else 'N/A'}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text[:200])
