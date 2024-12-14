# config.py

import os

# Configuration du bot
API_ID = int(os.getenv("API_ID", "24817837"))  # Identifiant API
API_HASH = os.getenv("API_HASH", "acd9f0cc6beb08ce59383cf250052686")  # Clé secrète
BOT_TOKEN = os.getenv("BOT_TOKEN", "8154409136:AAHs9j-J0Uk4FPMNB0Lxy4CSyh9h8kjI0pk")  # Jeton du bot
ADMIN_IDS = [7428552084, 1740287480]