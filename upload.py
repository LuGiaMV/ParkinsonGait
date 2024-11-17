import os
import subprocess
import time

def guardar(repo_path, output_folder, baseFileName_arduino, fileName_gps, fileName_kml):
    
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

if __name__ == "__main__":
    guardar()