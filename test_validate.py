#!/usr/bin/env python3
import requests
import os

testFile = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard\test_upload.csv"

print("Testing upload validate endpoint...")

# Test with proper multipart form
with open(testFile, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/validate', files=files)
    
print(f"Status: {response.status_code}")

if response.status_code == 200:
    print("✅ Validate endpoint working!")
    data = response.json()
    print(f"✅ Data type: {data.get('data_type')}")
    print(f"✅ Rows uploaded: {data.get('rows_uploaded')}")
    print(f"✅ Rows valid: {data.get('rows_valid')}")
    print(f"✅ Status: {data.get('status')}")
    print(f"✅ Can proceed: {data.get('can_proceed')}")
    if data.get('errors'):
        print(f"Errors: {data.get('errors')}")
    if data.get('warnings'):
        print(f"Warnings: {data.get('warnings')}")
else:
    print(f"Response status: {response.status_code}")
    try:
        print(response.json())
    except:
        print(response.text[:500])
