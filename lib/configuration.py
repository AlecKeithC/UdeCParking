import json
import os
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')

Window.maximize()

class PointItem(BoxLayout):
    """ Clase para representar y editar un punto. """
    def __init__(self, point_number, score, update_callback, **kwargs):
        super(PointItem, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 30  # Disminuye la altura para hacer las cajas de texto más pequeñas
        self.point_number_label = Label(text=f'Point {point_number}:', size_hint_x=0.4)
        self.score_input = TextInput(text=str(score), multiline=False, size_hint_x=0.6, font_size=14)
        self.score_input.bind(text=update_callback)
        self.add_widget(self.point_number_label)
        self.add_widget(self.score_input)

class PointsApp(App):
    def build(self):
        self.root = BoxLayout(orientation='horizontal')
        self.current_page = 0
        self.points_data = []
        self.page_size = 20
        self.selected_cam_id = None

        # Sección de la imagen ajustada para darle más espacio
        self.image_section = BoxLayout(orientation='vertical', size_hint=(0.8, 1))
        self.root.add_widget(self.image_section)

        # Widget AsyncImage para una mejor carga de imágenes.
        self.image_widget = AsyncImage(
            size_hint=(1, 0.9),
            keep_ratio=True,
            allow_stretch=True
        )
        self.image_section.add_widget(self.image_widget)

        # Sección de los puntos ajustada para hacerla más pequeña
        self.points_section = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        self.root.add_widget(self.points_section)

        # Contenedor para los puntos
        self.points_container = BoxLayout(orientation='vertical', size_hint=(1, None), height=Window.height)
        self.points_section.add_widget(self.points_container)

        # Botones de paginación
        self.pagination_buttons = BoxLayout(size_hint=(1, None), height=50)
        self.previous_button = Button(text='< Previa', on_press=self.load_previous_points)
        self.next_button = Button(text='Siguiente >', on_press=self.load_next_points)
        self.pagination_buttons.add_widget(self.previous_button)
        self.pagination_buttons.add_widget(self.next_button)
        self.points_section.add_widget(self.pagination_buttons)

        # Botón para guardar
        self.save_button = Button(text='Guardar Cambios', size_hint=(1, None), height=50, font_size=14)
        self.save_button.bind(on_press=self.save_data)
        self.points_section.add_widget(self.save_button)

        # Spinner para los IDs de las cámaras.
        self.spinner = Spinner(
            text='Select Camera ID',
            values=[],  # Se llenará con los IDs disponibles
            size_hint=(1, None),
            height=50,
            pos_hint={'center_x': 0.5}
        )
        self.spinner.bind(text=self.on_spinner_select)
        self.image_section.add_widget(self.spinner)

        return self.root


    def on_start(self):
        # Se llama cuando Kivy inicia la aplicación, después de construir la interfaz
        self.load_camera_ids()

    def load_camera_ids(self):
        file_names = os.listdir('Points')
        camera_ids = [re.search(r'AoT_(\d+).json', file_name).group(1)
                      for file_name in file_names if re.search(r'AoT_(\d+).json', file_name)]
        self.spinner.values = camera_ids

    def on_spinner_select(self, spinner, text):
        self.selected_cam_id = text
        self.load_image(text)
        self.load_json_data(text)
        self.current_page = 0
        self.update_points_display()

    def load_image(self, cam_id):
        image_path = f"Points/Screenshots/PointDrawer_{int(cam_id)}.png"
        if os.path.exists(image_path):
            self.image_widget.source = image_path
        else:
            self.image_widget.source = 'atlas://data/images/defaulttheme/button_pressed'  # Una imagen de placeholder.

    def load_json_data(self, cam_id):
        json_path = f"Points/AoT_{int(cam_id)}.json"
        if os.path.exists(json_path):
            with open(json_path, 'r') as file:
                self.points_data = json.load(file)
        else:
            self.points_data = []
        self.update_points_display()

    def update_points_display(self):
        # Limpiar el contenedor de puntos antes de añadir nuevos
        self.points_container.clear_widgets()
        start_index = self.current_page * self.page_size
        end_index = start_index + self.page_size
        for index, item in enumerate(self.points_data[start_index:end_index]):
            point_widget = PointItem(item['point_number'], item['score'], self.update_point_score(index + start_index))
            self.points_container.add_widget(point_widget)

    def load_next_points(self, instance):
        if (self.current_page + 1) * self.page_size < len(self.points_data):
            self.current_page += 1
            self.update_points_display()

    def load_previous_points(self, instance):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_points_display()

    def update_point_score(self, point_index):
        """ Función para crear un callback que actualice el score en self.points_data. """
        def update_score(instance, value):
            try:
                # Intentamos convertir el valor de la caja de texto a float y guardarlo
                self.points_data[point_index]['score'] = float(value)
            except ValueError:
                # Si hay un error en la conversión, no hacemos nada (o mostramos un mensaje de error)
                pass
        return update_score

    def save_data(self, instance):
        """ Guarda los cambios hechos en los puntos al archivo JSON correspondiente. """
        if self.selected_cam_id:
            json_path = f"Points/AoT_{int(self.selected_cam_id)}.json"
            if os.path.exists(json_path):
                with open(json_path, 'w') as file:
                    json.dump(self.points_data, file, indent=4)
                print(f"Data saved to {json_path}")
            else:
                print(f"Error: No se encontró el archivo JSON para el cam_id {self.selected_cam_id}")
        else:
            print("No camera ID selected. Cannot save data.")

if __name__ == '__main__':
    PointsApp().run()
