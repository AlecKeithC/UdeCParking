import json
import cv2
import numpy as np
import torch
from torchvision.ops import nms
import csv
import subprocess
import math
from datetime import datetime

past_angles_x = []
c_x = 0

def letterbox(im, new_shape=(1280, 1280), color=(114, 114, 114)):
    shape = im.shape[:2]
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
    dw /= 2
    dh /= 2
    im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return im, r, (dw, dh)

def load_parking_points(cam_id):
    try:
        with open(f'Points/AoT_{cam_id}.json', 'r') as f:
            data = json.load(f)
        points = [{'x': item['x']*2, 'y': item['y']*2, 'point_number': item['point_number']} for item in data if 'point_number' in item and 'x' in item and 'y' in item]
        scores = [item['score'] if 'score' in item else 0 for item in data]
        return points, scores
    except FileNotFoundError:
        return [], []


def draw_parking_points(frame, points, occupied_points):
    for point in points:
        px = point['x']
        py = point['y']
        score = point['score'] if 'score' in point else 0  # Use a default score of 0 if 'score' is not in the point dictionary
        color = (0, 255, 0)
        if tuple([px, py]) in occupied_points:  # Check if the point is in occupied_points
            color = (0, 0, 255)
        cv2.circle(frame, (px, py), 5, color, 4)
        #cv2.putText(frame, f"{score:.2f}", (px, py - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)  # Display the score above the point
    return frame

def apply_nms(boxes, scores, threshold=0.4):
    """
    Aplica Non-Maximum Suppression (NMS) a las cajas de detección.

    Parámetros:
    - boxes (list): Lista de cajas de detección [x1, y1, x2, y2]
    - scores (list): Lista de puntuaciones para cada caja
    - threshold (float): Umbral IoU para NMS

    Retorna:
    - selected_boxes (list): Lista de cajas seleccionadas después de NMS
    """
    if len(boxes) > 0:
        boxes_tensor = torch.tensor(boxes, dtype=torch.float32)
        scores_tensor = torch.tensor(scores, dtype=torch.float32)
        indices = nms(boxes_tensor, scores_tensor, threshold)
        selected_boxes = [boxes[i] for i in indices]
        return selected_boxes
    else:
        return []

def apply_nms2(current_boxes, scores, threshold=0.4):
    """
    Aplica Non-Maximum Suppression (NMS) a las cajas de detección.

    Parámetros:
    - current_boxes (list of tuples): Lista de tuplas que contienen cajas, cls_ids y scores [(box, cls_id, score), ...]
    - scores (list): Lista de puntuaciones para cada caja
    - threshold (float): Umbral IoU para NMS

    Retorna:
    - final_boxes (list of tuples): Lista de tuplas que contienen las cajas seleccionadas, cls_ids y scores [(box, cls_id, score), ...]
    """
    if len(current_boxes) > 0:
        # Separamos las coordenadas, los cls_ids y los scores
        boxes = [box for box, cls_id, score in current_boxes]
        
        # Convertimos a tensores
        boxes_tensor = torch.tensor(boxes, dtype=torch.float32)
        scores_tensor = torch.tensor(scores, dtype=torch.float32)
        
        # Aplicamos NMS
        indices = nms(boxes_tensor, scores_tensor, threshold)
        
        # Obtenemos las cajas finales, sus respectivos cls_ids y scores
        final_boxes = [current_boxes[i] for i in indices.tolist()]
        
        return final_boxes
    else:
        return []
    
#Dibujar las últimas cajas detectadas
# for x1, y1, x2, y2 in last_boxes:
#     cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
def adjust_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)])
    return cv2.LUT(image.astype(np.uint8), table.astype(np.uint8))

def clip_white(image, threshold=240):
    return np.clip(image, 0, threshold)

def adjust_contrast_brightness(image, alpha=1.0, beta=0.0):
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

def log_inference_time_to_csv(cam_id, inference_time):
    with open("C:\\Users\\aleci\\OneDrive\\Escritorio\\DataAnalysis\\output16.csv", 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter='\t')
        csvwriter.writerow([cam_id, inference_time])


def get_gpu_utilization():
    try:
        smi_output = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]).decode()
        return float(smi_output.strip())
    except Exception as e:
        print(f"Error while fetching GPU utilization: {e}")
        return None

def filter_contained_boxes(boxes):
    """
    Filtra las cajas que están completamente contenidas dentro de otras.

    :param boxes: Lista de cajas, donde cada caja es una tupla ([x1, y1, x2, y2], cls_id, score).
    :return: Lista de cajas filtradas.
    """
    filtered_boxes = []
    for boxA in boxes:
        x1A, y1A, x2A, y2A = boxA[0]
        is_contained = False
        for boxB in boxes:
            if boxA == boxB:
                continue  # No comparar la caja consigo misma
            x1B, y1B, x2B, y2B = boxB[0]
            if x1A >= x1B and x2A <= x2B and y1A >= y1B and y2A <= y2B:
                # Si todas las esquinas de boxA están dentro de boxB
                is_contained = True
                break
        if not is_contained:
            filtered_boxes.append(boxA)

    return filtered_boxes
