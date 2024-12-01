import csv
import os
import time
from simplekml import Kml
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import ArduinoData, GPSData

# Configuración de la base de datos PostgreSQL
DATABASE_URL = "postgresql+psycopg2://postgres:ruyeJZhoonKcduSYQZidpOPxXWsDAZUg@junction.proxy.rlwy.net:51508/railway"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Ruta del repositorio y nombres de archivos
repo_path = "/home/user/Desktop/ParkinsonGait"  # Cambia con la ruta local del repositorio
subfolder_name = time.strftime("data/Marcha %Y-%m-%d")
output_folder = os.path.join(repo_path, subfolder_name)

baseFileName_arduino = os.path.join(output_folder, time.strftime("%Y-%m-%d_%H-%M-%S_arduino"))
fileName_gps = os.path.join(output_folder, time.strftime("%Y-%m-%d_%H-%M-%S_gps.csv"))
fileName_kml = os.path.join(output_folder, time.strftime("%Y-%m-%d_%H-%M-%S.kml"))

# Función para exportar ArduinoData a CSV
def export_arduino_to_csv(session, output_path):
    data = session.query(ArduinoData).all()
    columns = [column.name for column in ArduinoData.__table__.columns]
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        for row in data:
            writer.writerow([getattr(row, col) for col in columns])
    print(f"Datos de Arduino exportados a {output_path}")

# Función para exportar GPSData a CSV
def export_gps_to_csv(session, output_path):
    data = session.query(GPSData).all()
    columns = [column.name for column in GPSData.__table__.columns]
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        for row in data:
            writer.writerow([getattr(row, col) for col in columns])
    print(f"Datos GPS exportados a {output_path}")

# Función para exportar GPSData a KML
def export_gps_to_kml(session, output_path):
    data = session.query(GPSData).all()
    kml = Kml()
    linea = kml.newlinestring(name="Ruta GPS")
    coords = [(row.longitude, row.latitude) for row in data if row.latitude and row.longitude]
    linea.coords = coords
    linea.style.linestyle.color = '219de2'  # Azul
    linea.style.linestyle.width = 5
    kml.save(output_path)
    print(f"Archivo KML guardado como {output_path}")

# Subir los archivos al repositorio de Git
def push_files_to_git(repo_path, files):
    import subprocess
    try:
        # Cambiar al directorio del repositorio
        subprocess.run(["git", "-C", repo_path, "add"] + files, check=True)
        commit_message = "Exportación automática de datos a CSV y KML"
        subprocess.run(["git", "-C", repo_path, "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "-C", repo_path, "push"], check=True)
        print("Archivos subidos exitosamente a GitHub.")
    except Exception as e:
        print(f"Error al subir los archivos a Git: {e}")

# Flujo principal
if __name__ == "__main__":
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    session = Session()
    try:
        # Exportar datos a CSV
        export_arduino_to_csv(session, f"{baseFileName_arduino}.csv")
        export_gps_to_csv(session, fileName_gps)
        # Exportar datos a KML
        export_gps_to_kml(session, fileName_kml)
        # Subir archivos al repositorio
        push_files_to_git(repo_path, [f"{baseFileName_arduino}.csv", fileName_gps, fileName_kml])
    finally:
        session.close()
