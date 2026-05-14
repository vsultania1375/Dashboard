#!/usr/bin/env python3
import pandas as pd
import requests

# Create a proper engineers test CSV file
testFile = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard\test_engineers.csv"
data = {
    'engineer_code': ['001', '002', '003'],
    'engineer_name': ['Rajesh Kumar', 'Priya Singh', 'Amit Patel'],
    'state': ['Maharashtra', 'Karnataka', 'Tamil Nadu'],
    'designation': ['Engineer', 'Engineer', 'Engineer'],
    'active_status': ['YES', 'YES', 'YES'],
    'phone': ['9876543210', '9876543211', '9876543212'],
    'email': ['rajesh@company.com', 'priya@company.com', 'amit@company.com'],
    'service_area_code': ['MH001', 'KA001', 'TN001']
}

df = pd.DataFrame(data)
df.to_csv(testFile, index=False)
print(f"✅ Engineers test file created with {len(df)} rows")

# Test validate endpoint
print("\nTesting validate endpoint...")
with open(testFile, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/validate', files=files)
    
print(f"Status: {response.status_code}")
data = response.json()
print(f"✅ Data type: {data.get('data_type')}")
print(f"✅ Rows uploaded: {data.get('rows_uploaded')}")
print(f"✅ Status: {data.get('status')}")
print(f"✅ Can proceed: {data.get('can_proceed')}")
if data.get('errors'):
    print(f"Errors: {data.get('errors')}")
if data.get('warnings'):
    print(f"Warnings: {data.get('warnings')}")
