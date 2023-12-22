#Los colores son todos en formato RGB, de 0-1. Dividir RGB entre 255.
#Licencia Kivy MIT

import json
import json.decoder
import subprocess
import psutil
import threading
import time
import sys
import cv2
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from kivy.uix.progressbar import ProgressBar
from kivy.uix.checkbox import CheckBox

Window.clearcolor = (1, 1, 1, 0)
Window.size = (700,715)

class StylishButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 60
        self.background_color = (41/255, 51/255, 155/255, 0)  # Color de fondo blanco
        self.color = (1, 1, 1, 1)  # Color de texto: blanco
        with self.canvas.before:
            Color(41/255, 51/255, 155/255, 1)  # Color del borde azul oscuro
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[5,])
        self.bind(pos=self.update_rect, size=self.update_rect)
        self.bind(on_press=self.on_button_press, on_release=self.on_button_release)

    def on_button_press(self, instance):
        self.background_color = (116/255, 164/255, 188/255, 1)  # Color cuando se presiona el botón

    def on_button_release(self, instance):
        self.background_color = (41/255, 51/255, 155/255, 0)  # Color cuando se presiona el botón

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class MainApp(App):
    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
        self.title = 'Detect Udec'
        self.icon = 'assets/escudoIcon.ico'
        self.is_check_cameras_done = False
        with open('lib/camera_info.json', 'r') as f:
            camera_info = json.load(f)
        with open('lib/camera_info_temp.json', 'w') as f:
            json.dump(camera_info, f)

    def build(self):
        Window.title = 'DetectUdeC'
        self.layout = GridLayout(cols=2, padding=10,spacing =10)
        self.left_col = BoxLayout(orientation="vertical", spacing=10)
        self.right_col = BoxLayout(orientation="vertical", spacing=5)
        
        self.layout.add_widget(self.left_col)
        self.layout.add_widget(self.right_col)

        self.add_camera_button = StylishButton(text="Añadir cámara")
        self.add_camera_button.bind(on_press=self.add_camera)
        self.left_col.add_widget(self.add_camera_button)

        self.delete_camera_button = StylishButton(text="Eliminar cámara")
        self.delete_camera_button.bind(on_press=self.delete_camera)
        self.left_col.add_widget(self.delete_camera_button)

        self.detections_button = StylishButton(text="Añadir/Editar puntos")
        self.detections_button.bind(on_press=self.open_detections)
        self.left_col.add_widget(self.detections_button)

        self.umbral_button = StylishButton(text="Ajustar Umbral")
        self.umbral_button.bind(on_press=self.open_umbral)
        self.left_col.add_widget(self.umbral_button)

        self.init_detection_button = StylishButton(text="Iniciar detecciones")
        self.init_detection_button.bind(on_press=self.init_detection_and_check)
        self.left_col.add_widget(self.init_detection_button)

        self.stop_detection_button = StylishButton(text="Detener Detecciones")
        self.stop_detection_button.bind(on_press=self.stop_detection)
        self.left_col.add_widget(self.stop_detection_button)

        self.check_cameras_button = StylishButton(text="Verificar cámaras")
        self.check_cameras_button.bind(on_press=lambda instance: self.check_cameras())
        self.left_col.add_widget(self.check_cameras_button)

        self.config_button = StylishButton(text="Configuración")
        self.config_button.bind(on_press=self.open_configuration)
        self.left_col.add_widget(self.config_button)

        self.log_box = TextInput(size_hint=(1, 1), size=(Window.size[0]*0.5,1))
        log_box_container = BoxLayout()
        log_box_container.add_widget(self.log_box)
        self.right_col.add_widget(log_box_container)

        self.status_button = Button(text="Estado: Desconocido", size_hint=(1, 1),size=(Window.size[0]*0.5, 400),background_color = (182/255, 214/255, 204/255, 1))
        self.left_col.add_widget(self.status_button)



        self.camera_status_label = Button(text="Cámara {ID}: Espacios libres: {Número}\n",
                                        font_size='15sp',
                                        color=[1, 1, 1, 1],
                                        background_color = (116/255, 164/255, 188/255, 1), 
                                        size_hint=(1, 1),
                                        size=(Window.size[0], 400),
                                        valign='center',
                                        halign = 'center')

        camera_status_container = BoxLayout()
        camera_status_container.add_widget(self.camera_status_label)
        self.right_col.add_widget(camera_status_container)

        self.camera_status_label.bind(size=self.camera_status_label.setter('text_size'))


        self.last_known_status = None
        self.update_status()
        self.thread_timer = threading.Thread(target=self.status_timer)
        self.thread_timer.daemon = True
        self.thread_timer.start()

        self.thread_camera_status = threading.Thread(target=self.update_camera_status)
        self.thread_camera_status.daemon = True
        self.thread_camera_status.start()

        return self.layout
    
    def init_detection_and_check(self, instance):
        with open('lib/camera_info.json', 'r') as f:
            camera_info = json.load(f)
        with open('lib/camera_info_temp.json', 'w') as f:
            json.dump(camera_info, f)
        self.check_cameras(init_after=True)

    def remove_unavailable_camera(self, cam_id):
        try:
            # Leer la información actual de lib/camera_info_temp.json
            with open('lib/camera_info_temp.json', 'r') as f:
                camera_info_temp = json.load(f)

            for cam in camera_info_temp:
                if cam['id'] == cam_id:
                    print(f"Eliminando IP de la cámara con ID {cam['id']}")
                    cam['ip'] = ''
                    break

            # Guardar de nuevo la información actualizada en lib/camera_info_temp.json
            with open('lib/camera_info_temp.json', 'w') as f:
                json.dump(camera_info_temp, f)

        except FileNotFoundError:
            self.log_box.text += "Archivo lib/camera_info_temp.json no encontrado.\n"
        except json.decoder.JSONDecodeError:
            self.log_box.text += "Error al decodificar el archivo JSON.\n"


    def check_single_camera(self, cam):
        cap = None
        result = [None]

        def _inner_check():
            nonlocal result
            start_time = time.time()  # Registra el tiempo justo antes del intento de conectar
            
            try:
                cap = cv2.VideoCapture(cam['ip'])
                end_time = time.time()  # Registra el tiempo justo después de la conexión
                response_time = (end_time - start_time) * 1000  # Calcula la diferencia y convierte a milisegundos
                result[0] = f"Cámara con ID {cam['id']} disponible. TR: {response_time:.2f} ms\n"
                    
            except Exception as e:
                end_time = time.time()  # Registra el tiempo si se produce una excepción
                response_time = (end_time - start_time) * 1000  # Calcula la diferencia y convierte a milisegundos
                result[0] = f"Error al acceder a cámara con ID {cam['id']}: {str(e)}. TR: {response_time:.2f} ms\n"
                
            finally:
                if cap and cap.isOpened():
                    cap.release()

        thread = threading.Thread(target=_inner_check)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5)  # Espera 5 segundos para que el hilo termine.
        print(result[0])
        if result[0] is None:
            self.remove_unavailable_camera(cam['id'])
            return f"Cámara con ID {cam['id']} no respondió en 5 segundos.\n"
        else:
            # Aquí es donde actualizamos los archivos JSON si la cámara responde correctamente
            with open('lib/camera_info.json', 'r') as f:
                camera_info = json.load(f)
            with open('camera_info_temp_xd.json', 'w') as f:
                json.dump(camera_info, f)
            return result[0]


    def update_logs_on_close(self, instance):
        self.log_box.text += "Verificación de cámaras completada.\n"


    def check_cameras(self, init_after=False):
        # Definir las variables aquí
        total_cameras = 0  # <-- Define total_cameras aquí
        verified_cameras = 0  # <-- Define verified_cameras aquí
        start_time = 0  # <-- Define start_time aquí

        def update_progress_bar():
            nonlocal verified_cameras
            verified_cameras += 1
            self.progress_bar.value = (verified_cameras / total_cameras) * 100

        def close_popup(dt):
            nonlocal start_time
            elapsed_time = time.time() - start_time
            if elapsed_time >= 1:
                self.update_logs_on_close(None)
                popup.dismiss()
                if os.path.exists('camera_info_temp_xd.json'):
                    os.remove('camera_info_temp_xd.json')
            else:
                Clock.schedule_once(close_popup, 1 - elapsed_time)

        def threaded_camera_check():
            nonlocal start_time, total_cameras, verified_cameras

            start_time = time.time()
            total_cameras = len(camera_info)
            verified_cameras = 0

            with ThreadPoolExecutor() as executor:
                for cam in camera_info:
                    result = self.check_single_camera(cam)
                    Clock.schedule_once(lambda dt, res=result: setattr(self.log_box, 'text', self.log_box.text + res))
                    Clock.schedule_once(lambda dt: update_progress_bar())

            Clock.schedule_once(close_popup, 5)

        try:
            with open('lib/camera_info.json', 'r') as f:
                camera_info = json.load(f)
        except FileNotFoundError:
            self.log_box.text += "Archivo lib/camera_info.json no encontrado.\n"
            return

        self.progress_bar = ProgressBar(max=100)
        popup_layout = BoxLayout(orientation='vertical')
        popup_layout.add_widget(Label(text='Verificando cámaras...'))
        popup_layout.add_widget(self.progress_bar)
        popup = Popup(title='Verificación en Progreso', content=popup_layout, size_hint=(None, None), size=(400, 200))

        if init_after:
            popup.bind(on_dismiss=self.init_detection)  # Llamamos a init_detection cuando el pop-up se cierra

        popup.open()
        threading.Thread(target=threaded_camera_check).start()


    def add_camera(self, instance):
        self.log_box.text += "Intentando añadir una nueva cámara.\n"

        content = BoxLayout(orientation="vertical")

        # Campo para el nombre del estacionamiento
        name_input = TextInput(hint_text="Ingrese el nombre del estacionamiento")
        content.add_widget(name_input)

        # Campo para el ID de la cámara
        id_input = TextInput(hint_text="Ingrese el ID de la cámara")
        content.add_widget(id_input)

        # Campo para la IP de la cámara
        ip_input = TextInput(hint_text="Ingrese la IP de la cámara")
        content.add_widget(ip_input)
        latitude_input = TextInput(hint_text="Ingrese la latitud")
        content.add_widget(latitude_input)

        longitude_input = TextInput(hint_text="Ingrese la longitud")
        content.add_widget(longitude_input)
        # CheckBox y Label para capacidad reducida
        reduced_layout = BoxLayout(orientation="horizontal")
        reduced_checkbox = CheckBox()
        reduced_label = Label(text="Capacidad Reducida")
        reduced_layout.add_widget(reduced_checkbox)
        reduced_layout.add_widget(reduced_label)
        content.add_widget(reduced_layout)
        mobile_checkbox = CheckBox()
        mobile_label = Label(text="Cámara móvil")
        mobile_layout = BoxLayout(orientation="horizontal")
        mobile_layout.add_widget(mobile_checkbox)
        mobile_layout.add_widget(mobile_label)
        content.add_widget(mobile_layout)

        # CheckBoxes y Labels para tipos de usuarios
        user_types = ["Academico", "Administrativo", "Estudiante", "Otros"]
        checkboxes = {}
        for user_type in user_types:
            user_layout = BoxLayout(orientation="horizontal")
            checkbox = CheckBox()
            label = Label(text=user_type)
            user_layout.add_widget(checkbox)
            user_layout.add_widget(label)
            checkboxes[user_type] = checkbox
            content.add_widget(user_layout)

        # Botones de acción
        add_button = Button(text="Añadir")
        cancel_button = Button(text="Cancelar")
        content.add_widget(add_button)
        content.add_widget(cancel_button)

        popup = Popup(title="Añadir cámara", content=content, size_hint=(None, None), size=(400, 500))
        add_button.bind(on_press=lambda x: self.confirm_add_camera(popup, ip_input.text, id_input.text, name_input.text, reduced_checkbox.active, checkboxes, latitude_input.text, longitude_input.text, mobile_checkbox.active))  # Pasar latitud y longitud
        cancel_button.bind(on_press=popup.dismiss)

        popup.open()

    def confirm_add_camera(self, popup, ip, id, name, reduced_capacity, checkboxes, latitude, longitude, estatica):
        camera_info = []
        try:
            with open('lib/camera_info.json', 'r') as f:
                camera_info = json.load(f)
            self.log_box.text += "Archivo lib/camera_info.json leído correctamente.\n"
        except FileNotFoundError:
            self.log_box.text += "Archivo lib/camera_info.json no encontrado, se creará uno nuevo.\n"

        # Convertir y validar el ID
        try:
            id_int = int(id)
        except ValueError:
            self.log_box.text += "Error: ID inválido.\n"
            return

        # Verificar si el ID ya existe
        for camera in camera_info:
            if camera['id'] == id_int:
                warning_popup = Popup(title="Error", content=Label(text="El ID de la cámara ya existe."), size_hint=(None, None), size=(300, 200))
                ok_button = Button(text="OK")
                ok_button.bind(on_press=warning_popup.dismiss)
                warning_popup.content.add_widget(ok_button)
                warning_popup.open()
                return

        selected_user_types = [key for key, checkbox in checkboxes.items() if checkbox.active]

        # Convertir y validar la latitud y longitud
        try:
            latitude_float = float(latitude.replace(',', '.'))
            longitude_float = float(longitude.replace(',', '.'))
        except ValueError:
            self.log_box.text += "Error: Latitud o longitud inválidas.\n"
            return

        camera_info.append({
            "id": id_int,
            "ip": ip,
            "name": name,
            "reduced_capacity": reduced_capacity,
            "user_types": selected_user_types,
            "latitude": latitude_float,
            "longitude": longitude_float,
            "score_threshold": 0.2,
            "nms_threshold": 0.6,
            "estatica": estatica
        })

        with open('lib/camera_info.json', 'w') as f:
            json.dump(camera_info, f)
        with open('lib/camera_info_temp.json', 'w') as f:
            json.dump(camera_info, f)
        self.log_box.text += f"Cámara añadida con ID {id_int}, IP {ip} y nombre {name}.\n"
        popup.dismiss()


    def delete_camera(self, instance):
        self.log_box.text += "Intentando eliminar una cámara.\n"
        
        content = BoxLayout(orientation="vertical")
        id_input = TextInput(hint_text="Ingrese el ID de la cámara a eliminar")
        content.add_widget(id_input)

        delete_button = Button(text="Eliminar")
        cancel_button = Button(text="Cancelar")

        content.add_widget(delete_button)
        content.add_widget(cancel_button)

        popup = Popup(title="Eliminar cámara", content=content, size_hint=(None, None), size=(400, 300))

        delete_button.bind(on_press=lambda x: self.confirm_delete_camera(popup, id_input.text))
        cancel_button.bind(on_press=popup.dismiss)
        
        popup.open()

    def confirm_delete_camera(self, popup, id):
        camera_info = []
        id = int(id)
        try:
            with open('lib/camera_info.json', 'r') as f:
                camera_info = json.load(f)
        except FileNotFoundError:
            self.log_box.text += "Archivo lib/camera_info.json no encontrado.\n"
            return

        if not camera_info:
            self.log_box.text += "No hay cámaras para eliminar.\n"
            return

        new_camera_info = [camera for camera in camera_info if camera['id'] != id]

        if len(new_camera_info) == len(camera_info):
            self.log_box.text += f"No se encontró la cámara con ID {id}.\n"
            return

        with open('lib/camera_info.json', 'w') as f:
            json.dump(new_camera_info, f)

        self.log_box.text += f"Cámara con ID {id} eliminada exitosamente.\n"
        popup.dismiss()


    def open_detections(self, instance):
        self.log_box.text += "Abriendo editor de detecciones.\n"
        subprocess.Popen([sys.executable, 'lib/PointSelector.py'])

    def open_umbral(self, instance):
        self.log_box.text += "Abriendo editor de umbral.\n"
        subprocess.Popen([sys.executable, 'diferencia_umbral.py'])

    def init_detection(self, instance):
        self.log_box.text += "Inicializando detecciones.\n"
        subprocess.Popen([sys.executable, 'ParkingDetector.py'])
        subprocess.Popen([sys.executable, 'diferencia.py'])

    def open_configuration(self, instance):
        self.log_box.text += "Abriendo editor de configuración.\n"
        subprocess.Popen([sys.executable, "lib/configuration.py"])

    def stop_detection(self, instance):
        self.log_box.text += "Intentando detener detecciones...\n"
        target_script_names = ["ParkingDetector.py", "diferencia.py"]

        for process in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            try:
                if "python" in process.info['name']:
                    cmdline = process.info['cmdline']
                    if cmdline and any(target_script_name in ' '.join(cmdline) for target_script_name in target_script_names):
                        psutil.Process(process.info['pid']).terminate()
                        self.log_box.text += "Detecciones detenidas exitosamente.\n"
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        self.log_box.text += "No se encontró el proceso ParkingDetector.py en ejecución.\n"

    def update_status(self):
        target_script_name = "ParkingDetector.py"
        is_running = False

        for process in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            try:
                if "python" in process.info['name']:
                    cmdline = process.info['cmdline']
                    if cmdline and target_script_name in ' '.join(cmdline):
                        is_running = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if is_running != self.last_known_status:
            if is_running:
                Clock.schedule_once(lambda dt: setattr(self.status_button, 'text', "Estado: Ejecutándose"))
                Clock.schedule_once(lambda dt: setattr(self.log_box, 'text', self.log_box.text + "ParkingDetector.py está ejecutándose.\n"))
            else:
                Clock.schedule_once(lambda dt: setattr(self.status_button, 'text', "Estado: Detenido"))
                Clock.schedule_once(lambda dt: setattr(self.log_box, 'text', self.log_box.text + "ParkingDetector.py está detenido.\n"))


            self.last_known_status = is_running

    def status_timer(self):
        while True:
            self.update_status()
            time.sleep(1)

    def update_camera_status(self):
        status_text = ""
        while True:
            try:
                with open('parking_status.json', 'r') as f:
                    data = json.load(f)
                temp_text = ""
                for cam_id, cam_data in data.items():
                    free_spaces = cam_data.get("free_spaces", "Desconocido")
                    total_spaces = cam_data.get("total_spaces")
                    pk_name = cam_data.get("pk_name")
                    temp_text += f"{pk_name}: Espacios: {free_spaces} / {total_spaces}\n"
                if temp_text:  # Solo actualizar status_text si temp_text no está vacío
                    status_text = temp_text
                self.camera_status_label.text = status_text
            except FileNotFoundError:
                self.camera_status_label.text = "Archivo parking_status.json no encontrado"
                print("Archivo parking_status.json no encontrado, reintentando en 1 segundo...")
            except json.decoder.JSONDecodeError:
                self.camera_status_label.text = "Archivo parking_status.json está vacío o contiene datos no válidos"
                print("Archivo parking_status.json está vacío o contiene datos no válidos, reintentando en 1 segundo...")
            time.sleep(1)


if __name__ == "__main__":

    MainApp().run()
