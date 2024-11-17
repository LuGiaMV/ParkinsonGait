import os
import subprocess
import time

def guardar(repo_path, output_folder, baseFileName_arduino, fileName_gps, fileName_kml):

    # Crear la carpeta dentro del repositorio local
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Mover los archivos generados al repositorio
    try:
        # Mover archivos Arduino
        for file in os.listdir("."):
            if file.startswith(baseFileName_arduino) or file == fileName_gps or file == fileName_kml:
                os.rename(file, os.path.join(output_folder, file))
                print(f"Archivo {file} movido a {output_folder}")

        # Cambiar al directorio del repositorio
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