#!/usr/bin/env python3
import pandas as pd
import requests

# Create a test file with blank rows
test_file = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard\test_blank_rows.csv"

data = {
    'site_id': ['SITE001', 'SITE002', None, 'SITE004', '', 'SITE006'],
    'site_name': ['Bank A', 'Bank B', None, 'Bank D', '', 'Bank F'],
    'state': ['Maharashtra', 'Karnataka', None, 'Tamil Nadu', '', 'Delhi'],
    'segment': ['PSU', 'PSU', None, 'PSU', '', 'PSU'],
    'last_online_date': ['2026-01-01', '2026-01-15', None, '2026-02-01', '', '2026-02-15'],
    'offline_duration_days': [100, 85, None, 70, '', 60],
    'priority': ['HIGH', 'HIGH', None, 'HIGH', '', 'MEDIUM']
}

df = pd.DataFrame(data)
df.to_csv(test_file, index=False)

print("Created test file with blank rows")
print(f"Total rows in file: {len(df)}")
print()

# Test validation
print("Testing validation with blank row removal...")
print("=" * 60)

with open(test_file, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/validate', files=files)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Validation successful")
    print(f"   Rows uploaded: {data['rows_uploaded']}")
    print(f"   Rows valid: {data['rows_valid']}")
    print(f"   Warnings: {data.get('warnings', [])}")
else:
    print(f"Status: {response.status_code}")
    print(response.text[:300])
