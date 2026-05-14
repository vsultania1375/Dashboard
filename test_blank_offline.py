#!/usr/bin/env python3
import pandas as pd
import requests

# Create a proper offline_sites test file with blank rows mixed in
test_file = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard\test_blank_offline.xlsx"

data = {
    'site_id': ['SITE001', 'SITE002', '', '', 'SITE003', '', 'SITE004'],
    'site_name': ['PSU Bank A', 'PSU Bank B', '', '', 'PSU Bank C', '', 'PSU Bank D'],
    'state': ['Delhi', 'Mumbai', '', '', 'Bangalore', '', 'Chennai'],
    'segment': ['PSU', 'PSU', '', '', 'PSU', '', 'PSU'],
    'last_online_date': ['2026-01-01', '2026-01-15', '', '', '2026-02-01', '', '2026-02-15'],
    'offline_duration_days': ['100', '85', '', '', '70', '', '60'],
    'priority': ['HIGH', 'HIGH', '', '', 'MEDIUM', '', 'MEDIUM']
}

df = pd.DataFrame(data)
df.to_excel(test_file, index=False)

print("Created test file with blank rows")
print(f"Total rows in file: {len(df)}")
print("Sample rows (first 4):")
print(df.head(4))
print()

# Test validation
print("Testing validation with blank row removal...")
print("=" * 60)

with open(test_file, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/validate', files=files)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Validation result:")
    print(f"   Rows uploaded: {data['rows_uploaded']}")
    print(f"   Rows valid: {data['rows_valid']}")
    print(f"   Rows invalid: {data['rows_invalid']}")
    print(f"   Status: {data['status']}")
    print(f"   Data type: {data['data_type']}")
    print(f"   Warnings:")
    for warning in data.get('warnings', []):
        print(f"     - {warning}")
    if data.get('errors'):
        print(f"   Errors:")
        for error in data.get('errors', []):
            print(f"     - {error}")
else:
    print(f"Status: {response.status_code}")
    print(response.text[:500])
