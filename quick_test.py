#!/usr/bin/env python3
import requests

response = requests.get('http://localhost:8000/api/upload/template/engineers', allow_redirects=True)

print(f"Status: {response.status_code}")
print(f"Method in URL: {response.request.method}")
print(f"URL: {response.url}")

if response.status_code == 200:
    print("✅ Template endpoint working!")
    data = response.json()
    print(f"   Columns: {len(data['columns'])} columns")
else:
    print(f"Response content: {response.text[:200]}")
