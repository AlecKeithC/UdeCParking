import json
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Point, Color, Line, Rectangle
from kivy.graphics.texture import Texture
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.uix.spinner import Spinner  # Importar Spinner
from kivy.uix.slider import Slider
from kivy.clock import Clock

import os


import cv2


Window.maximize()
Window.size
Window.resizable = True


# Asegurarse de que la carpeta 'Points' exista o crearla
if not os.path.exists('Points'):
    os.makedirs('Points')

class PointDrawer(Widget):
    def __init__(self, cam_id, camera_info_dict, **kwargs):
        super(PointDrawer, self).__init__(**kwargs)
        self.points = []
        self.cam_id = cam_id
        self.camera_info_dict = camera_info_dict  # Añadir esta línea
        self.deletion_mode = False
        self.load_points()
        self.point_counter = 0  # Añade un contador de puntos



    def undo_point(self):
        if self.points:
            self.points.pop()
            self.canvas.clear()
            self.draw_loaded_points()

    def delete_closest_point(self, touch):
        if not self.points:
            return
        # Accede a las coordenadas x, y a través de las claves del diccionario
        closest_point = min(self.points, key=lambda p: ((p['x'] * Window.size[0] / 640 - touch.x)**2 + (Window.size[1] - (p['y'] * Window.size[1] / 640) - touch.y)**2)**0.5)
        self.points.remove(closest_point)
        self.canvas.clear()
        self.draw_loaded_points()

    def show_create_file_popup(self):
        box = BoxLayout(orientation='vertical')
        label = Label(text='No se encuentra el archivo de puntos. ¿Desea crear uno nuevo?')
        box.add_widget(label)
        yes_button = Button(text='Sí')
        no_button = Button(text='No')
        yes_button.bind(on_press=self.create_new_file)
        no_button.bind(on_press=self.cancel_new_file)
        box.add_widget(yes_button)
        box.add_widget(no_button)
        self.popup = Popup(title='Archivo no encontrado', content=box, size_hint=(0.4, 0.4))
        self.popup.open()

    def create_new_file(self, instance):
        self.points = []
        self.popup.dismiss()
        self.camera_info_dict[str(self.cam_id)]['file'] = f'Points/AoT_{self.cam_id}.json'
        camera_info_list = list(self.camera_info_dict.values())
        with open('lib/camera_info.json', 'w') as f:
            json.dump(camera_info_list, f)

    def cancel_new_file(self, instance):
        self.popup.dismiss()
        self.points = []

    def load_points(self):
        try:
            with open(f'Points/AoT_{self.cam_id}.json', 'r') as f:
                self.points = json.load(f)
                self.draw_loaded_points()
        except FileNotFoundError:
            self.show_create_file_popup()


    def draw_loaded_points(self):
        with self.canvas:
            for i, point in enumerate(self.points):
                point['point_number'] = i + 1  # Actualiza el número del punto basado en su posición en la lista
                x, y = point['x'] * (Window.size[0] / 640), (Window.size[1] * 0.9) - (point['y'] * (Window.size[1] * 0.9) / 640)
                Color(1, 0, 0)
                Point(points=[x, y], pointsize=5)
                lbl = CoreLabel(text=str(point['point_number']), font_size=20)
                lbl.refresh()
                texture = lbl.texture
                Rectangle(pos=(x + 10, y - 10), size=(texture.width, texture.height), texture=texture)

    def on_touch_down(self, touch):
        if self.deletion_mode: 
            self.delete_closest_point(touch)  
        else:            
            with self.canvas:
                Color(1, 0, 0)  
                Point(points=[touch.x, touch.y], pointsize=5)  
                point_number = len(self.points) + 1  # Usa la longitud de la lista de puntos para el número del punto
                lbl = CoreLabel(text=str(point_number), font_size=20)  
                lbl.refresh()  
                texture = lbl.texture  
                Rectangle(pos=(touch.x, touch.y), size=(texture.width, texture.height), texture=texture)  
            scaled_x = int(touch.x * 640 / Window.size[0])  
            scaled_y = int((Window.size[1] * 0.9 - touch.y) * 640 / (Window.size[1] * 0.9))  
            point = {'point_number': point_number, 'x': scaled_x, 'y': scaled_y, 'score': 0.2}  
            self.points.append(point)  
            score_slider = Slider(min=0, max=0.99, value=0.6, step=0.01)  
            score_label = Label(text="{:.2f}".format(score_slider.value))  
            save_button = Button(text='Guardar')  
            box_layout = BoxLayout(orientation='vertical')  
            box_layout.add_widget(score_slider)  
            box_layout.add_widget(score_label)  
            box_layout.add_widget(save_button)  
            score_popup = Popup(title='Enter score', content=box_layout, size_hint=(None, None), size=(200, 200))  
            score_popup.open()  
            def on_press(instance):  
                point['score'] = score_slider.value  
                score_popup.dismiss()  
            save_button.bind(on_press=on_press)  
            def on_value(instance, value):  
                score_label.text = "{:.2f}".format(value)  
            score_slider.bind(value=on_value)  

    def toggle_deletion_mode(self, button):
        self.deletion_mode = not self.deletion_mode
        if self.deletion_mode:
            button.background_color = (1, 0, 0, 1)  # Cambiar a rojo cuando esté activado
        else:
            button.background_color = (0.1, 0.5, 0.6, 1)  # Cambiar de nuevo al color original cuando esté desactivado

    def update_points(self):
        with open(f'Points/AoT_{self.cam_id}.json', 'w') as f:
            json.dump(self.points, f)


class KivyCamera(Image):

    def __init__(self, capture, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self.capture = capture
        self.allow_stretch = True  # Permitir estiramiento
        self.keep_ratio = False  # Mantener la relación de aspecto
        self.update()

    def update(self):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.flip(frame,0)
            frame = cv2.resize(frame,(1280,720))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture.blit_buffer(rgb.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
            self.texture = texture
        self.capture.release()


import glob
import time
from PIL import ImageGrab

class CamApp(App):
    def build(self):
        self.layout = FloatLayout()
        self.load_camera_info()
        self.show_popup()
        return self.layout

    def save_screenshot(self):
        # Define el directorio donde quieres guardar la captura de pantalla
        desktop_path = os.path.join(os.path.expanduser("~"), "OneDrive", "Escritorio", "Tomorrow")
        directory = os.path.join(desktop_path, 'Points', 'Screenshots')
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Toma una captura de pantalla de toda la pantalla
        screenshot = ImageGrab.grab()
        # Supongamos que la barra superior tiene una altura de 50 píxeles y quieres recortarla
        top_bar_height = 150
        screen_width, screen_height = screenshot.size
        cropped_screenshot = screenshot.crop((0, top_bar_height, screen_width, screen_height - 50))        # Define la ruta de guardado y el nombre de la captura de pantalla
        screenshot_name = f'PointDrawer_{self.cam_id}.png'
        screenshot_path = os.path.join(directory, screenshot_name)

        # Guarda la captura de pantalla recortada
        cropped_screenshot.save(screenshot_path)
        print(f"Screenshot saved at {screenshot_path}")

    def load_camera_info(self):
        try:
            with open('lib/camera_info.json', 'r') as f:
                camera_info = json.load(f)

            # Asegurarse de que cada cámara tenga un archivo asociado
            for info in camera_info:
                if 'file' not in info:
                    info['file'] = f"Points/AoT_{info['id']}.json"  # Puedes cambiar esto para usar un nombre de archivo diferente

            # Actualizar el archivo lib/camera_info.json con la nueva información
            with open('lib/camera_info.json', 'w') as f:
                json.dump(camera_info, f)

            self.camera_info_dict = {str(info['id']): info for info in camera_info}
            self.camera_ids = [str(info['id']) for info in camera_info]
        except FileNotFoundError:
            print("No se encontró el archivo lib/camera_info.json.")

    def show_popup(self):
        # Leer el archivo JSON para obtener los IDs de cámara
        try:
            with open('lib/camera_info.json', 'r') as f:
                camera_info = json.load(f)
            camera_info_dict = {str(info['id']): info.get('file', 'ValorPorDefecto.json') for info in camera_info}
            camera_ids = [str(info['id']) for info in camera_info]

        except FileNotFoundError:
            print("No se encontró el archivo lib/camera_info.json.")
#            camera_ids = ['0', '1', '2', '3']  # Valores predeterminados en caso de error

        box = BoxLayout(orientation='vertical')
        label = Label(text='Por favor, seleccione el ID de la cámara:')
        self.spinner = Spinner(
            values=camera_ids,
            size_hint=(None, None),
            size=(100, 44),
            pos_hint={'center_x': .5}
        )
        box.add_widget(label)
        box.add_widget(self.spinner)
        my_button = Button(text='Aceptar', background_color=(0.1, 0.5, 0.6, 1))
        my_button.bind(on_press=self.on_button_press)
        box.add_widget(my_button)
        self.popup = Popup(title='Seleccionar ID de Cámara', content=box, size_hint=(0.4, 0.4))
        self.popup.open()

    def on_button_press(self, instance):
        try:
            selected_value = self.spinner.text  # Obtener el valor seleccionado del Spinner
            camera_config = self.camera_info_dict.get(str(selected_value), None)  # Usar self.camera_info_dict

            if camera_config:
                self.cam_id = camera_config.get('id', 0)
                ip_address = camera_config.get('ip', None)
            else:
                self.show_error_popup("Configuración de cámara no encontrada. Intente de nuevo.")
                return

            self.popup.dismiss()
            self.capture = cv2.VideoCapture(ip_address if ip_address else self.cam_id)
            self.my_camera = KivyCamera(capture=self.capture, size_hint=(1, .9), pos_hint={'x': 0, 'y': 0})
            self.point_drawer = PointDrawer(cam_id=self.cam_id, camera_info_dict=self.camera_info_dict, size_hint=(1, .9), pos_hint={'x': 0, 'y': 0})
            self.layout.add_widget(self.my_camera)
            self.layout.add_widget(self.point_drawer)
            
            # Añadir botones para guardar puntos, etc.
            button_layout = BoxLayout(size_hint=(1, .1), pos_hint={'x': 0, 'y': .9})
            
            save_button = Button(text='Guardar Puntos', size_hint=(.33, 1), background_color=(0.1, 0.5, 0.6, 1))
            save_button.bind(on_press=self.save_points)
            
            undo_button = Button(text='Deshacer punto', size_hint=(.33, 1), background_color=(0.1, 0.5, 0.6, 1))
            undo_button.bind(on_press=lambda x: self.point_drawer.undo_point())
            
            self.toggle_delete_mode_button = Button(text='Activar/Desactivar Modo de Eliminación', size_hint=(.34, 1), background_color=(0.1, 0.5, 0.6, 1))
            self.toggle_delete_mode_button.bind(on_press=lambda x: self.point_drawer.toggle_deletion_mode(self.toggle_delete_mode_button))
            
            button_layout.add_widget(save_button)
            button_layout.add_widget(undo_button)
            button_layout.add_widget(self.toggle_delete_mode_button)
            
            self.layout.add_widget(button_layout)
        except ValueError:
            self.show_error_popup("ID de cámara no válido. Intente de nuevo.")


#Crear una ventana flotante que muestre los scores para cada punto, que con el scroll pueda mover el número del punto y el score

    def save_points(self, instance):
        self.point_drawer.update_points()
        screenshot_path = self.save_screenshot()
        self.show_info_popup(f"Puntos y captura de pantalla guardados.\nImagen: {screenshot_path}")
        def close_app(instance):
            self.stop()

        # Programar el cierre de la aplicación después de que el Popup se cierre
        popup = Popup(title='Información', content=Label(text=f"Puntos guardados para la cámara {self.cam_id}.\nClickee fuera de este diálogo para salir."), size_hint=(0.2, 0.2))
        popup.bind(on_dismiss=close_app)
        popup.open()

    def show_error_popup(self, message):
        popup = Popup(title='Error', content=Label(text=message), size_hint=(0.4, 0.4))
        popup.open()

    def show_info_popup(self, message):
        popup = Popup(title='Información', content=Label(text=message), size_hint=(0.4, 0.4))
        popup.open()

    def on_stop(self):
        self.capture.release()

if __name__ == '__main__':
    CamApp().run()

#1.- Cargar los scores - Listo
#2.- Por cada punto, añadir un score
#3.- Crear mini ventana que muestre los scores para cada punto, permitiendo editarlos
#4.- Guardar los scores en un archivo JSON en Points/Scorepoints/SoT_{self.cam_id}.json
    