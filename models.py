from sqlalchemy import create_engine, Column, String, Float, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TIMESTAMP

Base = declarative_base()

class ArduinoData(Base):
    __tablename__ = 'arduino_data'
    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(precision=3))  # Precisión de milisegundos
    x_acel_l = Column(Float)
    y_acel_l = Column(Float)
    z_acel_l = Column(Float)
    x_gyro_l = Column(Float)
    y_gyro_l = Column(Float)
    z_gyro_l = Column(Float)
    x_mag_l = Column(Float)
    y_mag_l = Column(Float)
    z_mag_l = Column(Float)
    x_acel_r = Column(Float)
    y_acel_r = Column(Float)
    z_acel_r = Column(Float)
    x_gyro_r = Column(Float)
    y_gyro_r = Column(Float)
    z_gyro_r = Column(Float)
    x_mag_r = Column(Float)
    y_mag_r = Column(Float)
    z_mag_r = Column(Float)

class GPSData(Base):
    __tablename__ = 'gps_data'
    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(precision=3))  # Precisión de milisegundos
    time = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    fix_status = Column(String)
