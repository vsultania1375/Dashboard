#!/usr/bin/env python3
"""
Test file upload functionality through the frontend API endpoints
Simulates what the browser does when uploading files
"""
import requests
import pandas as pd
import os
import json

# URLs
API_BASE = "http://localhost:8000"

# Create test files
test_dir = r"C:\Users\Vivek\Desktop\dashboard 2\dashboard"

# 1. Create test engineers file
print("=" * 60)
print("Testing File Upload Functionality")
print("=" * 60)

engineers_file = os.path.join(test_dir, "test_engineers.csv")
data = {
    'engineer_code': ['001', '002', '003', '004', '005'],
    'engineer_name': ['Rajesh Kumar', 'Priya Singh', 'Amit Patel', 'Neha Verma', 'Ravi Sharma'],
    'state': ['Maharashtra', 'Karnataka', 'Tamil Nadu', 'Delhi', 'Uttar Pradesh'],
    'designation': ['Engineer', 'Engineer', 'Engineer', 'Engineer', 'Engineer'],
    'active_status': ['YES', 'YES', 'YES', 'YES', 'YES'],
    'phone': ['9876543210', '9876543211', '9876543212', '9876543213', '9876543214'],
    'email': ['rajesh@company.com', 'priya@company.com', 'amit@company.com', 'neha@company.com', 'ravi@company.com'],
    'service_area_code': ['MH001', 'KA001', 'TN001', 'DL001', 'UP001']
}
df = pd.DataFrame(data)
df.to_csv(engineers_file, index=False)
print(f"\n✅ Created test file: {engineers_file}")

# 2. Test Preview Endpoint
print("\n" + "-" * 60)
print("1. Testing Preview Endpoint (/api/upload/preview)")
print("-" * 60)

try:
    with open(engineers_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(f'{API_BASE}/api/upload/preview?rows=10', files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Preview successful!")
        print(f"   Columns: {', '.join(data['columns'])}")
        print(f"   Total rows: {data['total_rows']}")
        print(f"   Sample data: {len(data['preview_data'])} rows returned")
    else:
        print(f"❌ Preview failed with status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

# 3. Test Validate Endpoint
print("\n" + "-" * 60)
print("2. Testing Validate Endpoint (/api/upload/validate)")
print("-" * 60)

try:
    with open(engineers_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(f'{API_BASE}/api/upload/validate', files=files)
    
    if response.status_code == 200:
        validation_data = response.json()
        print(f"✅ Validation successful!")
        print(f"   Data type: {validation_data['data_type']}")
        print(f"   Status: {validation_data['status']}")
        print(f"   Rows valid: {validation_data['rows_valid']}/{validation_data['rows_uploaded']}")
        print(f"   Can proceed: {validation_data['can_proceed']}")
        
        if validation_data.get('errors'):
            print(f"   Errors: {validation_data['errors']}")
        if validation_data.get('warnings'):
            print(f"   Warnings: {validation_data['warnings']}")
        
        upload_id = validation_data['upload_id']
        print(f"   Upload ID: {upload_id}")
    else:
        print(f"❌ Validation failed with status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

# 4. Test Confirm Endpoint
print("\n" + "-" * 60)
print("3. Testing Confirm Endpoint (/api/upload/confirm)")
print("-" * 60)

try:
    if upload_id:
        response = requests.post(f'{API_BASE}/api/upload/confirm?upload_id={upload_id}')
        
        if response.status_code == 200:
            confirm_data = response.json()
            print(f"✅ Confirmation successful!")
            print(f"   Status: {confirm_data.get('status')}")
            print(f"   Rows to load: {confirm_data.get('rows_to_load')}")
        else:
            print(f"❌ Confirmation failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

# 5. Test History Endpoint
print("\n" + "-" * 60)
print("4. Testing History Endpoint (/api/upload/history)")
print("-" * 60)

try:
    response = requests.get(f'{API_BASE}/api/upload/history?limit=5')
    
    if response.status_code == 200:
        history_data = response.json()
        print(f"✅ History retrieved!")
        print(f"   Recent uploads: {len(history_data.get('recent_uploads', []))}")
        if history_data.get('recent_uploads'):
            for upload in history_data['recent_uploads'][:2]:
                print(f"   - {upload.get('filename')}: {upload.get('status')}")
    else:
        print(f"❌ History failed with status {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# 6. Test Template Endpoint
print("\n" + "-" * 60)
print("5. Testing Template Endpoint (/api/upload/template)")
print("-" * 60)

try:
    response = requests.get(f'{API_BASE}/api/upload/template/engineers')
    
    if response.status_code == 200:
        template_data = response.json()
        print(f"✅ Template retrieved!")
        print(f"   Columns: {', '.join(template_data['columns'])}")
        print(f"   Notes: {len(template_data.get('notes', []))} provided")
    else:
        print(f"❌ Template failed with status {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
