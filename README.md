# Instrucciones para la Configuración del Proyecto ParkingUdeC

## Descripción

Esta guía detalla los pasos necesarios para configurar y ejecutar la aplicación ParkingUdeC en tu entorno local. Incluye la instalación de dependencias, configuración de cuDNN, y la preparación del entorno de desarrollo.

## Requisitos Previos

- **Python 3.9**: Descárgalo e instálalo desde [python.org](https://www.python.org/downloads/).
- **Modelo Necesario**: Descarga el modelo desde el [siguiente enlace de Google Drive](URL_DEL_ENLACE).

## Paso 1: Instalar cuDNN

Para utilizar cuDNN en Windows, sigue estos pasos:

1. Asegúrate de que **CUDA 11.8** esté ya instalado en tu sistema.
2. Visita la página de [NVIDIA cuDNN](https://developer.nvidia.com/cudnn) (se requiere una cuenta NVIDIA y estar registrado en el programa NVIDIA Developer para descargar cuDNN).
3. Descarga la versión de cuDNN que sea compatible con tu versión instalada de CUDA.
4. Extrae el contenido del archivo ZIP descargado.
5. Copia los archivos del directorio descomprimido a los directorios correspondientes de CUDA:
    - `bin\cudnn*.dll` a `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.X\bin`
    - `include\cudnn*.h` a `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.X\include`
    - `lib\x64\cudnn*.lib` a `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.X\lib\x64`
    - Reemplaza `X.X` con tu versión de CUDA.

6. Agrega las rutas de cuDNN a las variables de entorno de Windows.
7. Verifica la instalación de cuDNN con `nvcc --version` en CMD o PowerShell.

## Paso 2: Configuración del Entorno de Desarrollo

### Crear un Entorno Virtual

Utiliza un entorno virtual para ejecutar tu aplicación:

```bash
python3.9 -m venv nombre_del_entorno
nombre_del_entorno\Scripts\activate
```
## Paso 3: Clonar el Repositorio y Configurar el Proyecto

Después de preparar tu entorno de desarrollo y activar tu entorno virtual, el siguiente paso es clonar el repositorio de tu proyecto y configurar las dependencias.

### Clonar el Repositorio de GitHub

Para obtener la última versión del código fuente, clona el repositorio de GitHub ejecutando el siguiente comando en tu terminal:

```bash
git clone https://github.com/AlecKeithC/Parkingudec.git
cd Parkingudec
```

### Instalar Dependencias del Proyecto

Dentro del directorio del proyecto y con el entorno virtual activado, instala las dependencias necesarias para ejecutar la aplicación. Esto se hace utilizando el archivo `requirements.txt` que debe estar en el directorio raíz del proyecto y contener una lista de todas las bibliotecas necesarias. Ejecuta el siguiente comando:
```bash
pip install -r requirements.txt
```

## Paso 4: Configuración de la Conexión a la Base de Datos

Para configurar la conexión a la base de datos, edita los parámetros en el archivo .env en el directorio raíz del proyecto. Asegúrate de especificar los detalles correctos para tu base de datos, incluyendo el host, puerto, nombre de usuario, contraseña y nombre de la base de datos.

### Mover modelo model6l6.onnx

Dejar en el directorio raíz del proyecto el modelo descargado.

## Iniciar main.py
