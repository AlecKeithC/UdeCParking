from datetime import datetime
import psycopg2
import time
from dotenv import load_dotenv
import os

load_dotenv()
DB_IP= os.getenv("DB_IP")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_last_update():
    while True:
        try:
            connection = psycopg2.connect(
                host=DB_IP,
                database=DB_NAME,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD
            )
            cursor = connection.cursor()
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_query = """UPDATE parking SET last_update = %s WHERE estatica = FALSE;"""
            cursor.execute(update_query, (current_timestamp,))
            connection.commit()
        except Exception as e:
            print("Error al actualizar la base de datos:", e)
        finally:
            if connection:
                if not connection.closed:
                    connection.close()

        time.sleep(5)

def update_database(cam_id, free_spaces, total_spaces, pk_name, latitude, longitude, user_types, reduced_capacity, active, last_update, estatica):
    try:
        connection = psycopg2.connect(
            host=DB_IP,
            database=DB_NAME,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
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