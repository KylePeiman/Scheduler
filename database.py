import os
import ssl
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Read DATABASE_URL from production location first (/tmp/replitdb), then environment variable
# Published apps store DATABASE_URL in /tmp/replitdb instead of environment variables
DATABASE_URL = None
db_url_source = "unknown"

# Try reading from /tmp/replitdb first (production deployments)
if os.path.exists('/tmp/replitdb'):
    try:
        with open('/tmp/replitdb', 'r') as f:
            content = f.read().strip()
            # Only use if it's a valid PostgreSQL URL
            if content.startswith('postgresql://') or content.startswith('postgres://'):
                DATABASE_URL = content
                db_url_source = "/tmp/replitdb"
    except Exception as e:
        print(f"[DB] Warning: Could not read /tmp/replitdb: {e}")

# Fall back to environment variable (development)
if not DATABASE_URL:
    DATABASE_URL = os.getenv('DATABASE_URL')
    db_url_source = "environment variable"

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not found. "
        "Please ensure PostgreSQL database is configured. "
        "Run: create_postgresql_database_tool to set up the database."
    )

import sys
import logging

# Configure logging to output to stdout (visible in production logs)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='[DATABASE] %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"DATABASE_URL source: {db_url_source}")

# Configure for Neon PostgreSQL (Replit's managed database)
# Use pooled connection for serverless/Replit environments
import re

# Log original URL (sanitized)
original_sanitized = re.sub(r':([^:@]+)@', ':***@', DATABASE_URL)
logger.info(f"Original URL: {original_sanitized}")

if 'neon.tech' in DATABASE_URL and '-pooler' not in DATABASE_URL:
    # Insert -pooler before the region (e.g., ep-xxx-pooler.region.aws.neon.tech)
    DATABASE_URL = re.sub(r'(ep-[^.]+)', r'\1-pooler', DATABASE_URL)
    logger.info("✓ Converted to pooled connection endpoint")
else:
    logger.info("URL already has -pooler or is not Neon")

# Add connection timeout if not present (critical for Neon cold starts)
if 'connect_timeout' not in DATABASE_URL:
    separator = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL += f'{separator}connect_timeout=15'
    logger.info("✓ Added connect_timeout=15")
else:
    logger.info("URL already has connect_timeout")

# Ensure SSL mode is set
if 'sslmode' not in DATABASE_URL:
    separator = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL += f'{separator}sslmode=require'
    logger.info("✓ Set sslmode=require")
else:
    logger.info("URL already has sslmode")

# Log final sanitized connection info (hide password)
final_sanitized = re.sub(r':([^:@]+)@', ':***@', DATABASE_URL)
logger.info(f"Final URL: {final_sanitized}")

# Create engine with AGGRESSIVE settings for Neon's serverless architecture
# Neon auto-suspends after 5 minutes, so we need to avoid stale connections
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,           # CRITICAL: Test connections before use
    pool_recycle=60,              # Recycle connections every 60 seconds (AGGRESSIVE)
    pool_size=2,                  # Small pool to minimize stale connections
    max_overflow=8,               # Allow overflow for traffic spikes
    pool_timeout=20,              # Timeout for getting connection from pool
    pool_reset_on_return='rollback',  # Reset connections when returned to pool
    echo=False
)
logger.info("✓ Engine created with aggressive pool settings for Neon")
logger.info("Pool config: size=2, recycle=60s, pre_ping=True")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Provider(Base):
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    provider_type = Column(String, default='MD')
    credentials = Column(JSON, default=[])
    preferred_sites = Column(JSON, default=[])
    avoided_sites = Column(JSON, default=[])
    target_hours = Column(Float, default=40.0)
    pto_dates = Column(JSON, default=[])
    commute_distances = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    assignments = relationship("Assignment", back_populates="provider_rel")

class Shift(Base):
    __tablename__ = 'shifts'
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    site = Column(String, nullable=False)
    shift_type = Column(String, nullable=False)
    required_credentials = Column(JSON, default=[])
    hours = Column(Float, nullable=False)
    is_weekend = Column(Boolean, default=False)
    is_holiday = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    locked_provider_id = Column(Integer, ForeignKey('providers.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assignments = relationship("Assignment", back_populates="shift_rel")
    locked_provider = relationship("Provider", foreign_keys=[locked_provider_id])

class Schedule(Base):
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    status = Column(String, default='draft')
    optimization_score = Column(Float, nullable=True)
    fairness_weight = Column(Float, default=5.0)
    preference_weight = Column(Float, default=3.0)
    max_hours_per_week = Column(Float, default=60.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    assignments = relationship("Assignment", back_populates="schedule_rel", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = 'assignments'
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id'), nullable=False)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)
    provider_id = Column(Integer, ForeignKey('providers.id'), nullable=True)
    is_unfilled = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    is_manual = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    schedule_rel = relationship("Schedule", back_populates="assignments")
    shift_rel = relationship("Shift", back_populates="assignments")
    provider_rel = relationship("Provider", back_populates="assignments")

class CallOut(Base):
    __tablename__ = 'callouts'
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id'), nullable=False)
    assignment_id = Column(Integer, ForeignKey('assignments.id'), nullable=False)
    provider_id = Column(Integer, ForeignKey('providers.id'), nullable=False)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)
    reason = Column(Text, nullable=True)
    replacement_provider_id = Column(Integer, ForeignKey('providers.id'), nullable=True)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    return SessionLocal()
