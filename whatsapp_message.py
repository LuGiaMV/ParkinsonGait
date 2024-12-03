import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import pywhatkit as kit

# Conexión a la base de datos PostgreSQL
DATABASE_URL = "postgresql+psycopg2://postgres:ruyeJZhoonKcduSYQZidpOPxXWsDAZUg@junction.proxy.rlwy.net:51508/railway"
engine = create_engine(DATABASE_URL)

# Función para enviar mensajes de WhatsApp
def send_whatsapp_message_now(phone_number, message):
    # Obtiene la hora actual y agrega 2 minutos para evitar problemas de carga
    now = datetime.now() + timedelta(minutes=2)
    hour = now.hour
    minute = now.minute

    # Enviar el mensaje
    try:
        kit.sendwhatmsg(phone_number, message, hour, minute)
        print(f"Mensaje programado para {hour}:{minute}.")
    except Exception as e:
        print(f"Error al enviar el mensaje: {e}")
    
# Función para generar el mensaje de WhatsApp basado en las anomalías detectadas
def generate_whatsapp_message(anomalies_with_gps):
    """
    Genera un mensaje con los detalles de las anomalías detectadas.
    """
    message = "⚠️ *Posibles caidas detectadas:* ⚠️\n\n"
    for _, row in anomalies_with_gps.iterrows():
        message += (
            f"📍 *Posible Caida*\n"
            f"   - Tiempo: {row['anomaly_time']}\n"
            f"   - Valor: {row['anomaly_value']}\n"
            f"   - Coordenadas: {row['latitude']}, {row['longitude']}\n\n"
        )
    return message.strip()

# Función para cargar datos de la base de datos desde una fecha específica
def fetch_data_from_db(table_name, start_date):
    query = f"""
        SELECT *
        FROM {table_name}
        WHERE timestamp >= '{start_date}'
    """
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

# Detectar valores atípicos en una columna
def detect_anomalies(data, column, upper_threshold=2, lower_threshold=-2):
    """
    Detectar valores atípicos en una columna basados en un rango.
    Considera como atípico cualquier valor mayor al umbral superior o menor al umbral inferior.
    """
    anomalies = data[(data[column] > upper_threshold) | (data[column] < lower_threshold)]
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
    # Establecer la fecha de inicio (2024-12-02)
    start_date = "2024-12-02"

    # Cargar datos de la base de datos desde la fecha específica
    arduino_data = fetch_data_from_db("arduino_data", start_date)
    gps_data = fetch_data_from_db("gps_data", start_date)

    # Detectar anomalías en la columna z_acel_l usando el umbral personalizado
    anomalies = detect_anomalies(arduino_data, column="z_acel_l", upper_threshold=2, lower_threshold=-2)

    if not anomalies.empty:
        print(f"Anomalías detectadas:\n{anomalies[['timestamp', 'z_acel_l']]}")

        # Mapear las anomalías a las posiciones GPS
        anomaly_gps_mapping = map_anomalies_to_gps(anomalies, gps_data)
        print(f"Mapa de anomalías con GPS:\n{anomaly_gps_mapping}")

        # Generar mensaje de WhatsApp
        message = generate_whatsapp_message(anomaly_gps_mapping)
        print(f"Mensaje a enviar por WhatsApp:\n{message}")

        # Enviar una notificación por WhatsApp
        phone_number = "+56979599627"  # Incluye el '+'
        send_whatsapp_message_now(phone_number, message)