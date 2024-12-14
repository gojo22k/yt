# bot.py

import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_IDS
from yt_dlp import YoutubeDL
from uuid import uuid4  # Génération d'identifiants uniques
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Initialisation du bot
bot = Client("youtube_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialisation de la base de données SQLite
conn = sqlite3.connect("users.db", timeout=10, check_same_thread=False)  # Ajout d'un délai pour éviter les verrous
cursor = conn.cursor()

# Création de la table pour stocker les utilisateurs
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Liste des callbacks
CALLBACK_DATA = {}

# Commande /start
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user = message.from_user
    user_link = f"[{user.first_name}](tg://user?id={user.id})"

    # Ajouter l'utilisateur à la base de données
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()

    # Message de bienvenue
    await message.reply_photo(
        "https://envs.sh/YOE.jpg",
        caption=f"Salut {user_link} ! 🎉 Je suis un bot de téléchargement de vidéos YouTube.\n\n"
                "Envoyez-moi le lien de la vidéo YouTube que vous souhaitez télécharger ! 📥\n\n"
                "😁😁😁😁😁"
    )

# Commande /broadcast (administrateurs uniquement)
@bot.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS) & filters.reply)
async def broadcast_message(client, message):
    # Récupérer tous les utilisateurs enregistrés dans la base de données
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    if not users:
        await message.reply("Aucun utilisateur enregistré pour recevoir le message.")
        return

    target_message = message.reply_to_message
    failed = 0

    # Envoyer le message à chaque utilisateur
    for user in users:
        user_id = user[0]
        try:
            await target_message.copy(chat_id=user_id)
        except Exception as e:
            failed += 1
            print(f"Erreur pour {user_id}: {e}")

    await message.reply(f"Message diffusé avec succès à {len(users) - failed} utilisateurs. Échecs : {failed}.")

# Commande /id
@bot.on_message(filters.command("id") & filters.private)
async def get_user_info(client, message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "Inconnu"

    # Message sans parse_mode
    await message.reply(
        f"➲ Nom : {user.last_name or 'Inconnu'}\n"
        f"➲ Prénom : {user.first_name}\n"
        f"➲ Nom d'utilisateur : {username}\n"
        f"➲ Telegram ID : {user.id}\n"
    )

# Gestion des liens YouTube
@bot.on_message(filters.regex(r"https?://(www\.)?(youtube\.com|youtu\.be)/.+") & filters.private)
async def handle_youtube_link(client, message):
    url = message.text.strip()

    # Ajouter l'utilisateur à la base de données
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()

    # Générer un identifiant unique pour les boutons
    callback_id_480p = str(uuid4())
    callback_id_720p = str(uuid4())
    callback_id_mp3 = str(uuid4())

    # Enregistrer les données dans le dictionnaire global
    CALLBACK_DATA[callback_id_480p] = {"format": "480p", "url": url}
    CALLBACK_DATA[callback_id_720p] = {"format": "720p", "url": url}
    CALLBACK_DATA[callback_id_mp3] = {"format": "mp3", "url": url}

    # Créer les boutons
    await message.reply_photo(
        "https://envs.sh/YOQ.jpg",
        caption="Choisissez le format à laquelle vous voudriez avoir vos vidéos.\n\n"
                f"🔗 {url}\n\nPatientez quelques minutes après avoir choisi le format.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥480p", callback_data=callback_id_480p),
             InlineKeyboardButton("🏮720p", callback_data=callback_id_720p)],
            [InlineKeyboardButton("🎧MP3", callback_data=callback_id_mp3),
             InlineKeyboardButton("Contact Support", url="https://kingcey.t.me")]
        ])
    )

# Téléchargement des vidéos YouTube
@bot.on_callback_query(filters.regex(r".*"))
async def download_video(client, callback_query):
    callback_id = callback_query.data

    # Vérification des données du bouton
    if callback_id not in CALLBACK_DATA:
        await callback_query.message.edit("Données du bouton introuvables ou expirées.")
        return

    data = CALLBACK_DATA[callback_id]
    format = data["format"]
    url = data["url"]

    await callback_query.message.edit("Téléchargement en cours, veuillez patienter...")

    # Options pour yt-dlp
    ydl_opts = {
        "format": "bestaudio/best" if format == "mp3" else f"bestvideo[height<={format[:-1]}]+bestaudio",
        "outtmpl": f"{callback_query.from_user.id}_%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4" if format in ["480p", "720p"] else "mp3"
    }

    try:
        # Téléchargement de la vidéo
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            video_title = info.get("title", "Vidéo")

        # Envoi de la vidéo téléchargée
        await callback_query.message.reply_document(
            file_path,
            caption=f"Voici votre vidéo YouTube : **{video_title}**",
            quote=True
        )
        os.remove(file_path)  # Supprimer le fichier après l'envoi
        await callback_query.message.edit("Téléchargement terminé et fichier envoyé.")

    except Exception as e:
        await callback_query.message.edit(f"Erreur lors du téléchargement ou de l'envoi : {e}")
        print(f"[Erreur] Téléchargement échoué : {e}")

# Serveur HTTP minimal pour répondre aux vérifications de santé
def run_http_server():
    server = HTTPServer(('0.0.0.0', 8000), SimpleHTTPRequestHandler)
    print("HTTP server running on port 8000 for health checks...")
    server.serve_forever()

# Lancement du serveur HTTP dans un thread séparé
http_thread = threading.Thread(target=run_http_server, daemon=True)
http_thread.start()

# Lancement du bot Telegram
if __name__ == "__main__":
    bot.run()
