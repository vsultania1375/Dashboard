"""
Database configuration and models for VProtect Dashboard
Uses SQLite for development/testing
Can be switched to PostgreSQL by changing DATABASE_URL
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vprotect_dashboard.db")

# SQLite specific: Use StaticPool and check_same_thread=False for testing
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ─── DATABASE MODELS ───────────────────────────────────
class Engineer(Base):
    __tablename__ = "engineer_master"
    
    id = Column(Integer, primary_key=True, index=True)
    engineer_code = Column(String(3), unique=True, index=True, nullable=False)  # 3-digit code
    engineer_name = Column(String(255), nullable=False)
    state = Column(String(50), nullable=False, index=True)
    designation = Column(String(50), nullable=False)
    active_status = Column(String(3), nullable=False)  # YES/NO
    phone = Column(String(20))
    email = Column(String(100))
    service_area_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OfflineSite(Base):
    __tablename__ = "offline_data_master"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(String(50), unique=True, index=True, nullable=False)
    site_name = Column(String(255), nullable=False)
    state = Column(String(50), nullable=False, index=True)
    segment = Column(String(20), nullable=False)  # PSU
    last_online_date = Column(DateTime, nullable=False)
    offline_duration_days = Column(Integer, nullable=False)
    priority = Column(String(20), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Attendance(Base):
    __tablename__ = "attendance_data"
    
    id = Column(Integer, primary_key=True, index=True)
    engineer_code = Column(String(3), ForeignKey("engineer_master.engineer_code"), nullable=False)
    attendance_date = Column(DateTime, nullable=False, index=True)
    check_in_time = Column(String(20))
    check_out_time = Column(String(20))
    status = Column(String(20), nullable=False)  # OnTime, Late, Absent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (Index("idx_engineer_date", "engineer_code", "attendance_date"),)


class Visit(Base):
    __tablename__ = "visit_master"
    
    id = Column(Integer, primary_key=True, index=True)
    engineer_code = Column(String(3), ForeignKey("engineer_master.engineer_code"), nullable=False)
    site_id = Column(String(50), ForeignKey("offline_data_master.site_id"), nullable=False)
    visit_date = Column(DateTime, nullable=False, index=True)
    visit_type = Column(String(50), nullable=False)
    problem_solved = Column(String(3), nullable=False)  # YES/NO
    problem_description = Column(Text)
    time_taken_minutes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Ticket(Base):
    __tablename__ = "view_ticket"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=False)
    site_id = Column(String(50), ForeignKey("offline_data_master.site_id"), nullable=False)
    engineer_code = Column(String(3), ForeignKey("engineer_master.engineer_code"))
    ticket_status = Column(String(20), nullable=False)  # OPEN, PENDING, etc.
    created_date = Column(DateTime, nullable=False, index=True)
    closed_date = Column(DateTime)
    priority = Column(String(5), nullable=False)  # P1, P2, P3, P4
    category = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UploadLog(Base):
    __tablename__ = "upload_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String(50), unique=True, nullable=False)
    filename = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)
    rows_uploaded = Column(Integer, nullable=False)
    rows_valid = Column(Integer, nullable=False)
    rows_invalid = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # success, error, loading
    errors = Column(Text)  # JSON string of errors
    warnings = Column(Text)  # JSON string of warnings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── DATABASE INITIALIZATION ───────────────────────────
def init_db():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── DATABASE OPERATIONS ───────────────────────────────
class DatabaseOps:
    """Database operations helper class"""
    
    @staticmethod
    def insert_engineers(db: Session, engineers: list):
        """Insert multiple engineers"""
        try:
            for eng in engineers:
                existing = db.query(Engineer).filter(
                    Engineer.engineer_code == eng['engineer_code']
                ).first()
                
                if existing:
                    # Update existing
                    for key, value in eng.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new
                    db.add(Engineer(**eng))
            
            db.commit()
            return len(engineers), 0
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def insert_offline_sites(db: Session, sites: list):
        """Insert multiple offline sites"""
        try:
            for site in sites:
                existing = db.query(OfflineSite).filter(
                    OfflineSite.site_id == site['site_id']
                ).first()
                
                if existing:
                    for key, value in site.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    db.add(OfflineSite(**site))
            
            db.commit()
            return len(sites), 0
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def insert_attendance(db: Session, records: list):
        """Insert attendance records"""
        try:
            for record in records:
                db.add(Attendance(**record))
            
            db.commit()
            return len(records), 0
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def insert_visits(db: Session, visits: list):
        """Insert visit records"""
        try:
            for visit in visits:
                db.add(Visit(**visit))
            
            db.commit()
            return len(visits), 0
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def insert_tickets(db: Session, tickets: list):
        """Insert ticket records"""
        try:
            for ticket in tickets:
                existing = db.query(Ticket).filter(
                    Ticket.ticket_id == ticket['ticket_id']
                ).first()
                
                if existing:
                    for key, value in ticket.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    db.add(Ticket(**ticket))
            
            db.commit()
            return len(tickets), 0
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def get_engineers(db: Session, state: str = None, limit: int = 100, offset: int = 0):
        """Get engineers with optional state filter"""
        query = db.query(Engineer).filter(Engineer.active_status == "YES")
        
        if state and state != "All (PAN India)":
            query = query.filter(Engineer.state == state)
        
        total = query.count()
        records = query.limit(limit).offset(offset).all()
        
        return {"total": total, "engineers": records}
    
    @staticmethod
    def get_offline_sites(db: Session, priority: str = None, state: str = None):
        """Get offline sites with optional filters"""
        query = db.query(OfflineSite)
        
        if priority:
            query = query.filter(OfflineSite.priority == priority)
        
        if state and state != "All (PAN India)":
            query = query.filter(OfflineSite.state == state)
        
        return query.all()
