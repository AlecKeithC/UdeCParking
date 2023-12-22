from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget, QGridLayout
import cv2
import numpy as np
import onnxruntime as ort
import sys
import time
import threading
import json
from utils import letterbox,load_parking_points, draw_parking_points, apply_nms,apply_nms2, adjust_contrast_brightness
import psycopg2
import math
from datetime import datetime

#Quedarse en la app con los datos de la última actualización de los que tienen estatica true

c_x= 320
past_angles_x = []
D = 10.0  # en metros
pixel_to_meter = 0.01  # en metros por píxel
current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def update_last_update():
    while True:
        try:
            connection = psycopg2.connect(
                host="192.168.1.81",
                database="parkingdb",
                port="32783",
                user="admin",
                password="detectaudec"
            )
            cursor = connection.cursor()
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_query = """UPDATE parking SET last_update = %s WHERE estatica = TRUE"""
            cursor.execute(update_query, (current_timestamp,))
            connection.commit()
        except Exception as e:
            print("Error al actualizar la base de datos:", e)
        finally:
            if connection:
                if not connection.closed:
                    connection.close()

        time.sleep(0.1)  # Esperar 5 segundos antes de la próxima actualización

# Crear y comenzar el hilo
update_thread = threading.Thread(target=update_last_update, daemon=True)
update_thread.start()

def update_database(cam_id, free_spaces, total_spaces, pk_name, latitude, longitude, user_types, reduced_capacity, active, last_update, estatica):
    try:
        connection = psycopg2.connect(
            host="192.168.1.81",
            database="parkingdb",
            port="32783",
            user="admin",
            password="detectaudec"
        )
        cursor = connection.cursor()
        
        academico = 'Academico' in user_types
        estudiante = 'Estudiante' in user_types
        administrativo = 'Administrativo' in user_types
        otro = 'Otros' in user_types
        query = """
            INSERT INTO parking (id, free_spaces, total_spaces, pk_name, latitude, longitude, reduced_capacity, 
                                 academico, estudiante, administrativo, otro, active, last_update, estatica)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
            free_spaces = EXCLUDED.free_spaces,
            total_spaces = EXCLUDED.total_spaces,
            pk_name = EXCLUDED.pk_name,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            reduced_capacity = EXCLUDED.reduced_capacity,
            academico = EXCLUDED.academico,
            estudiante = EXCLUDED.estudiante,
            administrativo = EXCLUDED.administrativo,
            otro = EXCLUDED.otro,
            active = EXCLUDED.active,
            last_update = EXCLUDED.last_update,
            estatica = EXCLUDED.estatica;
        """

        cursor.execute(query, (cam_id, free_spaces, total_spaces, pk_name, latitude, longitude, reduced_capacity, 
                               academico, estudiante, administrativo, otro, active, last_update, estatica))

        connection.commit()

        if not active:
            # Si active es False, borramos la fila correspondiente.
            delete_query = "DELETE FROM parking WHERE id = %s;"
            cursor.execute(delete_query, (cam_id,))
            connection.commit()
    except Exception as e:
        print("Error al actualizar la base de datos:", e)
    finally:
        if connection:
            if not connection.closed:
                connection.close()


def initialize_cameras_in_db():
    for cam_id in range(0, 16):  # Asumiendo que los cam_id van del 1 al 16
        update_database(cam_id, 0, 0, "Unknown", 0, 0, [], False, False, current_timestamp, False)

initialize_cameras_in_db()

with open('lib/camera_info_temp.json', 'r') as f:
    camera_info_temp = json.load(f)

semaphore = threading.Semaphore(1)  # Semáforo para controlar el acceso a la inferencia

cuda = True
w = "yolov6s6.onnx"
providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if cuda else ['CPUExecutionProvider']
session = ort.InferenceSession(w, providers=providers)

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QPixmap)
    parking_data = {}  # Nueva variable para almacenar la información del estacionamiento
    last_parking_data = {}  # Variable de clase para almacenar la última data conocida
    def __init__(self, cap, session, parent_label, cam_id, ip_address, pk_name, score_threshold, nms_threshold, reduced_capacity, user_types, latitude, longitude, active, already_counted_at_zero, last_update, estatica):  # Añadir ip_address como argumento
        super().__init__()
        self.cap = cap
        self.session = session
        self.parent_label = parent_label
        self.cam_id = cam_id
        self.pk_name = pk_name
        self.last_time = 0
        self.current_boxes = []
        self.current_labels = []
        self.parking_points, self.point_scores = load_parking_points(cam_id)
        self.free_spaces = len(self.parking_points)
        self.ip_address = ip_address  # Añadir esta línea para guardar la dirección IP
        self.status = "disconnected"  # Nuevo atributo para el estado de la cámara
        self.connection_timeout = time.time() + 300  # 10 segundos para el tiempo de espera
        self.skip_camera = False  # Bandera para saber si se debe omitir el procesamiento de esta cámara
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.user_types = user_types
        self.reduced_capacity = reduced_capacity
        self.latitude = latitude
        self.longitude = longitude
        self.active = active
        self.already_counted_at_zero = False  # Agrega esta variable de instancia
        self.estatica = estatica
        self.last_update = current_timestamp
        self.last_time_updated = None
        self.semaphore_detected = False
        self.previous_last_update = None

    def verificar_out_of_range(self):
        try:
            connection = psycopg2.connect(
                host="192.168.1.81",
                database="parkingdb",
                port="32783",
                user="admin",
                password="detectaudec"
            )
            cursor = connection.cursor()
            cursor.execute("SELECT out_of_range FROM parking_status WHERE id = %s;", (self.cam_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
        except Exception as e:
            print(f"Error al verificar out_of_range para la cámara {self.cam_id}: {e}")
            return False
        finally:
            if connection and not connection.closed:
                connection.close()

    def retry_connection(self):
        time.sleep(10)  # Espera 10 segundos antes de volver a intentar
        self.cap.release()  # Libera el objeto VideoCapture antes de volver a intentar
        with open('lib/camera_info.json', 'r') as f:  # Asegúrate de que el nombre del archivo esté entre comillas
            camera_info_reconnect = json.load(f)
            for cam in camera_info_reconnect:
                if cam['id'] == self.cam_id:
                    self.ip_address = cam['ip']
                    self.score_threshold = cam.get('score_threshold', self.score_threshold)  # Usar valor predeterminado si no está presente
                    self.nms_threshold = cam.get('nms_threshold', self.nms_threshold)
                    break
        self.cap = cv2.VideoCapture(self.ip_address)  # Utilizar ip_address para volver a intentar la conexión
        if self.cap.isOpened():
            self.connection_timeout = time.time() + 10  # Restablecer el tiempo de espera
            self.skip_camera = False  # Reiniciar la bandera
            self.status = "connected"
            self.run()
        else:
            self.retry_connection()

    def run(self):

        occupied_points = set()  # Usar un conjunto para almacenar puntos ocupados

        if time.time() > self.connection_timeout:
            self.skip_camera = True  # Si se supera el tiempo de espera, omitir la cámara

        if self.skip_camera:  # Si se debe omitir la cámara, intentar volver a conectar
            self.retry_connection()
            return

        if not self.cap.isOpened():
            self.retry_connection()  # Intenta volver a conectar si la cámara no está disponible
            return

        self.status = "connected"  # Actualiza el estado a conectado si la cámara está disponible

        while True:
            ret, frame = self.cap.read()
            if frame is None or not ret:
                self.status = "disconnected"  # Estado actualizado a desconectado
                self.active = False
                # Crear una imagen negra de tamaño 640x640x3
                frame = np.zeros((640, 640, 3), dtype=np.uint8)

                # Escribir el mensaje en el centro
                font = cv2.FONT_HERSHEY_SIMPLEX
                text = f"Cámara {self.cam_id} no disponible"
                text_size = cv2.getTextSize(text, font, 1, 2)[0]
                text_x = int((frame.shape[1] - text_size[0]) / 2)
                text_y = int((frame.shape[0] + text_size[1]) / 2)
                cv2.putText(frame, text, (text_x, text_y), font, 1, (255, 255, 255), 2)

                # Convertir el frame a QPixmap y emitir la señal
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                pixmap_resized = pixmap.scaled(self.parent_label.width(), self.parent_label.height(), Qt.AspectRatioMode.IgnoreAspectRatio)
                self.change_pixmap_signal.emit(pixmap_resized)  # Emitir la señal aquí

                self.retry_connection()  # Luego llama a retry_connection
                continue
            else:
                frame = cv2.resize(frame, (640, 640))

            if ret:
                frame = cv2.resize(frame, (1280, 1280))
                #frame = adjust_contrast_brightness(frame, 0.9,-1)


                current_time = time.time()
                if current_time - self.last_time >= 1.5:  # Realizar inferencia cada 5 segundos
                    
                    with semaphore:  # Usar el semáforo
                        self.last_time = current_time
                        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        image, _, _ = letterbox(img)
                        image = image.transpose((2, 0, 1))
                        image = np.expand_dims(image, 0)
                        image = np.ascontiguousarray(image)
                        im = image.astype(np.float32) / 255.0
                        out = self.session.run(None, {'images': im})
                        obj_num = out[0][0]
                        boxes = out[1][0]
                        scores = out[2][0]
                        cls_ids = out[3][0]
                        self.current_boxes = []
                        score_list = []
                        for i in range(int(obj_num[0])):
                            box = boxes[i]
                            score = scores[i]
                            cls_id = int(cls_ids[i])
                            if score > 0.01 and cls_id in [2, 7, 9]:
                                x1, y1, x2, y2 = map(int, box)
                                self.current_boxes.append(([x1, y1, x2, y2], cls_id, score))
                                score_list.append(score)
                        if int(obj_num[0]) == 0:
                            occupied_points.clear()

                        self.current_boxes = apply_nms2(self.current_boxes, score_list, threshold=self.nms_threshold)

            self.free_spaces = len(self.parking_points)  # Resetear los espacios libres
            occupied_points.clear()  # Limpiar el conjunto de puntos ocupados

            # Dibujar las últimas cajas detectadas
            # for (x1, y1, x2, y2), cls_id, score in self.current_boxes:
            #     cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            self.out_of_range = self.verificar_out_of_range()
            # Decidir si proceder con el conteo de espacios ocupados o no
            proceed_with_count = not self.out_of_range or (self.out_of_range and self.already_counted_at_zero)
            self.free_spaces = len(self.parking_points)  # Asume que todos los puntos están libres inicialmente
            if proceed_with_count:
                # Creando un conjunto de puntos disponibles
                available_points = set((point['x'], point['y']) for point in self.parking_points)
                occupied_points = set()  # Crear un conjunto para almacenar los puntos ocupados

                # Bloque de código para comprobar si un punto está dentro de una caja
                for box, cls_id, score in self.current_boxes:
                    if cls_id:  # Ignora el semáforo, solo se enfoca en vehículos
                        x1, y1, x2, y2 = box
                        box_center = [(x1 + x2) // 2, (y1 + y2) // 2]  # Calcula el centro de la caja

                        # Busca el punto más cercano al centro de la caja que aún esté disponible, esté dentro de la caja y tenga un score menor o igual al de la caja
                        min_distance = float('inf')
                        nearest_point = None

                        for point in available_points:
                            px, py = point
                            if x1 <= px <= x2 and y1 <= py <= y2:  # Comprueba que el punto esté dentro de la caja
                                point_dict = next((p for p in self.parking_points if p['x'] == px and p['y'] == py), None)
                                if point_dict is not None:
                                    point_index = self.parking_points.index(point_dict)  # Get the index of the point in self.parking_points
                                    point_score = self.point_scores[point_index]  # Get the score of the point
                                    if score >= point_score:  # Check if the box's score is greater or equal to the point's score
                                        distance = (box_center[0] - px) ** 2 + (box_center[1] - py) ** 2
                                        if distance < min_distance:
                                            min_distance = distance
                                            nearest_point = point

                        # Si encontramos un punto más cercano, lo marcamos como ocupado
                        if nearest_point:
                            occupied_points.add(nearest_point)

                # Eliminamos los puntos ocupados de los puntos disponibles después de procesar todas las cajas
                for point in occupied_points:
                    available_points.remove(point)

                self.free_spaces = len(available_points)  # Actualizar los espacios libres
                self.occupied_spaces = len(self.parking_points) - self.free_spaces  # Actualizar los espacios ocupados
                    # Actualizar el último last_update conocido
                self.previous_last_update = self.last_update
            VideoThread.parking_data[self.cam_id] = {'free_spaces': self.free_spaces,
                                                    'total_spaces': len(self.parking_points),
                                                    'pk_name': self.pk_name,
                                                    'latitude': self.latitude,
                                                    'longitude': self.longitude,
                                                    'user_types': self.user_types,
                                                    'reduced_capacity': self.reduced_capacity}

            if VideoThread.parking_data != VideoThread.last_parking_data:  # Comprueba si hay cambios
                with open('parking_status.json', 'w') as f:
                    json.dump(VideoThread.parking_data, f, indent=4)
                VideoThread.last_parking_data = VideoThread.parking_data.copy()  # Guarda la data actual como la última conocida
                self.active = True  # Actualiza el estado de actividad a Verdadero
                update_database(self.cam_id, self.free_spaces, len(self.parking_points), self.pk_name, self.latitude, self.longitude, self.user_types, self.reduced_capacity,
                                self.active, self.last_update, self.estatica)

            frame = draw_parking_points(frame, self.parking_points, occupied_points)
            # Convertir el frame a QPixmap y emitir la señal
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            pixmap_resized = pixmap.scaled(self.parent_label.width(), self.parent_label.height(), Qt.AspectRatioMode.IgnoreAspectRatio)
            self.change_pixmap_signal.emit(pixmap_resized)

            time.sleep(0.03)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MT Parking Detector")
        self.setGeometry(100, 100, 1280, 720)
        self.initUI()

    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.grid_layout = QGridLayout()
        self.central_widget.setLayout(self.grid_layout)
        for i in range(4):
            self.grid_layout.setColumnStretch(i, 1)
            self.grid_layout.setRowStretch(i, 1)
        self.labels = []
        self.threads = []

        for cam in camera_info_temp:
            label = QLabel(f"Camera {cam['id']}")
            self.grid_layout.addWidget(label, cam['id'] // 4, cam['id'] % 4)
            self.labels.append(label)

            ip_address = cam['ip']
            pk_name = cam['name']
            score_threshold = cam['score_threshold']
            nms_threshold = cam['nms_threshold']
            reduced_capacity = cam['reduced_capacity']
            user_types = cam['user_types']
            latitud = cam['latitude']
            longitud = cam['longitude']
            active = True
            already_counted_at_zero = False
            estatica = cam['estatica']
            print(estatica)

            last_update = time.time()
            if isinstance(ip_address, int) or (isinstance(ip_address, str) and len(ip_address) == 1):
                cap = cv2.VideoCapture(int(ip_address))
            else:
                cap = cv2.VideoCapture(ip_address)

            thread = VideoThread(cap, session, label, cam['id'], ip_address, pk_name, score_threshold, nms_threshold, reduced_capacity, user_types, latitud, longitud,active, already_counted_at_zero, last_update, estatica)  # Añadir ip_address como argumento
            thread.change_pixmap_signal.connect(label.setPixmap)
            self.threads.append(thread)
            thread.start()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.showMaximized()
    sys.exit(app.exec())