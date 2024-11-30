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

# Tamaño máximo del bloque de datos en bytes y contadores de archivos
block_size = 20480
file_count = 1

kml = Kml()
linea = kml.newlinestring(name="Ruta GPS")

repo_path = "/home/user/Desktop/ParkinsonGait"          # Cambia esta ruta por el repositorio clonado localmente
subfolder_name = time.strftime("data/Marcha %Y-%m-%d")                      # Carpeta con la fecha actual
output_folder = os.path.join(repo_path, subfolder_name)
# Nombre base de los archivos y encabezados de columnas
baseFileName_arduino = os.path.join(output_folder, time.strftime("%Y-%m-%d_%H-%M-%S_arduino"))
fileName_gps = os.path.join(output_folder, time.strftime("%Y-%m-%d_%H-%M-%S_gps.csv"))
fileName_kml = os.path.join(output_folder, time.strftime("%Y-%m-%d_%H-%M-%S.kml"))
labels_arduino = ["Timestamp", "xAcel_L", "yAcel_L", "zAcel_L", "xGyro_L", "yGyro_L", "zGyro_L",
                  "xMag_L", "yMag_L", "zMag_L", "xAcel_R", "yAcel_R", "zAcel_R",
                  "xGyro_R", "yGyro_R", "zGyro_R", "xMag_R", "yMag_R", "zMag_R"]
labels_gps = ["Timestamp", "Time", "latitude", "longitude", "fix_status"]
coords = []

# Función para insertar datos en la base de datos
def save_to_db(session, data, model):
    try:
        session.add(data)
        session.commit()
        print(f"Datos guardados en {model.__tablename__}: {data}")
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

def save_kml(coords):
    linea.coords = coords
    kml.save(f"{fileName_kml}")
    linea.style.linestyle.color = '219de2'
    linea.style.linestyle.width = 5
    print(f"Archivo KML guardado como {fileName_kml}.KML") 

def push_Git():
    
    # Mover los archivos generados al repositorio
    try:
        os.chdir(repo_path)
        # Ejecutar comandos de Git para agregar, confirmar y enviar los cambios
        subprocess.run(["git", "add", "."], check=True)
        commit_message = f"Datos generados el {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)  # Cambia "main" por tu rama principal si es diferente
        print("Archivos subidos exitosamente a GitHub.")
    except Exception as e:
        print(f"Error al subir los archivos a GitHub: {e}")
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

# # Búsqueda de un nombre de archivo único para Arduino y GPS
# while os.path.exists(f"{baseFileName_arduino}_{file_count}.csv"):
#     file_count_arduino += 1
# while os.path.exists(f"{baseFileName_gps}_{file_count}.csv"):
#     file_count += 1

# Crear la carpeta dentro del repositorio local
if not os.path.exists(subfolder_name):
    os.makedirs(subfolder_name)

try:
    session = Session()
    with open(fileName_gps, 'w', newline='') as csvfile_gps:
        gps_writer = csv.writer(csvfile_gps, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        gps_writer.writerow(labels_gps)
        print(f"Encabezados GPS: {labels_gps}")
        while True:

            fileName_arduino = f"{baseFileName_arduino}_{file_count}.csv"
            with open(fileName_arduino, 'w', newline='') as csvfile_arduino:
                arduino_writer = csv.writer(csvfile_arduino, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                arduino_writer.writerow(labels_arduino)
                print(f"Encabezados Arduino: {labels_arduino}")

                while os.path.getsize(fileName_arduino) < block_size:
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
                            save_to_db(session, arduino_data, ArduinoData)
                            arduino_writer.writerow(data_parts)                                                    # Escribir en el archivo CSV
                            csvfile_arduino.flush()                                                                     # Forzar la escritura en disco
                            print(f"Datos Arduino recibidos: {data_parts}")

                    # Leer varias líneas del GPS para obtener datos completos
                    if time.time() - current_time > time_interval:                                                      # Leer cada 1 segundos
                        current_time = time.time()                                                                      # Actualizar el tiempo actual
                        while ser_gps.in_waiting > 0:                                                                   # Leer todas las líneas disponibles
                            gps_linea = ser_gps.readline().decode("utf-8").strip()
                            if gps_linea.startswith("$GPGGA"):                                                          # Procesar $GPGGA para obtener latitud y longitud
                                gps_parts = gps_linea.split(",")
                                if gps_parts[6] == "1":
                                    tiempo = gps_parts[1] if gps_parts[1] else ""                             # Hora en formato HHMMSS

                                    latitude = convertir_grados_decimales(gps_parts[2], gps_parts[3])     # Convertir de grado-minuto a decimal
                                    longitude = convertir_grados_decimales(gps_parts[4], gps_parts[5])    # Convertir de grado-minuto a decimal
                                    coords.append((gps_data["long_format"], gps_data["lat_format"]))                    # Guardar coordenadas para KML

                                    # Crear entrada para el archivo GPS solo con los datos relevantes
                                    timestamp_gps = time.strftime("%Y-%m-%d %H:%M:%S")                                  # Marca de tiempo actual
                                    lectura_gps = [timestamp_gps, tiempo, latitude, longitude, "Valid fix"]    # Datos relevantes
                                    gps_data = GPSData(
                                        timestamp=timestamp_gps,
                                        time=tiempo,
                                        latitude=float(latitude),
                                        longitude=float(longitude),
                                        fix_status="Valid fix"
                                    )
                                    save_to_db(session, gps_data, GPSData)
                                    gps_writer.writerow(lectura_gps)                                                    # Escribir en el archivo CSV
                                    csvfile_gps.flush()                                                                 # Forzar la escritura en disco
                                    print(f"Datos GPS recibidos: {lectura_gps}")                                        # Mostrar en consola
                                else:
                                    print("No hay señal GPS")
                                ser_gps.reset_input_buffer()                                                            # Limpiar el buffer de entrada
                                break
                    time.sleep(0.1)  # Esperar un poco antes de la siguiente lectura
                print("Tamaño maximo alcanzado. Escribiendo en disco...")
                csvfile_arduino.flush()             # forzar la escritura en disco
                csvfile_gps.flush()                 # forzar la escritura en disco
                file_count += 1

except KeyboardInterrupt:
    print("Interrupción del usuario. Cerrando conexiones...")

except Exception as e:
    print(f"Error: {e}")

finally:
    if coords:
        save_kml(coords)
    else:
        os.remove(fileName_gps)
    input("Presiona Enter para subir los archivos a GitHub...")
    push_Git()
    ser_arduino.close()
    ser_gps.close()
    exit()
