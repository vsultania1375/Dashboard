#!/usr/bin/env python3
import requests
import os

testFile = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard\test_upload.csv"

print("Testing upload preview endpoint...")
print(f"File exists: {os.path.exists(testFile)}")

# Test with proper multipart form
with open(testFile, 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload/preview?rows=10', files=files)
    
print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    print("✅ Preview endpoint working!")
    data = response.json()
    print(f"✅ Columns: {', '.join(data['columns'])}")
    print(f"✅ Total rows: {data['total_rows']}")
    print(f"✅ Preview data:")
    for row in data.get('preview_data', [])[:3]:
        print(f"   {row}")
else:
    print(f"Response: {response.text[:500]}")
    print("\n\nFull response:")
    try:
        print(response.json())
    except:
        print(response.text)
