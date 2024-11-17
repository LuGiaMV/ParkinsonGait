import serial
import time
import csv
import os
from simplekml import Kml
from upload import guardar

# Configuración de puertos y tasas de baudios
gps_port = "/dev/ttyACM0"  # Puerto serial del GPS
arduino_port = "/dev/ttyACM1"  # Puerto serial del Arduino
baud_rate_gps = 4800
baud_rate_arduino = 9600

time_interval = 5
current_time = 0

# Tamaño máximo del bloque de datos en bytes y contadores de archivos
block_size = 20480
file_count = 1

kml = Kml()
linea = kml.newlinestring(name="Ruta GPS")

repo_path = "/home/user/Desktop/ParkinsonGait"          # Cambia esta ruta por el repositorio clonado localmente
subfolder_name = time.strftime("Marcha %Y-%m-%d")                      # Carpeta con la fecha actual
# Nombre base de los archivos y encabezados de columnas
baseFileName_arduino = time.strftime("%Y-%m-%d_%H-%M-%S_arduino")
fileName_gps = time.strftime("%Y-%m-%d_%H-%M-%S_gps.csv")
fileName_kml = time.strftime("%Y-%m-%d_%H-%M-%S.kml")
labels_arduino = ["Timestamp", "xAcel_L", "yAcel_L", "zAcel_L", "xGyro_L", "yGyro_L", "zGyro_L",
                  "xMag_L", "yMag_L", "zMag_L", "xAcel_R", "yAcel_R", "zAcel_R",
                  "xGyro_R", "yGyro_R", "zGyro_R", "xMag_R", "yMag_R", "zMag_R"]
labels_gps = ["Timestamp", "Time", "latitude", "longitude", "fix_status"]
coords = []

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

try:
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
                            lectura_arduino = [timestamp] + linea_arduino.split(",")
                            arduino_writer.writerow(lectura_arduino)                                                    # Escribir en el archivo CSV
                            csvfile_arduino.flush()                                                                     # Forzar la escritura en disco
                            print(f"Datos Arduino recibidos: {lectura_arduino}")

                    # Leer varias líneas del GPS para obtener datos completos
                    if time.time() - current_time > time_interval:                                                      # Leer cada 5 segundos
                        current_time = time.time()                                                                      # Actualizar el tiempo actual
                        while ser_gps.in_waiting > 0:                                                                   # Leer todas las líneas disponibles
                            gps_linea = ser_gps.readline().decode("utf-8").strip()
                            if gps_linea.startswith("$GPGGA"):                                                          # Procesar $GPGGA para obtener latitud y longitud
                                gps_parts = gps_linea.split(",")
                                if gps_parts[6] == "1":
                                    gps_data["Time"] = gps_parts[1] if gps_parts[1] else ""                             # Hora en formato HHMMSS
                                    gps_data["fix_status"] = "Valid fix" if gps_parts[6] == "1" else "No fix"           # Estado de la señal GPS

                                    gps_data["lat_format"] = convertir_grados_decimales(gps_parts[2], gps_parts[3])     # Convertir de grado-minuto a decimal
                                    gps_data["long_format"] = convertir_grados_decimales(gps_parts[4], gps_parts[5])    # Convertir de grado-minuto a decimal
                                    coords.append((gps_data["long_format"], gps_data["lat_format"]))                    # Guardar coordenadas para KML

                                    # Crear entrada para el archivo GPS solo con los datos relevantes
                                    timestamp_gps = time.strftime("%Y-%m-%d %H:%M:%S")                                  # Marca de tiempo actual
                                    lectura_gps = [timestamp_gps, gps_data["Time"], gps_data["lat_format"], gps_data["long_format"], gps_data["fix_status"]]    # Datos relevantes

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
    # Ruta del repositorio local donde se almacenarán los archivos
    output_folder = os.path.join(repo_path, subfolder_name)
    if coords:
        save_kml(coords)
    else:
        os.remove(fileName_gps)
    guardar(repo_path, output_folder, baseFileName_arduino, fileName_gps, fileName_kml)
    ser_arduino.close()
    ser_gps.close()
    exit()
