from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "mysql+pymysql://root:12345@localhost/RFP_Creation_Project"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class ProjectCredential(Base):
    __tablename__ = "project_credentials"

    id = Column(String(50), primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False)
    estimated_amount = Column(Float, nullable=False)
    business_justification = Column(String(1000), nullable=False)
    submitted_by = Column(String(255), nullable=False)

    technical_specification = Column(String(1000), nullable=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
