#!/usr/bin/env python3
import pandas as pd
from backend.api.upload_handler import UploadProcessor

# Create test data exactly as it would appear after read
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
print("Original DataFrame:")
print(f"Shape: {df.shape}")
print(df)
print("\nRow analysis:")
for i, row in df.iterrows():
    values = [str(v).strip() if pd.notna(v) else None for v in row]
    values = [v for v in values if v is not None]
    print(f"Row {i}: {len(values)} non-empty values")

print("\n" + "="*60)
print("Testing blank row removal...")

cleaned_df, removed = UploadProcessor.remove_blank_rows(df)
print(f"Rows removed: {removed}")
print(f"Cleaned shape: {cleaned_df.shape}")
print("\nCleaned DataFrame:")
print(cleaned_df)
