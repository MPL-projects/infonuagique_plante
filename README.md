# Projet Arrosage Automatique

Ce projet a pour objectif de créer un **système d’arrosage automatique intelligent**, contrôlé à distance, en combinant une **Raspberry Pi** (client physique avec capteur, pompe et caméra) et un **serveur Flask** (hébergé sur une instance AWS EC2) qui gère l'interface, les logs, et la logique d’arrosage.

---

## Vue d’ensemble du setup

![Photo du setup](setup.jpg)

---

## Structure du dépôt

Ce dépôt est organisé en deux dossiers principaux :

### 1. `client/` – Code embarqué sur la Raspberry Pi

Ce dossier contient :
- `client.py` : script principal qui gère la capture vidéo, la lecture du capteur d’humidité, le déclenchement de la pompe et la communication avec le serveur Flask.
- `README.md` : explication complète de l’installation sur la Raspberry Pi.

> Ce script s'exécute en continu sur la Raspberry Pi et communique avec le serveur.

---

### 2. `server/` – Serveur Flask sur AWS EC2

Contient :
- `app.py` : serveur Flask avec base SQLite et API.
- `templates/index.html` : interface web.
- `static/` : images envoyées par la caméra.
- `README.md` : guide d’installation sur EC2.

> Permet de contrôler l’arrosage, suivre l’humidité et consulter l’historique.

---

## Fonctionnalités principales

- Lecture d’un capteur d’humidité connecté à la Raspberry Pi
- Activation d’une pompe à eau manuellement, automatiquement ou par intervalle
- Envoi d’une image de la plante toutes les 0.5 secondes
- Affichage de l’état de la plante et de l’historique d’arrosage via une interface web
- Utilisation de `screen` pour garder les scripts actifs en arrière-plan sur EC2 et la Raspberry

---

## Technologies utilisées

- **Raspberry Pi 4**
- **Flask** (serveur web)
- **SQLite** (Flask-SQLAlchemy)
- **Requests** (communication HTTP)
- **HTML/CSS/JS** pour l’interface web
- **screen** pour la gestion des processus en fond

---

## Dossiers clés

```
.
├── client/
│   ├── client.py
│   └── README.md
├── server/
│   ├── app.py
│   ├── templates/
│   │   └── index.html
│   ├── static/
│   │   └── uploads/
│   │       └── video_frame.jpg
│   ├── instance/
│   │   └── watering.db
│   └── README.md
```

---

## À faire pour exécuter le projet

- Suivre le `README.md` dans `client/` pour installer le script sur la Raspberry Pi
- Suivre le `README.md` dans `server/` pour déployer le serveur sur AWS EC2
- Lancer `client.py` sur la Raspberry et `app.py` sur le serveur Flask
- Ouvrir un navigateur à l’adresse `http://<IP_PUBLIC_EC2>:5000` pour accéder à l’interface
