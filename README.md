# Parkingudec

¡Bienvenido al software de monitoreo!

## Requisitos previos

Requiere Python 3.9. Puedes descargarlo e instalarlo desde [python.org](https://www.python.org/downloads/).

Para obtener el modelo necesario, visita el siguiente enlace de [Google Drive](https://drive.google.com/file/d/1QlHycASXWvXVHzgxVX728efxljNvgNUl/view?usp=sharing).

## Paso 1: Instalar cuDNN

Para utilizar cuDNN en Windows, sigue estos pasos:

1. Asegúrate de que CUDA esté ya instalado en tu sistema. cuDNN es una extensión de CUDA y necesita que CUDA esté instalado.

2. Visita la página de [NVIDIA cuDNN](https://developer.nvidia.com/cudnn) (es necesario tener una cuenta NVIDIA y estar registrado en el programa NVIDIA Developer para descargar cuDNN).

3. Descarga la versión de cuDNN que sea compatible con tu versión instalada de CUDA.

4. Una vez descargado el archivo, extrae el contenido del archivo ZIP.

5. Copia los siguientes archivos del directorio descomprimido a los directorios correspondientes de CUDA:

   - `bin\cudnn*.dll` a `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.X\bin`
   - `include\cudnn*.h` a `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.X\include`
   - `lib\x64\cudnn*.lib` a `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.X\lib\x64`

   Reemplaza `X.X` con tu versión de CUDA.

6. Agrega las rutas de cuDNN a las variables de entorno de Windows para que las aplicaciones puedan encontrar las bibliotecas cuDNN:

   - Haz clic derecho en 'Este PC' o 'Mi PC' en el escritorio o en el Explorador de Windows y selecciona 'Propiedades'.
   - Haz clic en 'Configuración avanzada del sistema'.
   - En la pestaña 'Opciones avanzadas', haz clic en 'Variables de entorno'.
   - En 'Variables del sistema', busca y selecciona la variable `Path`, luego haz clic en 'Editar'.
   - Agrega las rutas de las carpetas `bin` y `lib\x64` de CUDA donde copiaste los archivos de cuDNN.
   - Haz clic en 'Aceptar' para cerrar todas las ventanas de diálogo.
     
7. Para asegurarte de que cuDNN está correctamente instalado y reconocido por tu sistema, sigue estos pasos:

	- Abre el Símbolo del sistema (cmd) o PowerShell en Windows.

	- Ejecuta el siguiente comando para verificar la versión de CUDA (esto asume que has agregado CUDA a tus variables de entorno como se mencionó anteriormente):

   ```bash
   nvcc --version

## Paso 2: Configuración del Entorno de Desarrollo

Una vez que tengas Python 3.9 y cuDNN instalados, el siguiente paso es configurar tu entorno de desarrollo.

### Crear un Entorno Virtual

Es recomendable utilizar un entorno virtual para ejecutar tu aplicación. Esto ayuda a gestionar las dependencias y asegurar que tu proyecto no afecte o sea afectado por otros proyectos en tu sistema.

Para crear un entorno virtual, sigue estos pasos:

1. Abre una terminal en tu sistema.

2. Navega al directorio donde deseas almacenar tu proyecto y crea un nuevo entorno virtual con el siguiente comando:

   ```bash
   python3.9 -m venv nombre_del_entorno
   nombre_del_entorno\Scripts\activate (para activarlo)

## Paso 3: Clonar el Repositorio y Configurar el Proyecto

Después de preparar tu entorno de desarrollo y activar tu entorno virtual, el siguiente paso es clonar el repositorio de tu proyecto y configurar las dependencias.

### Clonar el Repositorio de GitHub

Para obtener la última versión del código fuente, clona el repositorio de GitHub ejecutando el siguiente comando en tu terminal:


	git clone https://github.com/nachoklp/Parkingudec.git
	cd Parkingudec
 
 ### Instalar Dependencias del Proyecto

Dentro del directorio del proyecto y con el entorno virtual activado, instala las dependencias necesarias para ejecutar la aplicación. Esto se hace utilizando el archivo `requirements.txt` que debe estar en el directorio raíz del proyecto y contener una lista de todas las bibliotecas necesarias. Ejecuta el siguiente comando:

pip install -r requirements.txt

 ### Mover modelo yolov6m6x.onnx

 Dejar en el directorio raíz del proyecto el modelo descargado.

## Iniciar main.py
