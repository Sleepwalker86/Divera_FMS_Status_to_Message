import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
import websockets
import aiohttp
import os
import time
import urllib
from datetime import datetime

# Erhalte den absoluten Pfad zur aktuellen Datei
current_directory = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(current_directory, 'config.json')
LOG_FILE = os.path.join(current_directory, 'log.txt')

# ------------------------------------------------------------
# Konfiguration laden (für max_log_file_size)
# ------------------------------------------------------------
with open(CONFIG_FILE) as f:
    cfg = json.load(f)

max_log_file_size = cfg.get("max_log_file_size", 5)  # in MB
max_bytes = max_log_file_size * 1024 * 1024          # MB → Bytes

# ------------------------------------------------------------
# Logger mit automatischer Logrotation einrichten
# ------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=max_bytes,
    backupCount=cfg.get("backup_count", 5)
)

formatter = logging.Formatter('%(asctime)s | %(levelname)s: %(message)s')
handler.setFormatter(formatter)

# Root-Logger zuerst aufräumen, dann Handler setzen
logger.handlers.clear()
logger.addHandler(handler)
# ------------------------------------------------------------


# Setze die erforderlichen Konstanten.
DIVERA_CORE_URL = 'https://app.divera247.com'
WS_URL = 'wss://ws.divera247.com'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        logger.info("Die Konfigurationsdatei '{}' existiert nicht.".format(CONFIG_FILE))
        logger.info("Bitte erstellen Sie eine Konfigurationsdatei mit den erforderlichen Informationen.")
        logger.info("Starte das Script: python3 setup.py um die config.json zu erstellen.")
        exit(1)
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def send_message(title, text, private_mode, notification_type, send_push, send_mail, ts_publish, archive, ts_archive, group, users_fremdschluessel, api_key):
    message_data = {
        "News": {
            "title": title,
            "text": text,
            "private_mode": private_mode,
            "notification_type": notification_type,
            "send_push": send_push,
            "send_mail": send_mail,
            "ts_publish": ts_publish,
            "archive": archive,
            "ts_archive": ts_archive,
            "group": group,
            "user_cluster_relation": users_fremdschluessel
        }
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    message_url = f"https://app.divera247.com/api/v2/news?accesskey={api_key}"

    try:
        req = urllib.request.Request(message_url, method='POST', headers=headers)
        data = json.dumps(message_data).encode('utf-8')
        response = urllib.request.urlopen(req, data=data)
        result = json.loads(response.read().decode('utf-8'))
        if 'success' in result and result['success']:
            logger.info(text)
            logger.info("Meldung erfolgreich gesendet.")
        else:
            logger.error("Fehler beim Senden der Meldung. Antwort: %s", result)
    except Exception as e:
        logger.error("Es ist ein Fehler beim Senden der Meldung aufgetreten: %s", e)

def archive_time(autoarchive_days, autoarchive_hours, autoarchive_minutes, autoarchive_seconds):
    if autoarchive_days == 0 and autoarchive_hours == 0 and autoarchive_minutes == 0 and autoarchive_seconds == 0:
        ts_archive = int(time.time()) + autoarchive_days * 86400 + 24 * 3600 + autoarchive_minutes * 60 + autoarchive_seconds
    else:
        ts_archive = int(time.time()) + autoarchive_days * 86400 + autoarchive_hours * 3600 + autoarchive_minutes * 60 + autoarchive_seconds
    return ts_archive

async def authenticate_and_listen():
    while True:
        try:
            jwt_response = await fetch_jwt_token()
            jwt = jwt_response['data']['jwt_ws']

            async with websockets.connect(WS_URL + '/ws') as websocket:
                print('WebSocket-Verbindung hergestellt')

                auth_data = {'type': 'authenticate', 'payload': {'jwt': jwt}}
                await websocket.send(json.dumps(auth_data))

                async for message in websocket:
                    await main(message)

        except (websockets.ConnectionClosed, aiohttp.ClientError) as e:
            logger.error(f"Verbindung unterbrochen: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Ein Fehler ist aufgetreten: {e}")
            await asyncio.sleep(5)

async def fetch_jwt_token():
    config = load_config()
    api_key = config["api_key"]
    async with aiohttp.ClientSession() as session:
        async with session.get(DIVERA_CORE_URL + '/api/v2/auth/jwt?accesskey=' + api_key, ssl=False) as response:
            return await response.json()

async def main(message):
    config = load_config()
    api_key = config["api_key"]
    mode = config.get("mode", 1)
    destination_fms = config.get("destination_fms", 3)
    auto_archiv = config["auto_archiv"]
    autoarchive_days = config.get('autoarchive_days', 0)
    autoarchive_hours = config.get('autoarchive_hours', 0)
    autoarchive_minutes = config.get('autoarchive_minutes', 0)
    autoarchive_seconds = config.get('autoarchive_seconds', 0)
    send_push = config["send_push"]
    send_mail = config["send_mail"]
    private_mode = config["private_mode"]
    notification_type = config.get("notification_type", 4)
    users_primaerschluessel = config.get("users_primaerschluessel", [])
    groups_divera = config.get("groups_divera", [])
    message_titel = config["message_titel"]
    ts_publish = int(time.time())

    status_dict = config.get("status_dict", {})

    url = f"https://app.divera247.com/api/v2/pull/vehicle-status?accesskey={api_key}"

    message_data = json.loads(message)

    if message_data.get('type') == 'cluster-vehicle':
        vehicle_data = message_data.get('payload', {}).get('vehicle', {})
        if vehicle_data:
            vehicle_id = str(vehicle_data.get('id'))
            fmsstatus_id = vehicle_data.get('fmsstatus_id')

            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    for item in data["data"]:
                        id = str(item["id"])
                        if id == vehicle_id:
                            fullname = item["fullname"]
                            shortname = item["shortname"]
                            fmsstatus = item["fmsstatus"]

                            if id not in status_dict:
                                status_dict[id] = fmsstatus

                            if mode == 1:
                                if (status_dict[vehicle_id] == 6 and fmsstatus_id != 6) or (status_dict[vehicle_id] != 6 and fmsstatus_id == 6):
                                    msg = f"Das Fahrzeug ({shortname}) hat in den Status: {fmsstatus} gewechselt.\n Fahrzeugname: {fullname},\n Kurzname: {shortname},\n FMS Status: {fmsstatus}\n"
                                    send_message(message_titel, msg, private_mode, notification_type, send_push, send_mail, ts_publish, auto_archiv, archive_time(autoarchive_days, autoarchive_hours, autoarchive_minutes, autoarchive_seconds), groups_divera, users_primaerschluessel, api_key)

                            elif mode == 2:
                                if fmsstatus_id != status_dict[vehicle_id]:
                                    msg = f"Das Fahrzeug ({shortname}) hat in den Status: {fmsstatus} gewechselt.\n Fahrzeugname: {fullname},\n Kurzname: {shortname},\n FMS Status: {fmsstatus}\n"
                                    send_message(message_titel, msg, private_mode, notification_type, send_push, send_mail, ts_publish, auto_archiv, archive_time(autoarchive_days, autoarchive_hours, autoarchive_minutes, autoarchive_seconds), groups_divera, users_primaerschluessel, api_key)

                            elif mode == 3:
                                if fmsstatus_id != status_dict[vehicle_id] and fmsstatus_id == destination_fms:
                                    msg = f"Das Fahrzeug ({shortname}) hat in den Status: {fmsstatus} gewechselt.\n Fahrzeugname: {fullname},\n Kurzname: {shortname},\n FMS Status: {fmsstatus}\n"
                                    send_message(message_titel, msg, private_mode, notification_type, send_push, send_mail, ts_publish, auto_archiv, archive_time(autoarchive_days, autoarchive_hours, autoarchive_minutes, autoarchive_seconds), groups_divera, users_primaerschluessel, api_key)

                            status_dict[id] = fmsstatus

                    config["status_dict"] = status_dict
                    save_config(config)

            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Daten: {e}")

    else:
        print("Daten vom Typ: '", message_data.get('type') + " ' empfangen. Diese Daten werden nicht weiter verarbeitet.")

if __name__ == "__main__":
    asyncio.run(authenticate_and_listen())
    logger.info("Script erfolgreich ausgeführt!")
