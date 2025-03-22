#!/home/mpl/mpl_env/bin/python3
import cv2
import time
import requests
import os
import threading
import RPi.GPIO as GPIO
from threading import Lock
from rpi_lcd import LCD

# ----------------------------
# Configuration du serveur
# ----------------------------
# SERVER_URL = "http://192.168.0.166:5000"
SERVER_URL = "http://13.59.238.115:5000" # IP du server sur l'intance AWS

# ----------------------------
# Configuration des endpoints
# ----------------------------
CAMERA_UPLOAD_ENDPOINT = SERVER_URL + "/upload_video_frame"
SENSOR_UPDATE_ENDPOINT = SERVER_URL + "/update_sensor"
PUMP_STATE_ENDPOINT = SERVER_URL + "/get_pump_state"
PUMP_MODE_ENDPOINT = SERVER_URL + "/get_pump_mode"
LCD_ENDPOINT = SERVER_URL + "/get_lcd"
LOG_PUMP = SERVER_URL + "/manual_pump"

# ----------------------------
# Définition des intervalles de mise à jour (en secondes)
# ----------------------------
CAMERA_INTERVAL = 0.5  # Capture de la caméra toutes les secondes
SENSOR_INTERVAL = 2  # Vérification du capteur toutes les 2 secondes
PUMP_POLL_INTERVAL = 5  # Vérification de l'état de la pompe toutes les 5 secondes
PUMP_INTERVAL_AUTOM = 30  # Intervalle d'activation de la pompe en mode automatique
LCD_POLL_INTERVAL = 2  # Mise à jour de l'affichage LCD toutes les 2 secondes
TIME_ACTIVATION_PUMP = 1  # Temps d'activation de la pompe

# ----------------------------
# Configuration des broches GPIO
# ----------------------------
SENSOR_PIN = 21  # Capteur d'humidité
PUMP_PIN = 14  # Pompe (relai)

gpio_lock = Lock()  # Configuration GPIO
GPIO.setwarnings(False) 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)

# ----------------------------
# Initialisation du LCD local
# ----------------------------
lcd = LCD(address=0x27)

# ----------------------------
# Configuration des variables globales
# ----------------------------
global humidity
camera_active = True  # Ajout de cette ligne pour éviter le NameError

# ----------------------------
# Détection de la caméra
# ----------------------------
# Recherche une caméra connectée au système
def detect_camera():
    for i in range(32):  # Tester plusieurs indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Caméra détectée sur /dev/video{i}")
            cap.release()
            return i
    print("Aucune caméra détectée.")
    return None


# ----------------------------
# Tâche caméra : capture et envoi des frames et les envoie au serveur
# ----------------------------
def camera_task():
    global camera_active
    camera_index = detect_camera()
    if camera_index is None:
        return
    
    cap = cv2.VideoCapture(camera_index)
    failed_attempts = 0

    while True:
        if not camera_active:
            cap.release()
            time.sleep(1)
            continue

        if not cap.isOpened():
            print("Erreur : caméra non accessible. Tentative de reconnexion...")
            failed_attempts += 1
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(camera_index)
            if failed_attempts >= 5:
                print("Échec répété de la caméra. Redémarrage complet...")
                cap.release()
                time.sleep(5)
                failed_attempts = 0
            continue

        ret, frame = cap.read()
        if not ret:
            print("Erreur lors de la capture de l'image.")
            failed_attempts += 1
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(camera_index)
            continue

        failed_attempts = 0
        tmp_filename = "temp_frame.jpg"
        cv2.imwrite(tmp_filename, frame)

        with open(tmp_filename, 'rb') as f:
            files = {'frame': f}
            try:
                response = requests.post(CAMERA_UPLOAD_ENDPOINT, files=files)
                if response.status_code != 200:
                    print("Erreur serveur (cam):", response.status_code)
            except Exception as e:
                print("Erreur lors de l'envoi de la frame :", e)

        os.remove(tmp_filename)
        time.sleep(CAMERA_INTERVAL)

    cap.release()

# ----------------------------
# Tâche capteur : lecture et envoi de l'état du capteur d'humidité
# ----------------------------
def sensor_task():
    while True:
        global humidity
        sensor_state = GPIO.input(SENSOR_PIN)
        humidity = "HIGH" if sensor_state == GPIO.LOW else "LOW"
        data = {"humidity": humidity}
        try:
            response = requests.post(SENSOR_UPDATE_ENDPOINT, json=data)
            if response.status_code == 200:
                print(f"Capteur: Humidité = {humidity}")
            else:
                print("Erreur lors de l'envoi du capteur :", response.status_code)
        except Exception as e:
            print("Erreur lors de l'envoi des données du capteur :", e)
        time.sleep(SENSOR_INTERVAL)

# ----------------------------
# Tâche pompe on : active la pompe et envoie la commande au serveur
# ----------------------------
def pump_on(mode):
    global camera_active  
    with gpio_lock:  
        if not camera_active:
            print("La caméra est déjà arrêtée, pas besoin de la couper à nouveau.")
        else:
            print("Arrêt temporaire de la caméra pour éviter les conflits avec la pompe...")
            camera_active = False  # Désactive temporairement la capture

        time.sleep(1)  # Pause pour s'assurer que la caméra est bien arrêtée

        print("Activation de la pompe...")
        GPIO.output(PUMP_PIN, GPIO.HIGH)  # Active la pompe
        time.sleep(TIME_ACTIVATION_PUMP)  # Pompe activée
        GPIO.output(PUMP_PIN, GPIO.LOW)  # Désactive la pompe
        print("Pompe désactivée.")

        payload = {"mode": mode}
        requests.post(LOG_PUMP, json=payload)
        print(f"Log envoyé: Mode = {mode}")

        time.sleep(1)  # Pause avant de réactiver la caméra
        camera_active = True  # Réactive la capture

# ----------------------------
# Tâche boutton arosser : vérifie régulièrement l'état de la pompe et active si nécessaire
# ----------------------------
def pump_task():
    while True:
        try:
            response = requests.get(PUMP_STATE_ENDPOINT)
            if response.status_code == 200:
                data = response.json()
                if data.get("pump", "OFF").lower() == "water":
                    print("Commande d'arrosage détectée : Activation de la pompe")
                    pump_on("manuel")
            else:
                print("Erreur lors de la récupération de l'état de la pompe :", response.status_code)
        except Exception as e:
            print("Erreur lors du polling du pump state:", e)
        time.sleep(PUMP_POLL_INTERVAL)



# ----------------------------
# Tâche gestion mode de la pompe
# ----------------------------
def pump_mode_task():
    while True:
        try:
            response = requests.get(PUMP_MODE_ENDPOINT)
            if response.status_code == 200:
                data = response.json()
                mode = data.get("mode", "Non défini")
                interval = data.get("interval", "")
                print(f"Mode de pompe : {mode} - Intervalle : {interval} sec")
                if mode == "manuel":
                    print("MANUEL")
                    pass
                if mode == "automatique":
                    print("AUTOMATIQUE")
                    if humidity == "LOW" :
                        pump_on("automatique")
                        time.sleep(PUMP_INTERVAL_AUTOM)
                if mode == "timer" :
                    print("TIMER")
                    time.sleep(interval)
                    pump_on("timer")
            else:
                print("Erreur lors de la récupération du mode de pompe :", response.status_code)
        except Exception as e:
            print("Erreur lors du polling du mode de pompe:", e)
        time.sleep(PUMP_POLL_INTERVAL)

# ----------------------------
# Tâche LCD : récupération et mise à jour du message LCD local
# ----------------------------
def lcd_task():
    while True:
        try:
            response = requests.get(LCD_ENDPOINT)
            if response.status_code == 200:
                data = response.json()
                line1 = data.get("line1", "")
                line2 = data.get("line2", "")
                lcd.clear()
                lcd.text(line1, 1)
                lcd.text(line2, 2)
            else:
                print("Erreur LCD polling:", response.status_code)
        except Exception as e:
            print("Erreur lors de la mise à jour du LCD:", e)
        time.sleep(LCD_POLL_INTERVAL)

# ----------------------------
# Fonction principale : démarrage des threads
# ----------------------------
def main():
    threads = []
    threads.append(threading.Thread(target=camera_task, daemon=True))
    threads.append(threading.Thread(target=sensor_task, daemon=True))
    threads.append(threading.Thread(target=pump_task, daemon=True))
    threads.append(threading.Thread(target=pump_mode_task, daemon=True))
    threads.append(threading.Thread(target=lcd_task, daemon=True))
    
    for t in threads:
        t.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt de client.py")
    finally:
        lcd.clear()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
