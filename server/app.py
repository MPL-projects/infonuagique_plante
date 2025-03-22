#!/usr/bin/python3
from flask import Flask, request, jsonify, render_template, redirect, url_for
import time
import os
import csv
from flask_sqlalchemy import SQLAlchemy

# ----------------------------
# Initialisation de l'application Flask
# ----------------------------
app = Flask(__name__)

# ----------------------------
# Configuration de la base de données SQLite
# ----------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///watering.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ----------------------------
# Définition du modèle de la base de données
# ----------------------------
class WateringLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<WateringLog {self.timestamp} - {self.action}>'
    
# Path vers la base de données
CSV_FILE = "mnt/watering_log.csv"

# Fonction pour enregistrer un arrosage dans le fichier CSV
def log_watering(action):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    new_log = WateringLog(timestamp=timestamp, action=action)
    db.session.add(new_log)
    db.session.commit()
    print(f"Ajout à l'historique SQL: {timestamp} - {action}")

# ----------------------------
# Configuration des variables globales
# ----------------------------
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

plant_name = "Chlorophyton chevelu"
plant_name = "  Spider plant"
humidity_status = "UNKNOWN"   # "HIGH" ou "LOW"
last_image_filename = None
watering_logs = []  # Exemple : [{"timestamp": 1670000000, "command": "water"}, ...]
pump_command = "OFF"  # "water" pour activer la pompe, sinon "OFF"
pump_mode = "manuel"  # Modes possibles : "manuel", "automatique", "timer"
pump_timer_interval = 300  # Intervalle en secondes pour le mode timer (par défaut 5 minutes)

# Message pour le "LCD virtuel" affiché sur l'interface
message = {
    "line1": plant_name,       # Nom de la plante
    "line2": humidity_status     # Niveau d'humidité 
}


# ----------------------------
# Filtre personnalisé pour formater une date/heure
# ----------------------------

# Route pour afficher la page d'accueil
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    return time.strftime(format, time.localtime(value))

# ----------------------------
# Routes Flask
# ----------------------------

# Page principale
@app.route("/")
def index():
    filename = "video_frame.jpg"
    video_frame = filename if os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], filename)) else None
    timestamp = int(time.time())
    return render_template("index.html", 
                           plant_name=plant_name, 
                           humidity_status=humidity_status, 
                           last_image=last_image_filename,
                           watering_logs=watering_logs,
                           video_frame=video_frame, 
                           timestamp=timestamp,
                           message=message,
                           pump_mode=pump_mode,
                           pump_timer_interval=pump_timer_interval)

# Endpoint pour mettre à jour l'état du capteur d'humidité
@app.route("/update_sensor", methods=["POST"])
def update_sensor():
    global humidity_status, message, pump_mode
    data = request.get_json() or request.form
    humidity_status = data.get("humidity", "UNKNOWN")
    print(f"[{time.ctime()}] Mise à jour du capteur: Humidité = {humidity_status}")
    return jsonify({"status": "OK", "humidity": humidity_status})

# Endpoint pour recevoir la frame de la caméra
@app.route("/upload_video_frame", methods=["POST"])
def upload_video_frame():
    global last_image_filename
    if 'frame' not in request.files:
        return "Aucune frame transmise", 400
    file = request.files['frame']
    if file.filename == "":
        return "Aucun fichier sélectionné", 400
    filename = "video_frame.jpg"  # On écrase toujours le même fichier
    upload_folder = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, filename)
    file.save(save_path)
    last_image_filename = filename
    print(f"[{time.ctime()}] Frame reçue: {filename}")
    return "Frame reçue", 200


# Active manuellement la pompe et enregistre l'action
@app.route("/manual_pump", methods=["POST"])
def manual_pump():
    global pump_command, pump_mode
    pump_command = "water"
    data = request.get_json() or {}
    received_mode = data.get("mode", pump_mode)
    log_watering(f"Arrosage {received_mode}")
    print(f"[{time.ctime()}] Commande d'arrosage reçue")

    time.sleep(5)
    pump_command = "OFF"
    print("Pump_command réinitialisé à OFF après l'activation.")
    return jsonify({"status": "OK", "pump": pump_command})

# Récupère l'historique des arrosages depuis la base de données
@app.route("/get_watering_logs", methods=["GET"])
def get_watering_logs():
    logs = WateringLog.query.all()
    return jsonify({"logs": [{"timestamp": log.timestamp, "action": log.action} for log in logs]})


# Endpoint pour que le client récupère la commande de pompe
@app.route("/get_pump_state", methods=["GET"])
def get_pump_state():
    global pump_command
    current_command = pump_command
    pump_command = "OFF"
    return jsonify({"pump": current_command})

# Endpoint pour définir le mode de la pompe
@app.route("/set_pump_mode", methods=["POST"])
def set_pump_mode():
    global pump_mode, pump_timer_interval
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Données invalides"}), 400
    
    pump_mode = data.get("mode", "manuel")
    pump_timer_interval = int(data.get("interval", 300))

    print(f"[{time.ctime()}] Nouveau mode: {pump_mode}, Intervalle: {pump_timer_interval}s")
    return jsonify({"status": "OK", "mode": pump_mode, "interval": pump_timer_interval})

# Endpoint pour récupérer le mode de pompe
@app.route("/get_pump_mode", methods=["GET"])
def get_pump_mode():
    return jsonify({"mode": pump_mode, "interval": pump_timer_interval})

# Endpoint pour récupérer le message LCD (pour le client)
@app.route("/get_lcd", methods=["GET"])
def get_lcd():
    global message
    if pump_mode == "manuel":
        if humidity_status == "HIGH":
            message["line2"] = f"Mode: M | Hum: +" 
        else :
            message["line2"] = f"Mode: M | Hum: -" 

    if pump_mode == "automatique":
        if humidity_status == "HIGH":
            message["line2"] = f"Mode: A | Hum: +" 
        else :
            message["line2"] = f"Mode: A | Hum: -" 
    if pump_mode == "timer" :
        if humidity_status == "HIGH":
            message["line2"] = f"Mode: T | Hum: +" 
        else :
            message["line2"] = f"Mode: T | Hum: -" 
    return jsonify(message)

# Endpoint optionnel pour obtenir le niveau d'humidité en texte brut
@app.route("/get_humidity_txt", methods=["GET"])
def get_humidity_txt():
    return f"{humidity_status}", 200, {'Content-Type': 'text/plain'}

# Met à jour les informations affichées sur l'écran LCD
@app.route("/get_mode_txt", methods=["GET"])
def get_mode_txt():
    global pump_mode
    return f"{pump_mode}", 200, {'Content-Type': 'text/plain'}

# ----------------------------
# Lancement de l'application Flask
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
