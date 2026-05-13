"""
Data Seeding Script for VProtect Dashboard
Populates SQLite database with comprehensive test data for all 5 data types
Run this after database initialization to seed the system
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "vprotect_dashboard.db"

# Sample data
STATES = ["Maharashtra", "Karnataka", "Tamil Nadu", "Telangana", "Gujarat", "Punjab", "Rajasthan"]
ENGINEERS = [
    ("001", "Rajesh Kumar", "Mumbai"), ("002", "Priya Singh", "Bangalore"),
    ("003", "Amit Patel", "Chennai"), ("004", "Deepak Sharma", "Hyderabad"),
    ("005", "Neha Gupta", "Ahmedabad"), ("006", "Vikram Singh", "Chandigarh"),
    ("007", "Anjali Verma", "Jaipur"), ("008", "Karan Malhotra", "Pune"),
    ("009", "Sneha Reddy", "Visakhapatnam"), ("010", "Arjun Desai", "Vadodara"),
    ("011", "Divya Nair", "Kochi"), ("012", "Rohan Khan", "Lucknow"),
    ("013", "Sakshi Rao", "Indore"), ("014", "Nikhil Saxena", "Delhi"),
    ("015", "Pooja Singh", "Kolkata"), ("016", "Harsh Verma", "Surat"),
    ("017", "Rhea Patel", "Bhopal"), ("018", "Sanjay Kumar", "Gurgaon"),
    ("019", "Meera Chopra", "Noida"), ("020", "Aakash Joshi", "Nagpur"),
]

SITES = [
    ("SITE001", "Punjab National Bank", "Punjab", 25),
    ("SITE002", "HDFC Branch - Metro", "Maharashtra", 42),
    ("SITE003", "SBI Branch - Downtown", "Karnataka", 59),
    ("SITE004", "ICICI Bank", "Tamil Nadu", 8),
    ("SITE005", "Axis Bank - Central", "Telangana", 15),
    ("SITE006", "Bank of India", "Gujarat", 31),
    ("SITE007", "PNB Chandigarh", "Punjab", 45),
    ("SITE008", "IDBI Bank", "Rajasthan", 67),
    ("SITE009", "Canara Bank", "Maharashtra", 22),
    ("SITE010", "Indian Overseas Bank", "Tamil Nadu", 70),
    ("SITE011", "Union Bank", "Karnataka", 18),
    ("SITE012", "Dena Bank", "Gujarat", 5),
    ("SITE013", "Andhra Bank", "Telangana", 55),
    ("SITE014", "Bank of Baroda", "Maharashtra", 12),
    ("SITE015", "Central Bank", "Punjab", 38),
]

def seed_engineers(conn):
    """Seed engineer data"""
    cursor = conn.cursor()
    for code, name, state in ENGINEERS:
        cursor.execute("""
            INSERT OR IGNORE INTO engineer_master 
            (engineer_code, engineer_name, state, designation, active_status, phone, email, service_area_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code, name, state, "Engineer", "YES",
            f"98765{int(code):04d}", f"eng{code}@vprotect.com", f"SA{code}"
        ))
    conn.commit()
    print(f"✅ Seeded {len(ENGINEERS)} engineers")

def seed_offline_sites(conn):
    """Seed offline sites data"""
    cursor = conn.cursor()
    for site_id, name, state, days in SITES:
        # Calculate priority based on days offline
        if days > 60:
            priority = "CRITICAL"
        elif days > 30:
            priority = "HIGH"
        elif days > 15:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        
        cursor.execute("""
            INSERT OR IGNORE INTO offline_data_master
            (site_id, site_name, state, segment, last_online_date, offline_duration_days, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            site_id, name, state, "PSU",
            (datetime.now() - timedelta(days=days)).date(),
            days, priority
        ))
    conn.commit()
    print(f"✅ Seeded {len(SITES)} offline sites")

def seed_attendance(conn):
    """Seed attendance data"""
    cursor = conn.cursor()
    count = 0
    for eng_code, _, _ in ENGINEERS:
        for day_offset in range(0, 30):
            date = (datetime.now() - timedelta(days=day_offset)).date()
            status = random.choice(["OnTime", "Late", "Absent"])
            check_in = None
            
            if status == "OnTime":
                check_in = datetime.combine(date, datetime.min.time()).replace(hour=random.randint(6, 9), minute=random.randint(0, 59))
            elif status == "Late":
                check_in = datetime.combine(date, datetime.min.time()).replace(hour=random.randint(10, 12), minute=random.randint(0, 59))
            
            check_out = None
            if check_in:
                check_out = check_in.replace(hour=random.randint(17, 18), minute=random.randint(0, 59))
            
            cursor.execute("""
                INSERT INTO attendance_data
                (engineer_code, attendance_date, check_in_time, check_out_time, status)
                VALUES (?, ?, ?, ?, ?)
            """, (eng_code, date, check_in, check_out, status))
            count += 1
    
    conn.commit()
    print(f"✅ Seeded {count} attendance records")

def seed_visits(conn):
    """Seed visit data"""
    cursor = conn.cursor()
    count = 0
    for _ in range(500):
        eng_code = random.choice(ENGINEERS)[0]
        site_id = random.choice(SITES)[0]
        visit_date = (datetime.now() - timedelta(days=random.randint(0, 90))).date()
        visit_type = random.choice(["Installation", "Maintenance", "Support", "Inspection"])
        problem_solved = random.choice([True, False])
        time_taken = random.randint(30, 240)
        
        cursor.execute("""
            INSERT INTO visit_master
            (engineer_code, site_id, visit_date, visit_type, problem_solved, time_taken_minutes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (eng_code, site_id, visit_date, visit_type, problem_solved, time_taken))
        count += 1
    
    conn.commit()
    print(f"✅ Seeded {count} visit records")

def seed_tickets(conn):
    """Seed ticket data"""
    cursor = conn.cursor()
    count = 0
    for i in range(300):
        ticket_id = f"TKT{i+1:06d}"
        site_id = random.choice(SITES)[0]
        eng_code = random.choice(ENGINEERS)[0]
        status = random.choice(["Open", "In Progress", "Closed", "Pending"])
        priority = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        category = random.choice(["Hardware", "Software", "Network", "Maintenance", "Other"])
        
        created_date = (datetime.now() - timedelta(days=random.randint(0, 120))).date()
        closed_date = None
        if status == "Closed":
            closed_date = (datetime.fromisoformat(str(created_date)) + timedelta(days=random.randint(1, 30))).date()
        
        cursor.execute("""
            INSERT INTO view_ticket
            (ticket_id, site_id, engineer_code, ticket_status, created_date, closed_date, priority, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, site_id, eng_code, status, created_date, closed_date, priority, category))
        count += 1
    
    conn.commit()
    print(f"✅ Seeded {count} ticket records")

def main():
    """Run all seeding operations"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("Run the backend first to initialize the database.")
        return
    
    print("🌱 Starting database seeding...")
    conn = sqlite3.connect(DB_PATH)
    
    try:
        seed_engineers(conn)
        seed_offline_sites(conn)
        seed_attendance(conn)
        seed_visits(conn)
        seed_tickets(conn)
        print("\n✅ Database seeding complete!")
        
        # Show summary
        cursor = conn.cursor()
        tables = ["engineer_master", "offline_data_master", "attendance_data", "visit_master", "view_ticket"]
        print("\nDatabase Summary:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
