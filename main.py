from flask import Flask, request, jsonify, send_file
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

app = Flask(__name__)
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

@app.route('/process-all-data', methods=['GET'])
def process_all_data():
    """Procesar datos de la base de datos PostgreSQL para un ID específico."""

    try:
        # Conexión a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()

        # Consulta para obtener los datos de la tabla arduino_data
        query = """
            SELECT * FROM arduino_data
        """
        cur.execute(query)  # Prevenir inyección SQL
        data = cur.fetchall()

        # Si no se encuentra el ID
        if not data:
            return jsonify({"error": "No se encontraron datos"}), 404

        # Obtener los nombres de las columnas
        column_names = [desc[0] for desc in cur.description]

        # Crear un DataFrame para el procesamiento
        df = pd.DataFrame(data, columns=column_names)

        # Renombrar columna 'timestamp' a 'date'
        df.rename(columns={'timestamp': 'date'}, inplace=True)
        df['date_atemp'] = range(1, len(df) + 1)

        # Convertir las primeras filas del DataFrame a diccionario
        result = df.to_dict(orient='records')

        # Cerrar la conexión a la base de datos
        cur.close()
        conn.close()

        return jsonify({
            "data": result
        })

    except psycopg2.Error as e:
        return jsonify({"error": f"Error de base de datos: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['GET'])
def process():
    try:
        data_point = request.args.get('data_point')
        response = requests.get("http://localhost:5000/process-all-data")
        response.raise_for_status()
        processed_data = response.json()

        if 'error' in processed_data:
            return jsonify(processed_data)

        data = processed_data.get("data")
        if not data:
            return jsonify({"error": "No se encontraron datos en la respuesta"}), 400

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

        # Convertir fechas de anomalías a segundos relativos desde min_date
        data_x_st = [(pd.to_datetime(date) - min_date).total_seconds() for date in anomaly_dates]

        label_x_st = 'Tiempo (segundos desde el inicio)'
        label_y_st = 'Valor'

        """
        # Gráfico de anomalías
        plt.figure(figsize=(14, 7))
        plt.plot(range(len(time_series)), time_series, label='Serie Temporal Original', color='blue')
        plt.plot(range(len(time_series)), reconstructions, label='Reconstrucción del VAE', color='green', linestyle='--')
        plt.scatter(anomaly_indices, anomaly_values, color='red', label='Anomalías', marker='x')

        # Líneas verticales para las anomalías
        for anomaly_index in anomaly_indices:
            plt.axvline(anomaly_index, color='orange', linestyle=':')

        plt.xlabel('Índice de Tiempo')
        plt.ylabel('Valor')
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(integer=True, prune='both'))

        plt.title('Detección de Anomalías en la Serie Temporal')
        plt.legend()
        plt.tight_layout()
        plt.show()
        """

        # Calcular x_st y y_st dentro del proceso principal
        x_st = [(date - min_date).total_seconds() for date in df['date']]
        y_st = time_series.tolist()  # time_series contiene los valores originales


        return jsonify({
            "x_st": x_st,
            "y_st": y_st,
            "label_x_st": label_x_st,
            "data_x_st": data_x_st,
            "label_y_st": label_y_st,
            "data_y_st": anomaly_values.tolist()
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error al llamar a /process-all-data: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error en el procesamiento: {str(e)}"}), 500

# Bloque para ejecutar la aplicación
if __name__ == '__main__':
    # Cambiar `debug=True` por `debug=False` para producción
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))