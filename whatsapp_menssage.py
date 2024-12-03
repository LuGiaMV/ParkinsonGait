import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import webbrowser
import pywhatkit as kit

# Conexión a la base de datos PostgreSQL
DATABASE_URL = "postgresql+psycopg2://postgres:ruyeJZhoonKcduSYQZidpOPxXWsDAZUg@junction.proxy.rlwy.net:51508/railway"
engine = create_engine(DATABASE_URL)
"""
def send_whatsapp_message(phone_number, message):
        base_url = "https://api.whatsapp.com/send/"
        url = f"{base_url}?phone={phone_number}&text={message}"
        webbrowser.open(url)
"""

def send_whatsapp_message(phone_number, message):
    # Parámetros: número (incluido el '+'), mensaje, hora de envío (HH, MM)
    kit.sendwhatmsg(phone_number, message, 15, 30)  # Enviará el mensaje a las 15:30

def send_whatsapp_message_now(phone_number, message):
    # Obtiene la hora actual
    now = datetime.now()
    hour = now.hour
    minute = now.minute + 1  # Programar para el minuto siguiente

    # Enviar el mensaje
    kit.sendwhatmsg(phone_number, message, hour, minute)

# Función para cargar datos de la base de datos
def fetch_data_from_db(table_name):
    query = f"SELECT * FROM {table_name}"
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

# Detectar valores atípicos en una columna
def detect_anomalies(data, column, threshold=3):
    """Detectar valores atípicos en una columna usando desviaciones estándar."""
    mean = data[column].mean()
    std_dev = data[column].std()
    anomalies = data[np.abs(data[column] - mean) > threshold * std_dev]
    return anomalies

# Asociar anomalías con coordenadas GPS
def map_anomalies_to_gps(anomalies, gps_data, time_column="timestamp"):
    """Mapea las anomalías de arduino_data a los datos GPS más cercanos en tiempo."""
    # Convertir timestamps de cadena a datetime
    gps_data[time_column] = pd.to_datetime(gps_data[time_column], errors='coerce')
    anomalies[time_column] = pd.to_datetime(anomalies[time_column], errors='coerce')

    # Redondear los timestamps de arduino_data a segundos
    anomalies[time_column] = anomalies[time_column].dt.floor('S')

    # Remover valores nulos generados por errores en la conversión
    gps_data = gps_data.dropna(subset=[time_column])
    anomalies = anomalies.dropna(subset=[time_column])

    # Ordenar datos por tiempo
    gps_data = gps_data.sort_values(by=time_column)
    anomaly_gps_mapping = []

    for _, anomaly in anomalies.iterrows():
        anomaly_time = anomaly[time_column]

        # Encontrar el punto GPS más cercano en el tiempo
        closest_gps = gps_data.iloc[(gps_data[time_column] - anomaly_time).abs().idxmin()]
        anomaly_gps_mapping.append({
            "anomaly_time": anomaly[time_column],
            "anomaly_value": anomaly["z_acel_l"],
            "gps_time": closest_gps[time_column],
            "latitude": closest_gps["latitude"],
            "longitude": closest_gps["longitude"]
        })

    return pd.DataFrame(anomaly_gps_mapping)

# Flujo Principal
if __name__ == "__main__":
    # Cargar datos de la base de datos
    arduino_data = fetch_data_from_db("arduino_data")
    gps_data = fetch_data_from_db("gps_data")

    # Detectar anomalías en la columna z_acel_l
    anomalies = detect_anomalies(arduino_data, column="z_acel_l")

    if not anomalies.empty:
        print(f"Anomalías detectadas:\n{anomalies[['timestamp', 'z_acel_l']]}")
        
        # Mapear las anomalías a las posiciones GPS
        anomaly_gps_mapping = map_anomalies_to_gps(anomalies, gps_data)
        print(f"Mapa de anomalías con GPS:\n{anomaly_gps_mapping}")

        """
        # Ejemplo de uso
        phone_number = "+56951977208"  # Número de WhatsApp
        message = "Hola"  # Mensaje
        send_whatsapp_message(phone_number, message)
        """

        phone_number = "+56951977208"  # Incluye el '+'
        message = "Se ha detectado una anomalía"
        send_whatsapp_message_now(phone_number, message)