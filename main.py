import os  # <--- ESTO ES LO QUE TE FALTABA
import time
import re
import random
import asyncio
import aiohttp
import collections
import datetime

from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import PhoneNumberBannedError
from telethon.sessions import StringSession  # <--- PARA USAR SESSION_STRING

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import telebot

# ------------------------------------------------------------
#  LEER TODAS LAS CREDENCIALES DE LAS VARIABLES DE ENTORNO
# ------------------------------------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
PHONE_NUMBER = os.environ["PHONE_NUMBER"]
SESSION_STRING = os.environ.get("SESSION_STRING")  # <--- LA CLAVE PARA RAILWAY

# Si no hay SESSION_STRING, el bot fallará (pero tú ya la tienes)
if not SESSION_STRING:
    print("❌ ERROR: SESSION_STRING no está configurada en variables de entorno.")
    exit(1)

# ------------------------------------------------------------
#  CONFIGURACIÓN ADICIONAL
# ------------------------------------------------------------
PUBLICATION_DELAY_SECONDS = 5

images_url = [
    'https://i.pinimg.com/736x/4c/e0/6f/4ce06fcebb0a04d909aa1576ec95873f.jpg',
    'https://i.pinimg.com/736x/77/5c/cf/775ccf064684a7ea0f886b4a47fd23aa.jpg',
    'https://i.pinimg.com/736x/06/55/9b/06559b97ced10e030c88b4028890f7d9.jpg',
    'https://i.pinimg.com/736x/b9/03/8f/b9038fc97d38e0641750a6cad77dc1f8.jpg',
    'https://i.pinimg.com/736x/bb/95/bc/bb95bc1086d690e9be03b31e18d15a29.jpg'
]

# Inicializamos el bot de telebot
bot = telebot.TeleBot(BOT_TOKEN)

# Caché para evitar duplicados
PROCESSED_CARD_NUMBERS = collections.deque(maxlen=1000)

# --- NUEVO: Usar StringSession en lugar de archivo ---
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Sesión persistente para aiohttp
aiohttp_session = None

# --- Control de velocidad ---
publication_lock = asyncio.Lock()
last_publication_time = 0.0

# ------------------------------------------------------------
#  FUNCIONES AUXILIARES (tú lógica, sin cambios)
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
        processed_card = card_info[:6] +'x' + str(random.randint(10, 99)) + 'x' + str(random.randint(100, 999)) + 'xxx'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))
    elif mask_type == 6:
        processed_card = card_info[:9] + str(random.randint(100, 999)) + 'xxxx'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))
    elif mask_type == 7:
        processed_card = card_info[:9] + str(random.randint(100, 999)) + 'xxxx'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))
    elif mask_type == 8:
        processed_card = card_info[:9] + str(random.randint(100, 999)) + 'xxxx'
        expiration_month = str(random.randint(1, 12)).zfill(2)
        expiration_year = str(random.randint(2025, 2032))
    
    return processed_card, expiration_month, expiration_year

# ------------------------------------------------------------
#  MANEJADOR DE EVENTOS (sin cambios, solo la función)
# ------------------------------------------------------------
@client.on(events.NewMessage())
@client.on(events.MessageEdited())
async def handler(event):
    global last_publication_time

    current_time_str = datetime.datetime.now().strftime("%H:%M:%S")

    if event.is_private:
        chat_name = 'Chat privado'
    elif event.is_group:
        chat_name = 'Grupo: {}'.format(event.chat.title)
    else:
        chat_name = 'Canal: {}'.format(event.chat.title)

    message_get = event.message.message.upper()
    regex = r'(\d{14,16})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'

    match = re.search(regex, message_get)

    if match:
        cc = match.group(1)

        if cc in PROCESSED_CARD_NUMBERS:
            print(f"[{current_time_str}] [{chat_name}] Tarjeta {cc} ya procesada. Ignorando mensaje para evitar duplicados.")
            return

        PROCESSED_CARD_NUMBERS.append(cc)
        print(f"[{current_time_str}] [{chat_name}] Nueva tarjeta detectada y añadiendo a la caché: {cc}")

        mes = match.group(2)
        years = match.group(3)
        cvv = match.group(4)

        card_info = match.group(0)

        rs = {}
        try:
            async with aiohttp_session.get(f"https://bins.antipublic.cc/bins/{card_info[:6]}") as resp:
                resp.raise_for_status()
                rs = await resp.json()
        except aiohttp.ClientError as e:
            print(f"[{current_time_str}] Error al obtener información del BIN: {e}")
            rs = {"brand": "N/A", "type": "N/A", "level": "N/A", "bank": "N/A", "country_name": "N/A", "country_flag": ""}
        except ValueError as e:
            print(f"[{current_time_str}] Error al decodificar JSON del BIN: {e}")
            rs = {"brand": "N/A", "type": "N/A", "level": "N/A", "bank": "N/A", "country_name": "N/A", "country_flag": ""}

        processed_card1, expiration_month1, expiration_year1 = process_card_masking(card_info, match, 1)
        processed_card2, expiration_month2, expiration_year2 = process_card_masking(card_info, match, 2)
        processed_card3, expiration_month3, expiration_year3 = process_card_masking(card_info, match, 3)
        processed_card4, expiration_month4, expiration_year4 = process_card_masking(card_info, match, 4)
        processed_card5, expiration_month5, expiration_year5 = process_card_masking(card_info, match, 5)
        processed_card6, expiration_month6, expiration_year6 = process_card_masking(card_info, match, 6)
        processed_card7, expiration_month7, expiration_year7 = process_card_masking(card_info, match, 7)
        processed_card8, expiration_month8, expiration_year8 = process_card_masking(card_info, match, 8)

        brand = rs.get("brand", "N/A")
        types = rs.get("type", "N/A")
        level = rs.get("level", "N/A")
        bank = rs.get("bank", "N/A")
        country = rs.get("country_name", "N/A")
        flag = rs.get("country_flag", "")

        custom_message = f"""
✶  𝗖𝗛𝗘𝗥𝗥𝗬’𝗦 𝗘𝗫𝗧𝗥𝗔𝗦  — [#B{card_info[:6]}]

꩜ 𝖢𝖢: <code>{card_info}</code>
꩜ 𝖢𝖮𝖴𝖭𝖳𝖱𝖸: <code>{country}</code> <code>[{flag}]</code>
꩜ 𝖡𝖠𝖭𝖪: <code>{bank}</code>
꩜ 𝖨𝖭𝖥𝖮: <code>{level}</code> <code>{types}</code> <code>{brand}</code>

︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶
  —⠀𝖤𝖷𝖳𝖱𝖠𝖯𝖮𝖫𝖠𝖳𝖤𝖣 𝖤𝖷𝖳𝖱𝖠𝖲

➜ <code>{processed_card1}|{expiration_month1}|{expiration_year1}|rnd</code>
➜ <code>{processed_card2}|{expiration_month2}|{expiration_year2}|rnd</code>
➜ <code>{processed_card3}|{expiration_month3}|{expiration_year3}|rnd</code>
➜ <code>{processed_card4}|{expiration_month4}|{expiration_year4}|rnd</code>
➜ <code>{processed_card5}|{expiration_month5}|{expiration_year5}|rnd</code>

︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶︶
ᝬ  —⠀𝖣𝖠𝖳𝖠𝖡𝖠𝖲𝖤 𝖤𝖷𝖳𝖱𝖠𝖲

⥤ <code>{processed_card6}|{expiration_month6}|{expiration_year6}|rnd</code>
⥤ <code>{processed_card7}|{expiration_month7}|{expiration_year7}|rnd</code>
⥤ <code>{processed_card8}|{expiration_month8}|{expiration_year8}|rnd</code>
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("𖥻 INFO", url="https://t.me/infocherrys"), InlineKeyboardButton("𖥻 REFES", url="https://t.me/+oS0yU_A2yGxjMjQ0"))

        images_rdn_url = random.choice(images_url)

        print(f'[{current_time_str}] {types} CARD: {cc}|{mes}|{years}|{cvv}')

        try:
            async with publication_lock:
                time_since_last_publication = time.monotonic() - last_publication_time
                if time_since_last_publication < PUBLICATION_DELAY_SECONDS:
                    sleep_needed = PUBLICATION_DELAY_SECONDS - time_since_last_publication
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Lock adquirido. Esperando {sleep_needed:.2f} segundos antes de publicar {cc}...")
                    await asyncio.sleep(sleep_needed)

                await asyncio.to_thread(
                    bot.send_photo,
                    CHANNEL_ID,
                    images_rdn_url,
                    caption=custom_message,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )

                last_publication_time = time.monotonic()
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Tarjeta {cc} publicada exitosamente. Lock liberado.")
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Error al enviar la foto o mensaje con telebot para {cc}: {e}")

# ------------------------------------------------------------
#  FUNCIÓN PRINCIPAL
# ------------------------------------------------------------
async def main():
    global aiohttp_session, last_publication_time

    aiohttp_session = aiohttp.ClientSession()
    last_publication_time = time.monotonic()

    try:
        # Iniciar sesión con el número desde variables de entorno
        await client.start(phone=PHONE_NUMBER)
        print("Clientes de Telegram iniciados y escuchando mensajes...")

        await client.run_until_disconnected()

    except PhoneNumberBannedError:
        print("¡ATENCIÓN! Tu número de teléfono ha sido baneado por Telegram. Por favor, revisa tu cuenta.")
    except Exception as e:
        print(f"Ocurrió un error inesperado al iniciar o mantener el cliente: {e}.")
    finally:
        if aiohttp_session:
            await aiohttp_session.close()
            print("Sesión aiohttp cerrada.")

if __name__ == '__main__':
    asyncio.run(main())
