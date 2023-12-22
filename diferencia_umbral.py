import cv2
import numpy as np
import json
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
import time
import json
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
# Variables globales
x_inicio, y_inicio, x_fin, y_fin = -1, -1, -1, -1
dibujando = False
umbral_cambio = 10000
frame_referencia = None

# Funciones de procesamiento de imágenes
def seleccionar_area(event, x, y, flags, param):
    global x_inicio, y_inicio, x_fin, y_fin, dibujando, frame_referencia
    if event == cv2.EVENT_LBUTTONDOWN:
        dibujando = True
        x_inicio, y_inicio = x, y
    elif event == cv2.EVENT_MOUSEMOVE and dibujando:
        frame_temp = frame_referencia.copy()
        cv2.rectangle(frame_temp, (x_inicio, y_inicio), (x, y), (0, 255, 0), 2)
        cv2.imshow('Frame Referencia', frame_temp)
    elif event == cv2.EVENT_LBUTTONUP:
        dibujando = False
        x_fin, y_fin = x, y
        cv2.rectangle(frame_referencia, (x_inicio, y_inicio), (x_fin, y_fin), (0, 255, 0), 2)
        cv2.imshow('Frame Referencia', frame_referencia)

def on_trackbar(val):
    global umbral_cambio
    umbral_cambio = val * 0.01e6

def calcular_diferencia(frame1, frame2, x, y, ancho, alto):
    roi_frame1 = frame1[y:y+alto, x:x+ancho]
    roi_frame2 = frame2[y:y+alto, x:x+ancho]
    gray1 = cv2.cvtColor(roi_frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(roi_frame2, cv2.COLOR_BGR2GRAY)
    diferencia = cv2.absdiff(gray1, gray2)
    norma = np.sum(diferencia)
    return norma

def guardar_configuracion(id_camara, x, y, ancho, alto, umbral):
    data = {'rectangle': [[x, y], [x + ancho, y + alto]], 'umbral_cambio': umbral}
    with open(f'Rectangle/Rectangulo_{id_camara}.json', 'w') as f:
        json.dump(data, f)

def guardar_frame_referencia(id_camara, frame):
    cv2.imwrite(f'Rectangle/Rectangulo_{id_camara}.png', frame)

# Popup para seleccionar el ID de la cámara


class CameraIDPopup(Popup):
    def __init__(self, **kwargs):
        super(CameraIDPopup, self).__init__(**kwargs)
        self.title = 'Seleccione el ID de la cámara'
        self.size_hint = (None, None)
        self.size = (400, 200)

        self.content_layout = BoxLayout(orientation='vertical')

        # Load camera IDs from camera_info.json
        with open('lib/camera_info.json', 'r') as file:
            camera_info = json.load(file)
        camera_ids = [str(info['id']) for info in camera_info]

        # Spinner for camera IDs
        self.spinner = Spinner(
            text='ID',
            values=camera_ids,
            size_hint=(None, None),
            size=(100, 44),
            pos_hint={'center_x': 0.5}  # Add this line
        )
        self.content_layout.add_widget(self.spinner)

        self.confirm_button = Button(text='Confirmar')
        self.confirm_button.bind(on_press=self.on_confirm)
        self.content_layout.add_widget(self.confirm_button)

        self.content = self.content_layout

    def on_confirm(self, instance):
        global id_camara
        id_camara = int(self.spinner.text)  # Use the selected value from the Spinner
        self.dismiss()
        procesar_camara(id_camara)

# Función para procesar la cámara seleccionada
def procesar_camara(id_camara):
    global frame_referencia
    # Cargar información de cámaras desde el archivo JSON
    with open('lib/camera_info.json', 'r') as file:
        camaras = json.load(file)

    camara_seleccionada = next((cam for cam in camaras if cam["id"] == id_camara), None)

    if not camara_seleccionada:
        print(f"No se encontró la cámara con ID {id_camara}")
        exit()

    ip_camara = camara_seleccionada["ip"]

    # Inicializar la cámara
    cap = cv2.VideoCapture(ip_camara)

    # Capturar un frame de referencia
    ret, frame_actual = cap.read()
    if not ret:
        print("No se pudo capturar el frame de la cámara.")
        cap.release()
        exit()

    # Redimensionar el frame de referencia a 640x640
    frame_referencia = cv2.resize(frame_actual, (640, 640))
    cv2.imshow('Frame Referencia', frame_referencia)
    cv2.setMouseCallback('Frame Referencia', seleccionar_area)

    guardar_frame_referencia(id_camara, frame_referencia)

    # Esperar a que el usuario dibuje el rectángulo y presione 'q'
    while True:
        if cv2.waitKey(1) & 0xFF == ord('q') or (x_inicio != -1 and x_fin != -1 and not dibujando):
            break

    cv2.destroyAllWindows()

    # Establecer las coordenadas del rectángulo
    x, y, ancho, alto = min(x_inicio, x_fin), min(y_inicio, y_fin), abs(x_fin - x_inicio), abs(y_fin - y_inicio)

    # Guardar la configuración inicial
    guardar_configuracion(id_camara, x, y, ancho, alto, umbral_cambio)

    # Continuar con el procesamiento de la cámara
    cv2.namedWindow('Frame Actual - Presione Q para salir')
    cv2.createTrackbar('Umbral', 'Frame Actual - Presione Q para salir', int(umbral_cambio/0.01e6), 1000, on_trackbar)

    while True:
        ret, frame_actual = cap.read()
        if not ret:
            break

        # Redimensionar frame_actual a 640x640
        frame_actual_resized = cv2.resize(frame_actual, (640, 640))

        # Dibujar un rectángulo en la región de interés
        cv2.rectangle(frame_actual_resized, (x, y), (x + ancho, y + alto), (0, 255, 0), 2)

        # Calcular la diferencia con el frame de referencia
        norma_diferencia = calcular_diferencia(frame_referencia, frame_actual_resized, x, y, ancho, alto)

        # Verificar si el frame ha cambiado significativamente
        if norma_diferencia > umbral_cambio:
            print("Se detectó un cambio significativo en la cámara.")

        # Mostrar el frame actual
        cv2.imshow('Frame Actual - Presione Q para salir', frame_actual_resized)

        # Salir con 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Guardar la configuración final con el umbral actualizado
    guardar_configuracion(id_camara, x, y, ancho, alto, umbral_cambio)

    cap.release()
    cv2.destroyAllWindows()

# Aplicación principal
class MainApp(App):
    def build(self):
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        popup = CameraIDPopup()
        popup.open()

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'q':
            self.stop()
            return True
        return False

if __name__ == '__main__':
    MainApp().run()
