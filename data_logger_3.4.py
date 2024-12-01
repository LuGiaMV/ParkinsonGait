from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, ArduinoData, GPSData
import serial
import time
import csv
import os
import subprocess
from simplekml import Kml

# Configuración de la base de datos PostgreSQL
DATABASE_URL = "postgresql+psycopg2://postgres:ruyeJZhoonKcduSYQZidpOPxXWsDAZUg@junction.proxy.rlwy.net:51508/railway"  # Cambia con tus credenciales Railway
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Crear tablas si no existen
Base.metadata.create_all(engine)
# Configuración de puertos y tasas de baudios
arduino_port = "/dev/ttyACM0"  # Puerto serial del Arduino
gps_port = "/dev/ttyACM1"  # Puerto serial del GPS
baud_rate_gps = 4800
baud_rate_arduino = 9600

time_interval = 1
current_time = 0

kml = Kml()
linea = kml.newlinestring(name="Ruta GPS")

repo_path = "/home/user/Desktop/ParkinsonGait"          # Cambia esta ruta por el repositorio clonado localmente
subfolder_name = time.strftime("data/Marcha %Y-%m-%d")                      # Carpeta con la fecha actual
arduino_database = []
gps_database = []

# Función para insertar datos en la base de datos
def save_to_db(session, data, model):
    try:
        for item in data:
            session.add(item)
            session.commit()
            print(f"Datos guardados en {model.__tablename__}: {item}")
    except Exception as e:
        session.rollback()
        print(f"Error al guardar datos en {model.__tablename__}: {e}")

def convertir_grados_decimales(coord, direccion):
    # Separar grados y minutos
    if len(coord) == 11:  # Longitud (DDDMM.MMMM)
        grados = int(coord[:3])
        minutos = float(coord[3:])
    else:  # Latitud (DDMM.MMMM)
        grados = int(coord[:2])
        minutos = float(coord[2:])
    
    # Convertir a grados decimales
    decimal = grados + (minutos / 60)
    
    # Aplicar el signo negativo si es Sur o Oeste
    if direccion in ['S', 'W']:
        decimal = -decimal
        
    return decimal

# Conectar al Arduino
try:
    ser_arduino = serial.Serial(arduino_port, baud_rate_arduino, timeout=1)
    print(f"Conectado a {arduino_port}")
except serial.SerialException:
    print(f"No se puede conectar al puerto {arduino_port}")
    exit()

# Conectar al GPS
try:
    ser_gps = serial.Serial(gps_port, baud_rate_gps, timeout=1)
    print(f"Conectado a {gps_port}")
except serial.SerialException:
    print(f"No se puede conectar al puerto {gps_port}")
    exit()

# Inicialización de variables para almacenar datos GPS
gps_data = {"Time": "", "lat_format": "", "long_format": "", "fix_status": ""}

try:
    session = Session()
    while True:
        # Leer datos de Arduino y escribir en archivo correspondiente
        if ser_arduino.in_waiting > 0:
            linea_arduino = ser_arduino.readline().decode("utf-8").strip()
            if linea_arduino:
                # Obtener la marca de tiempo y datos de Arduino
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
                data_parts = linea_arduino.split(",")
                arduino_data = ArduinoData(
                    timestamp=timestamp,
                    x_acel_l=float(data_parts[0]),
                    y_acel_l=float(data_parts[1]),
                    z_acel_l=float(data_parts[2]),
                    x_gyro_l=float(data_parts[3]),
                    y_gyro_l=float(data_parts[4]),
                    z_gyro_l=float(data_parts[5]),
                    x_mag_l=float(data_parts[6]),
                    y_mag_l=float(data_parts[7]),
                    z_mag_l=float(data_parts[8]),
                    x_acel_r=float(data_parts[9]),
                    y_acel_r=float(data_parts[10]),
                    z_acel_r=float(data_parts[11]),
                    x_gyro_r=float(data_parts[12]),
                    y_gyro_r=float(data_parts[13]),
                    z_gyro_r=float(data_parts[14]),
                    x_mag_r=float(data_parts[15]),
                    y_mag_r=float(data_parts[16]),
                    z_mag_r=float(data_parts[17]),
                )
                arduino_database.append(arduino_data)                                                                 # Forzar la escritura en disco
                print(f"Datos Arduino recibidos: {data_parts}")

        # Leer varias líneas del GPS para obtener datos completos
        if time.time() - current_time > time_interval:                                                      # Leer cada 1 segundos
            current_time = time.time()                                                                      # Actualizar el tiempo actual
            while ser_gps.in_waiting > 0:                                                                   # Leer todas las líneas disponibles
                gps_linea = ser_gps.readline().decode("utf-8").strip()
                if gps_linea.startswith("$GPGGA"):                                                          # Procesar $GPGGA para obtener latitud y longitud
                    gps_parts = gps_linea.split(",")
                    print("fix_status: " + gps_parts[6])
                    if gps_parts[6] == "1":
                        tiempo = gps_parts[1]                            # Hora en formato HHMMSS
                        latitude = convertir_grados_decimales(gps_parts[2], gps_parts[3])     # Convertir de grado-minuto a decimal
                        longitude = convertir_grados_decimales(gps_parts[4], gps_parts[5])    # Convertir de grado-minuto a decimal

                        # Crear entrada para el archivo GPS solo con los datos relevantes
                        timestamp_gps = time.strftime("%Y-%m-%d %H:%M:%S")                                  # Marca de tiempo actual
                        lectura_gps = [timestamp_gps, tiempo, latitude, longitude, "Valid fix"]    # Datos relevantes
                        gps_data = GPSData(
                            timestamp=timestamp_gps,
                            time=tiempo,
                            latitude=latitude,
                            longitude=longitude,
                            fix_status="Valid fix"
                        )
                        arduino_database.append(gps_data)                                                            # Forzar la escritura en disco
                        print(f"Datos GPS recibidos: {lectura_gps}")                                        # Mostrar en consola
                    else:
                        print("No hay señal GPS")
                    ser_gps.reset_input_buffer()                                                            # Limpiar el buffer de entrada
                    break
        time.sleep(0.1)  # Esperar un poco antes de la siguiente lectura

except KeyboardInterrupt:
    print("Interrupción del usuario. Cerrando conexiones...")

except Exception as e:
    print(f"Error: {e}")

finally:
    input("Presiona Enter para subir los archivos...")
    save_to_db(session, arduino_database, ArduinoData)
    save_to_db(session, gps_database, GPSData)
#     push_Git()
    ser_arduino.close()
    ser_gps.close()
    exit()
