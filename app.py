import os
import sys
from flask import Flask, request, render_template, jsonify
from gevent.pywsgi import WSGIServer
import numpy as np
from util import base64_to_pil  # Asegúrate de tener esta función importada desde tu utilidad
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import mysql.connector

app = Flask(__name__)

MODEL_PATH = 'models/model_planta.h5'
model = load_model(MODEL_PATH)
print('Model loaded. Check http://127.0.0.1:5000/')

CUSTOM_CLASSES_PATH = 'custom_classes.txt'

def load_custom_classes(file_path):
    with open(file_path, 'r') as file:
        classes = [line.strip() for line in file.readlines()]
    return classes

custom_classes = load_custom_classes(CUSTOM_CLASSES_PATH)

def model_predict(img, model):
    img = img.resize((224, 224))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = x / 255.0  # Normaliza los píxeles
    preds = model.predict(x)
    predicted_class_index = np.argmax(preds)
    predicted_class = custom_classes[predicted_class_index]
    pred_proba = "{:.3f}".format(np.amax(preds))
    return predicted_class, pred_proba

# Configuración de la conexión a la base de datos MySQL
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''
MYSQL_DB = 'iaplantas'

def save_to_database(image_path, predicted_class):
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

        cursor = connection.cursor()

        insert_query = "INSERT INTO predictions (image_path, predicted_class) VALUES (%s, %s)"
        cursor.execute(insert_query, (image_path, predicted_class))

        connection.commit()
        print("Datos guardados en la base de datos")

    except mysql.connector.Error as error:
        print("Error al conectar con la base de datos:", error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión a la base de datos cerrada")


# Función para obtener datos de la base de datos
def get_predictions_from_db():
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

        cursor = connection.cursor()

        select_query = "SELECT image_path, predicted_class FROM predictions"
        cursor.execute(select_query)

        predictions = cursor.fetchall()

        connection.commit()
        print("Datos obtenidos de la base de datos")
        return predictions

    except mysql.connector.Error as error:
        print("Error al conectar con la base de datos:", error)
        return []

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión a la base de datos cerrada")

# Ruta para mostrar las predicciones
@app.route('/show_predictions', methods=['GET'])
def show_predictions():
    predictions = get_predictions_from_db()
    return render_template('index.html', predictions=predictions)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        img = base64_to_pil(request.json)
        predicted_class, pred_proba = model_predict(img, model)
        result = predicted_class.replace('_', ' ').capitalize()

        image_path = 'static/image.jpg'
        img.save(image_path)

        save_to_database(image_path, result)

        return jsonify(result=result, probability=pred_proba)
    return None

if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
