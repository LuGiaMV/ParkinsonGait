import numpy as np
import requests
import pandas as pd
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Input, Dense
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import pywt
from scipy.signal import find_peaks
import os
import io
import psycopg2
from datetime import datetime

# Configuración de la conexión a la base de datos
DB_CONFIG = {
    "host": "junction.proxy.rlwy.net",
    "port": 51508,
    "user": "postgres",
    "password": "ruyeJZhoonKcduSYQZidpOPxXWsDAZUg",
    "dbname": "railway",
}

def get_db_connection():
    """Establecer conexión con la base de datos PostgreSQL."""
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        dbname=DB_CONFIG["dbname"],
    )


# Función para aplicar la Transformada Wavelet Continua (CWT)
def perform_cwt(signal, wavelet='cmor', scales=np.arange(1, 16)):
    coefficients, frequencies = pywt.cwt(signal, scales, wavelet)
    return coefficients, frequencies

# Modelo DenseVAE
class DenseVAE(tf.keras.Model):
    def __init__(self, input_dim, latent_dim, beta=1.0):
        super(DenseVAE, self).__init__()
        self.latent_dim = latent_dim
        self.beta = beta
        # Encoder y Decoder usando Input en lugar de InputLayer
        self.encoder = Sequential([
            Input(shape=(input_dim,)),  # Cambiado InputLayer por Input
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(latent_dim + latent_dim),
        ])

        self.decoder = Sequential([
            Input(shape=(latent_dim,)),  # Cambiado InputLayer por Input
            Dense(32, activation='relu'),
            Dense(64, activation='relu'),
            Dense(input_dim, activation='sigmoid'),
        ])

    def encode(self, x):
        mean, logvar = tf.split(self.encoder(x), num_or_size_splits=2, axis=1)
        return mean, logvar

    def reparameterize(self, mean, logvar):
        eps = tf.random.normal(shape=mean.shape)
        return eps * tf.exp(logvar * 0.5) + mean

    def decode(self, z, apply_sigmoid=False):
        logits = self.decoder(z)
        if apply_sigmoid:
            return tf.sigmoid(logits)
        return logits

    def call(self, x):
        mean, logvar = self.encode(x)
        z = self.reparameterize(mean, logvar)
        x_recon = self.decode(z)
        return x_recon, mean, logvar

# Función de pérdida para DenseVAE
def compute_loss(model, x):
    x_recon, mean, logvar = model(x)
    reconstruction_loss = tf.reduce_mean(tf.keras.losses.mse(x, x_recon))
    kl_loss = -0.5 * tf.reduce_mean(1 + logvar - tf.square(mean) - tf.exp(logvar)) * model.beta
    total_loss = reconstruction_loss + kl_loss
    return total_loss

conn = get_db_connection() 
cur = conn.cursor()

# Consulta para obtener los datos de la tabla arduino_data
query = """
    SELECT * FROM arduino_data
"""
cur.execute(query)  # Prevenir inyección SQL
data = cur.fetchall()

# Obtener los nombres de las columnas
column_names = [desc[0] for desc in cur.description]

# Crear un DataFrame para el procesamiento
df = pd.DataFrame(data, columns=column_names)

# Renombrar columna 'timestamp' a 'date'
df.rename(columns={'timestamp': 'date'}, inplace=True)
df['date_atemp'] = range(1, len(df) + 1)

# Convertir las primeras filas del DataFrame a diccionario
result = df.to_dict(orient='records')

data_point = 'z_acel_l'
processed_data = result

data = processed_data.get("data") if isinstance(processed_data, dict) else None
if not data:
    raise ValueError("No se encontraron datos válidos en 'processed_data'.")

# Crea un DataFrame (si 'data' contiene registros)
df = pd.DataFrame(data)
df.rename(columns={'timestamp': 'date'}, inplace=True)
df['date_atemp'] = range(1, len(df) + 1)
df = df.dropna()

df['date'] = pd.to_datetime(df['date'])
min_date = df['date'].min()  # Fecha mínima como referencia
time_series = df[data_point].values
# print(df)
# print(time_series)
scaler = MinMaxScaler()
time_series_scaled = scaler.fit_transform(time_series.reshape(-1, 1)).flatten()

# input_dim se establece como la longitud de la serie temporal
input_dim = time_series_scaled.shape[0]

# Convertir los datos a tensor para VAE
train_data = tf.convert_to_tensor(time_series_scaled.reshape(1, -1), dtype=tf.float32)

latent_dim = 2
beta = 5
vae = DenseVAE(input_dim=input_dim, latent_dim=latent_dim, beta=beta)

optimizer = tf.keras.optimizers.Adam()
epochs = 100

for epoch in range(epochs):
    with tf.GradientTape() as tape:
        loss = compute_loss(vae, train_data)
    gradients = tape.gradient(loss, vae.trainable_variables)
    optimizer.apply_gradients(zip(gradients, vae.trainable_variables))
    print(f"Epoch {epoch + 1}, Loss: {loss.numpy()}")

# Reconstrucción y cálculo del error
reconstructions = vae(train_data)[0].numpy().flatten()
reconstruction_error = np.abs(time_series_scaled - reconstructions)

threshold = np.percentile(reconstruction_error, 98)
anomaly_indices = np.where(reconstruction_error > threshold)[0]
anomaly_dates = df['date'].iloc[anomaly_indices].values
anomaly_values = time_series[anomaly_indices]