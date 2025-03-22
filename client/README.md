# Raspberry Client - Arrosage Automatique

Ce script Python permet à une Raspberry Pi de gérer un système d’arrosage automatique en se connectant à un serveur Flask (hébergé sur une instance AWS ou localement).  
Fonctionnalités :
- Capture d’image via caméra USB
- Lecture d’un capteur d’humidité
- Activation automatique ou manuelle d’une pompe
- Affichage LCD
- Communication avec un backend Flask

---

## Installation

### 1. Dépendances système

```bash
sudo apt update
sudo apt install i2c-tools python3.12-venv -y
```

---

### 2. Création et activation de l’environnement Python

```bash
python3 -m venv mpl_env
source mpl_env/bin/activate
```

---

### 3. Installation des dépendances Python

Active ton environnement virtuel, puis :

```bash
pip install RPi.GPIO
pip install requests
pip install opencv-python
pip install rpi-lcd
```

---

### 4. Accès GPIO pour le capteur d’humidité

#### Créer le groupe `gpio` et configurer les permissions :

```bash
sudo groupadd gpio
sudo chown root:gpio /dev/gpiomem
sudo chmod 660 /dev/gpiomem
```

#### Vérifier les permissions :

```bash
ls -l /dev/gpiomem
```

Tu dois obtenir :
```
crw-rw---- 1 root gpio ... /dev/gpiomem
```

#### Ajouter une règle udev :

Cette étape est nécessaire car l’environnement virtuel Python peut empêcher l’accès correct aux GPIO sans cette règle.

```bash
sudo nano /etc/udev/rules.d/99-gpio.rules
```

Ajoute la ligne suivante :

```
KERNEL=="gpiomem", GROUP="gpio", MODE="0660"
```

Recharge les règles :

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Ajoute ton utilisateur au groupe `gpio` :

```bash
sudo usermod -aG gpio $(whoami)
groups
```

Puis redémarre la Raspberry :

```bash
sudo reboot
```

---

### 5. Détection de caméra USB

Assure-toi qu'une caméra USB est bien branchée.  
Le script détectera automatiquement le bon port.

---

## Lancement du script

Rends le script exécutable :

```bash
chmod u+x client.py
```

Exécute le script depuis l’environnement virtuel :

```bash
source mpl_env/bin/activate
./client.py
```

---

## Utilisation avec `screen` (optionnel mais recommandé)

Pour éviter que le programme s’arrête en quittant la session SSH :

### 1.Installer screen

```bash
sudo apt install screen -y
```

### 2. Démarrer une session screen

```bash
screen -S raspberry_client
```

### 3. Lancer le script dans la session screen

```bash
source mpl_env/bin/activate
./client.py
```

### 4. Détacher la session (garder le script actif en fond)

Appuie sur :
```
CTRL + A, puis D
```

### 5. Revenir plus tard dans la session :

```bash
screen -r raspberry_client
```

### 6. Lister les sessions screen existantes

```bash
screen -ls
```

### 7. Quitter proprement

Dans screen :
- Arrête le script avec `CTRL + C`
- Quitte la session avec `exit`

---

## Notes

- Le script utilise une caméra USB, un capteur d’humidité branché sur le GPIO 21, un relai pour la pompe sur GPIO 14, et un écran LCD via I2C (`0x27`).
- Le serveur Flask doit être configuré et en ligne avec les bons endpoints.
