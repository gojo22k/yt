# bot.py

import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_IDS
from yt_dlp import YoutubeDL
from uuid import uuid4

# Initialisation du bot
bot = Client("youtube_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialisation de la base de données SQLite
conn = sqlite3.connect("users.db", timeout=10, check_same_thread=False)
cursor = conn.cursor()

# Création de la table pour stocker les utilisateurs
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

CALLBACK_DATA = {}

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user = message.from_user
    user_link = f"[{user.first_name}](tg://user?id={user.id})"

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()

    await message.reply_photo(
        "https://envs.sh/YOE.jpg",
        caption=f"Salut {user_link} ! 🎉 Je suis un bot de téléchargement de vidéos YouTube.\n\n"
                "Envoyez-moi le lien de la vidéo YouTube que vous souhaitez télécharger ! 📥\n\n"
                "😁😁😁😁😁"
    )

@bot.on_callback_query(filters.regex(r".*"))
async def download_video(client, callback_query):
    callback_id = callback_query.data

    if callback_id not in CALLBACK_DATA:
        await callback_query.message.edit("Données du bouton introuvables ou expirées.")
        return

    data = CALLBACK_DATA[callback_id]
    format = data["format"]
    url = data["url"]

    await callback_query.message.edit("Téléchargement en cours, veuillez patienter...")

    ydl_opts = {
        "format": "bestaudio/best" if format == "mp3" else f"bestvideo[height<={format[:-1]}]+bestaudio",
        "outtmpl": f"{callback_query.from_user.id}_%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4" if format in ["480p", "720p"] else "mp3",
        "cookiefile": "cookies.txt"
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            video_title = info.get("title", "Vidéo")

        await callback_query.message.reply_document(
            file_path,
            caption=f"Voici votre vidéo YouTube : **{video_title}**",
            quote=True
        )
        os.remove(file_path)
        await callback_query.message.edit("Téléchargement terminé et fichier envoyé.")

    except Exception as e:
        await callback_query.message.edit(f"Erreur lors du téléchargement ou de l'envoi : {e}")
        print(f"[Erreur] Téléchargement échoué : {e}")

if __name__ == "__main__":
    bot.run()
