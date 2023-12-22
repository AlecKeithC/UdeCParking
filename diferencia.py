import cv2
import numpy as np
import json
import threading
import psycopg2
import time

def cargar_configuracion(id_camara):
    with open(f'Rectangle/Rectangulo_{id_camara}.json', 'r') as f:
        data = json.load(f)
    x1, y1 = data['rectangle'][0]
    x2, y2 = data['rectangle'][1]
    umbral_cambio = data['umbral_cambio']
    return x1, y1, x2 - x1, y2 - y1, umbral_cambio

def calcular_diferencia(frame1, frame2, x, y, ancho, alto):
    roi_frame1 = frame1[y:y+alto, x:x+ancho]
    roi_frame2 = frame2[y:y+alto, x:x+ancho]
    gray1 = cv2.cvtColor(roi_frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(roi_frame2, cv2.COLOR_BGR2GRAY)
    diferencia = cv2.absdiff(gray1, gray2)
    norma = np.sum(diferencia)
    return norma

def reset_out_of_range():
    try:
        with psycopg2.connect(
                host="192.168.1.81",
                database="parkingdb",
                port="32783",
                user="admin",
                password="detectaudec"
        ) as connection:
            with connection.cursor() as cursor:
                query = "UPDATE parking_status SET out_of_range = False;"
                cursor.execute(query)
                connection.commit()
                print("Todos los estados de out_of_range se han reseteado a False.")
    except Exception as e:
        print(f"Error al resetear out_of_range en la base de datos: {e}")

# Llamada a la función al inicio del script
reset_out_of_range()
def update_database(cam_id, out_of_range):
    try:
        connection = psycopg2.connect(
            host="192.168.1.81",
            database="parkingdb",
            port="32783",
            user="admin",
            password="detectaudec"
        )
        cursor = connection.cursor()

        # Convertir numpy.bool_ a booleano de Python
        out_of_range_bool = bool(out_of_range)
        # Actualiza la nueva tabla
        query = """
            INSERT INTO parking_status (id, out_of_range)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET 
            out_of_range = EXCLUDED.out_of_range;
        """
        cursor.execute(query, (cam_id, out_of_range_bool))
        connection.commit()
    except Exception as e:
        print(f"Error al actualizar la base de datos para la cámara {cam_id}: {e}")
    finally:
        if connection and not connection.closed:
            connection.close()

def procesar_camara(camara_info):
    x, y, ancho, alto, umbral_cambio = cargar_configuracion(camara_info['id'])
    frame_referencia = cv2.imread(f'Rectangle/Rectangulo_{camara_info["id"]}.png')
    cap = cv2.VideoCapture(camara_info['ip'])

    tiempo_ultima_ejecucion = time.time()

    while True:
        tiempo_actual = time.time()

        # Solo ejecutar si han pasado 5 segundos desde la última vez
        if tiempo_actual - tiempo_ultima_ejecucion >= 5:
            ret, frame_actual = cap.read()
            if not ret:
                break
            cap = cv2.VideoCapture(camara_info['ip'])
            frame_actual_resized = cv2.resize(frame_actual, (640, 640))
            norma_diferencia = calcular_diferencia(frame_referencia, frame_actual_resized, x, y, ancho, alto)

            out_of_range_actual = norma_diferencia > umbral_cambio

            if out_of_range_actual:
                print(f"Se detectó un cambio significativo en la cámara {camara_info['id']}.")
                update_database(camara_info['id'], True)
                print("Se actualizó la db")
            else:
                update_database(camara_info['id'], False)
                print("Se actualizó la db")

            tiempo_ultima_ejecucion = tiempo_actual


    cap.release()

# Cargar información de las cámaras
with open('lib/camera_info.json', 'r') as f:
    camaras = json.load(f)

# Filtrar cámaras estáticas
camaras_estaticas = [camara for camara in camaras if camara.get('estatica')]

# Crear un hilo para cada cámara estática
for camara in camaras_estaticas:
    threading.Thread(target=procesar_camara, args=(camara,)).start()
