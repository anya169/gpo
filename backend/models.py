from sqlalchemy import Column, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "User"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    
class Session(Base):
    __tablename__ = "Session"
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("User.user_id"), nullable=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    avg_concentration = Column(Float) 
    focus_dips_count = Column(Integer)
    baseline_concentration = Column(Float)
    is_active = Column(Boolean, default=True)

    user = relationship("User", backref="sessions") 

class Concentration(Base):
    __tablename__ = "Concentration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("Session.session_id"), nullable=False)
    time = Column(DateTime, default=func.now())
    value = Column(Float)
    is_calibration = Column(Boolean, default=False)

    session = relationship("Session", backref="concentrations")

class Exercise(Base):
    __tablename__ = "Exercise"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("Session.session_id"), nullable=False)
    exercise_type = Column(Text)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    completed = Column(Boolean, default=False)
    concentration_before = Column(Float)
    concentration_after = Column(Float)

    session = relationship("Session", backref="exercises")

class AuthCode(Base):
    __tablename__ = "AuthCode"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_used = Column(Boolean, default=False)