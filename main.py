import os
import sys
import re
import random
import time
import asyncio
import aiohttp
import collections
import datetime

from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import PhoneNumberBannedError
from telethon.sessions import StringSession

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import telebot

# ------------------------------------------------------------
#  LECTURA DE VARIABLES DE ENTORNO (obligatorias)
# ------------------------------------------------------------
def get_env_var(name):
    value = os.environ.get(name)
    if value is None:
        print(f"❌ ERROR: Falta la variable de entorno '{name}'")
        sys.exit(1)
    return value

API_ID = int(get_env_var("API_ID"))
API_HASH = get_env_var("API_HASH")
BOT_TOKEN = get_env_var("BOT_TOKEN")
CHANNEL_ID = int(get_env_var("CHANNEL_ID"))
PHONE_NUMBER = get_env_var("PHONE_NUMBER")
PUBLICATION_DELAY = float(os.environ.get("PUBLICATION_DELAY_SECONDS", 5))

# SESSION_STRING es OBLIGATORIA en Railway (la obtendrás localmente)
SESSION_STRING = os.environ.get("SESSION_STRING", None)
if not SESSION_STRING:
    print("⚠️  SESSION_STRING no configurada. Se generará una nueva sesión.")
    print("   Después de la primera ejecución, copia la cadena de los logs")
    print("   y pégala como variable de entorno SESSION_STRING para futuros reinicios.\n")

# ------------------------------------------------------------
#  INICIALIZACIÓN
# ------------------------------------------------------------
bot = telebot.TeleBot(BOT_TOKEN)
PROCESSED_CARD_NUMBERS = collections.deque(maxlen=1000)

IMAGES_URL = [
    'https://i.pinimg.com/736x/4c/e0/6f/4ce06fcebb0a04d909aa1576ec95873f.jpg',
    'https://i.pinimg.com/736x/77/5c/cf/775ccf064684a7ea0f886b4a47fd23aa.jpg',
    'https://i.pinimg.com/736x/06/55/9b/06559b97ced10e030c88b4028890f7d9.jpg',
    'https://i.pinimg.com/736x/b9/03/8f/b9038fc97d38e0641750a6cad77dc1f8.jpg',
    'https://i.pinimg.com/736x/bb/95/bc/bb95bc1086d690e9be03b31e18d15a29.jpg'
]

aiohttp_session = None
publication_lock = asyncio.Lock()
last_publication_time = 0.0

# ------------------------------------------------------------
#  FUNCIONES AUXILIARES
# ------------------------------------------------------------
def process_card_masking(card_info: str, match: re.Match, mask_type: int):
    processed_card = ""
    expiration_month = match.group(2)
    expiration_year = match.group(3)

    if mask_type == 1:
        processed_card = card_info[:12] + 'xxxx'
    elif mask_type == 2:
        processed_card = card_info[:10] + str(random.randint(10, 99)) + 'xxxx'
    elif mask_type == 3:
        processed_card = card_info[:10] + str(random.randint(10, 99)) + 'xxxx'
    elif mask_type == 4:
        processed_card = card_info[:8] + str(random.randint(0, 9)) + 'xxxxx' + str(random.randint(0, 9)) + 'x'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))
    elif mask_type == 5:
        processed_card = card_info[:6] + 'x' + str(random.randint(10, 99)) + 'x' + str(random.randint(100, 999)) + 'xxx'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))
    elif mask_type in (6, 7, 8):
        processed_card = card_info[:9] + str(random.randint(100, 999)) + 'xxxx'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))

    return processed_card, expiration_month, expiration_year

# ------------------------------------------------------------
#  MANEJADOR DE EVENTOS
# ------------------------------------------------------------
async def card_handler(event):
    global last_publication_time

    current_time_str = datetime.datetime.now().strftime("%H:%M:%S")

    if event.is_private:
        chat_name = 'Chat privado'
    elif event.is_group:
        chat_name = f'Grupo: {event.chat.title}'
    else:
        chat_name = f'Canal: {event.chat.title}'

    message_text = event.message.message.upper()
    regex = r'(\d{14,16})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    match = re.search(regex, message_text)

    if not match:
        return

    cc = match.group(1)

    if cc in PROCESSED_CARD_NUMBERS:
        print(f"[{current_time_str}] [{chat_name}] Tarjeta {cc} ya procesada. Ignorando.")
        return

    PROCESSED_CARD_NUMBERS.append(cc)
    print(f"[{current_time_str}] [{chat_name}] Nueva tarjeta: {cc}")

    mes = match.group(2)
    years = match.group(3)
    cvv = match.group(4)
    card_info = match.group(0)

    # Obtener información del BIN
    bin_info = {"brand": "N/A", "type": "N/A", "level": "N/A",
                "bank": "N/A", "country_name": "N/A", "country_flag": ""}
    try:
        async with aiohttp_session.get(f"https://bins.antipublic.cc/bins/{cc[:6]}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            bin_info.update(data)
    except Exception as e:
        print(f"[{current_time_str}] Error al obtener BIN: {e}")

    # Generar 8 enmascaramientos
    masks = [process_card_masking(card_info, match, i) for i in range(1, 9)]

    custom_message = f"""
✶  𝗖𝗛𝗘𝗥𝗥𝗬’𝗦 𝗘𝗫𝗧𝗥𝗔𝗦  — [#B{cc[:6]}]

꩜ 𝖢𝖢: <code>{card_info}</code>
꩜ 𝖢𝖮𝖴𝖭𝖳𝖱𝖸: <code>{bin_info['country_name']}</code> <code>[{bin_info['country_flag']}]</code>
꩜ 𝖡𝖠𝖭𝖪: <code>{bin_info['bank']}</code>
꩜ 𝖨𝖭𝖥𝖮: <code>{bin_info['level']}</code> <code>{bin_info['type']}</code> <code>{bin_info['brand']}</code>

︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶
  —⠀𝖤𝖷𝖳𝖱𝖠𝖯𝖮𝖫𝖠𝖳𝖤𝖣 𝖤𝖷𝖳𝖱𝖠𝖲

➜ <code>{masks[0][0]}|{masks[0][1]}|{masks[0][2]}|rnd</code>
➜ <code>{masks[1][0]}|{masks[1][1]}|{masks[1][2]}|rnd</code>
➜ <code>{masks[2][0]}|{masks[2][1]}|{masks[2][2]}|rnd</code>
➜ <code>{masks[3][0]}|{masks[3][1]}|{masks[3][2]}|rnd</code>
➜ <code>{masks[4][0]}|{masks[4][1]}|{masks[4][2]}|rnd</code>

︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶
ᝬ  —⠀𝖣𝖠𝖳𝖠𝖡𝖠𝖲𝖤 𝖤𝖷𝖳𝖱𝖠𝖲

⥤ <code>{masks[5][0]}|{masks[5][1]}|{masks[5][2]}|rnd</code>
⥤ <code>{masks[6][0]}|{masks[6][1]}|{masks[6][2]}|rnd</code>
⥤ <code>{masks[7][0]}|{masks[7][1]}|{masks[7][2]}|rnd</code>
"""

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("𖥻 INFO", url="https://t.me/infocherrys"),
        InlineKeyboardButton("𖥻 REFES", url="https://t.me/+oS0yU_A2yGxjMjQ0")
    )

    image_url = random.choice(IMAGES_URL)

    # Control de velocidad
    async with publication_lock:
        now = time.monotonic()
        elapsed = now - last_publication_time
        if elapsed < PUBLICATION_DELAY:
            wait = PUBLICATION_DELAY - elapsed
            print(f"[{current_time_str}] Esperando {wait:.2f}s para publicar {cc}")
            await asyncio.sleep(wait)

        try:
            await asyncio.to_thread(
                bot.send_photo,
                CHANNEL_ID,
                image_url,
                caption=custom_message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            last_publication_time = time.monotonic()
            print(f"[{current_time_str}] Tarjeta {cc} publicada.")
        except Exception as e:
            print(f"[{current_time_str}] Error al enviar: {e}")

# ------------------------------------------------------------
#  FUNCIÓN PRINCIPAL
# ------------------------------------------------------------
async def main():
    global aiohttp_session, last_publication_time

    aiohttp_session = aiohttp.ClientSession()
    last_publication_time = time.monotonic()

    # Crear cliente Telethon con sesión persistente
    if SESSION_STRING:
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        print("✅ Usando SESSION_STRING guardada.")
    else:
        client = TelegramClient("extras", API_ID, API_HASH)
        print("⚠️  No se encontró SESSION_STRING. Se generará una nueva sesión.")
        print("   Después de iniciar sesión, copia la cadena de los logs.")

    # Registrar el manejador de eventos
    client.add_event_handler(card_handler, events.NewMessage())
    client.add_event_handler(card_handler, events.MessageEdited())

    try:
        # Iniciar sesión
        await client.start(phone=PHONE_NUMBER)
        print("✅ Cliente Telethon conectado.")

        # Si no había SESSION_STRING, mostrar la cadena para guardarla
        if not SESSION_STRING:
            session_str = client.session.save()
            print("\n" + "="*70)
            print("🔑 GUARDA ESTA CADENA EN LA VARIABLE DE ENTORNO 'SESSION_STRING':")
            print(session_str)
            print("="*70 + "\n")
            print("📌 En Railway: ve a Settings → Variables y añade SESSION_STRING con este valor.")
            print("📌 Luego redeploy para que el bot use la sesión persistente.\n")

        print("📡 Escuchando mensajes...")
        await client.run_until_disconnected()

    except PhoneNumberBannedError:
        print("❌ El número de teléfono está baneado.")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    finally:
        if aiohttp_session:
            await aiohttp_session.close()
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
