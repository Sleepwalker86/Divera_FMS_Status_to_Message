import asyncio
import json
import logging
import websockets
import aiohttp
import os
import time
import urllib
import base64
from datetime import datetime

# Erhalte den absoluten Pfad zur aktuellen Datei
current_directory = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(current_directory, 'config.json')
LOG_FILE = os.path.join(current_directory, 'log.txt')

# Logger konfigurieren
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s | %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Konstanten
__version__ = "4.0.0"
DIVERA_CORE_URL = 'https://app.divera247.com'
WS_URL = 'wss://ws.divera247.com'

# Duplikat-Filter: (vehicle_id, fmsstatus_ts) → verhindert doppelte Verarbeitung über mehrere UCR-Verbindungen
seen_events: set = set()
seen_lock = asyncio.Lock()


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


def archive_time(autoarchive_days, autoarchive_hours, autoarchive_minutes, autoarchive_seconds):
    if autoarchive_days == 0 and autoarchive_hours == 0 and autoarchive_minutes == 0 and autoarchive_seconds == 0:
        ts_archive = int(time.time()) + 24 * 3600
    else:
        ts_archive = int(time.time()) + autoarchive_days * 86400 + autoarchive_hours * 3600 + autoarchive_minutes * 60 + autoarchive_seconds
    return ts_archive


def send_message(title, text, private_mode, notification_type, send_push, send_mail,
                 ts_publish, archive, ts_archive, group, users_fremdschluessel, api_key, ucr_id=None):
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
    message_url = f"{DIVERA_CORE_URL}/api/v2/news?accesskey={api_key}"
    if ucr_id:
        message_url += f"&ucr={ucr_id}"
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
        logger.error("Fehler beim Senden der Meldung: %s", e)


def resolve_recipients(config, vehicle_cluster_id):
    """
    Ermittelt die Empfänger anhand des notification_target und der Cluster-ID des Fahrzeugs.

    notification_target:
      "global"  → Empfänger aus dem globalen Fallback (erste Org oder globale Felder)
      "source"  → Empfänger aus der Organisation, zu der das Fahrzeug gehört
      "cluster" → Nur senden wenn Fahrzeug zur notification_target_cluster_id gehört,
                  Empfänger aus dieser Org
      "all"     → Nachricht an alle konfigurierten Organisationen senden

    Gibt zurück:
      - Für "all": Liste von (notification_type, groups_divera, users_primaerschluessel, ucr_id)
      - Sonst: (notification_type, groups_divera, users_primaerschluessel) oder None wenn nicht senden.
    """
    target = config.get("notification_target", "global")
    organizations = config.get("organizations", {})

    def recipients_for_cluster(cluster_id):
        """Sucht in organizations nach dem Eintrag mit passender cluster_id."""
        for ucr_id, org in organizations.items():
            if str(org.get("cluster_id")) == str(cluster_id):
                return (
                    org.get("notification_type", "4"),
                    org.get("groups_divera", []),
                    org.get("users_primaerschluessel", [])
                )
        return None

    if target == "global":
        # Globale Empfänger: Empfänger der Hauptorganisation (erste in der Liste)
        if organizations:
            first_org = next(iter(organizations.values()))
            return (
                first_org.get("notification_type", "4"),
                first_org.get("groups_divera", []),
                first_org.get("users_primaerschluessel", [])
            )
        return None

    elif target == "source":
        # Empfänger aus der Org des Fahrzeugs
        result = recipients_for_cluster(vehicle_cluster_id)
        if result is None:
            logger.warning(f"Keine Organisation für Cluster-ID {vehicle_cluster_id} gefunden. Nachricht wird nicht gesendet.")
        return result

    elif target == "cluster":
        # Nur senden wenn Fahrzeug zur konfigurierten Cluster-ID gehört
        target_cluster_id = config.get("notification_target_cluster_id")
        if str(vehicle_cluster_id) != str(target_cluster_id):
            return None  # Fahrzeug gehört nicht zur Ziel-Org → nicht senden
        result = recipients_for_cluster(vehicle_cluster_id)
        if result is None:
            logger.warning(f"Keine Organisation für Cluster-ID {vehicle_cluster_id} gefunden. Nachricht wird nicht gesendet.")
        return result

    elif target == "all":
        # Nachricht an jede konfigurierte Organisation senden
        results = []
        for ucr_id, org in organizations.items():
            results.append((
                org.get("notification_type", "4"),
                org.get("groups_divera", []),
                org.get("users_primaerschluessel", []),
                ucr_id
            ))
        return results if results else None

    return None


async def fetch_jwt_token(api_key, ucr_id=None):
    url = f"{DIVERA_CORE_URL}/api/v2/auth/jwt?accesskey={api_key}"
    if ucr_id:
        url += f"&ucr={ucr_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()



async def process_vehicle_message(message_data, ucr_id, cluster_id):
    """Verarbeitet eine eingehende WebSocket-Nachricht vom Typ 'cluster-vehicle'."""
    config = load_config()
    api_key = config["api_key"]
    mode = config.get("mode", 1)
    destination_fms = int(config.get("destination_fms", 2))
    auto_archiv = config["auto_archiv"]
    autoarchive_days = config.get('autoarchive_days', 0)
    autoarchive_hours = config.get('autoarchive_hours', 0)
    autoarchive_minutes = config.get('autoarchive_minutes', 0)
    autoarchive_seconds = config.get('autoarchive_seconds', 0)
    send_push = config["send_push"]
    send_mail = config["send_mail"]
    private_mode = config["private_mode"]
    message_titel = config["message_titel"]
    ts_publish = int(time.time())
    status_dict = {k: int(v) for k, v in config.get("status_dict", {}).items()}

    vehicle_data = message_data.get('payload', {}).get('vehicle', {})
    if not vehicle_data:
        return

    vehicle_id = str(vehicle_data.get('id'))
    fmsstatus_id = int(vehicle_data.get('fmsstatus_id'))

    # Fahrzeugdetails via REST abrufen – ucr_id übergeben damit auch Unterorganisationen abgerufen werden
    url = f"{DIVERA_CORE_URL}/api/v2/pull/vehicle-status?accesskey={api_key}&ucr={ucr_id}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            for item in data["data"]:
                item_id = str(item["id"])
                if item_id != vehicle_id:
                    continue

                fullname = item["fullname"]
                shortname = item["shortname"]
                fmsstatus = int(item["fmsstatus"])
                vehicle_cluster_id = item.get("cluster_id", cluster_id)
                
                # Neu gesehenes Fahrzeug eintragen
                if vehicle_id not in status_dict:
                    status_dict[vehicle_id] = fmsstatus
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Fahrzeug: {shortname} "
                          f"(Cluster: {vehicle_cluster_id}) hinzugefügt. Status: {fmsstatus}")

                # Prüfen ob Nachricht gesendet werden soll
                should_send = False
                if mode == 1:
                    if (status_dict[vehicle_id] == 6 and fmsstatus_id != 6) or \
                       (status_dict[vehicle_id] != 6 and fmsstatus_id == 6):
                        should_send = True
                elif mode == 2:
                    if fmsstatus_id != status_dict[vehicle_id]:
                        should_send = True
                elif mode == 3:
                    if fmsstatus_id != status_dict[vehicle_id] and fmsstatus_id == destination_fms:
                        should_send = True

                if should_send:
                    recipients = resolve_recipients(config, vehicle_cluster_id)
                    if recipients is not None:
                        message_text = (
                            f"Das Fahrzeug ({shortname}) hat in den Status: {fmsstatus} gewechselt.\n"
                            f" Fahrzeugname: {fullname},\n"
                            f" Kurzname: {shortname},\n"
                            f" FMS Status: {fmsstatus}\n"
                        )
                        ts_archive = archive_time(autoarchive_days, autoarchive_hours, autoarchive_minutes, autoarchive_seconds)
                        # "all"-Modus liefert eine Liste mit (notification_type, groups, users, ucr_id)
                        if isinstance(recipients, list):
                            for notification_type, groups_divera, users_primaerschluessel, target_ucr_id in recipients:
                                send_message(
                                    message_titel, message_text, private_mode, notification_type,
                                    send_push, send_mail, ts_publish, auto_archiv,
                                    ts_archive, groups_divera, users_primaerschluessel, api_key, target_ucr_id
                                )
                        else:
                            notification_type, groups_divera, users_primaerschluessel = recipients
                            send_message(
                                message_titel, message_text, private_mode, notification_type,
                                send_push, send_mail, ts_publish, auto_archiv,
                                ts_archive, groups_divera, users_primaerschluessel, api_key, ucr_id
                            )

                # Status aktualisieren
                status_dict[vehicle_id] = fmsstatus

        config["status_dict"] = status_dict
        save_config(config)

    except Exception as e:
        logger.error("Fehler beim Abrufen der Fahrzeugdaten: %s", e)


async def listen_ucr(api_key, ucr_id, cluster_id, cluster_name):
    """Stellt eine WebSocket-Verbindung für eine UCR her und verarbeitet Nachrichten."""
    while True:
        try:
            jwt_response = await fetch_jwt_token(api_key, ucr_id)
            jwt = jwt_response['data']['jwt_ws']

            async with websockets.connect(WS_URL + '/ws') as websocket:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | [{cluster_name}] WebSocket-Verbindung hergestellt.")
                logger.info(f"[{cluster_name}] WebSocket-Verbindung hergestellt (UCR: {ucr_id}).")

                auth_data = {'type': 'authenticate', 'payload': {'jwt': jwt}}
                await websocket.send(json.dumps(auth_data))

                async for raw_message in websocket:
                    message_data = json.loads(raw_message)

                    if message_data.get('type') == 'cluster-vehicle':
                        vehicle = message_data.get('payload', {}).get('vehicle', {})
                        vehicle_id = vehicle.get('id')
                        fmsstatus_ts = vehicle.get('fmsstatus_ts')

                        # Duplikat-Filter
                        if vehicle_id and fmsstatus_ts:
                            event_key = (vehicle_id, fmsstatus_ts)
                            async with seen_lock:
                                if event_key in seen_events:
                                    continue
                                seen_events.add(event_key)

                        await process_vehicle_message(message_data, ucr_id, cluster_id)
                    else:
                        msg_type = message_data.get('type', 'unbekannt')
                        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | [{cluster_name}] "
                              f"Nachrichtentyp '{msg_type}' empfangen – wird nicht verarbeitet.")

        except (websockets.ConnectionClosed, aiohttp.ClientError) as e:
            logger.warning(f"[{cluster_name}] Verbindung unterbrochen: {e} – Wiederverbindung in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"[{cluster_name}] Fehler: {e} – Wiederverbindung in 5s...")
            await asyncio.sleep(5)


async def authenticate_and_listen():
    config = load_config()
    api_key = config["api_key"]
    organizations = config.get("organizations", {})

    if not organizations:
        logger.error("Keine Organisationen in der config.json gefunden. Bitte setup.py erneut ausführen.")
        exit(1)

    print(f"Divera FMS Status to Message v{__version__}")
    print(f"\nStarte Überwachung für {len(organizations)} Organisation(en):")
    for ucr_id, org in organizations.items():
        print(f"  → {org['name']} (Cluster-ID: {org['cluster_id']}, UCR: {ucr_id})")

    notification_target = config.get("notification_target", "global")
    print(f"\nBenachrichtigungsmodus: {notification_target}")
    if notification_target == "cluster":
        print(f"Ziel-Cluster-ID: {config.get('notification_target_cluster_id')}")
    elif notification_target == "all":
        print(f"Nachricht wird an alle {len(organizations)} Organisation(en) gesendet.")
    print()

    # Pro Organisation eine eigene WebSocket-Task starten
    tasks = [
        listen_ucr(api_key, ucr_id, org["cluster_id"], org["name"])
        for ucr_id, org in organizations.items()
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logger.info("Script gestartet.")
    asyncio.run(authenticate_and_listen())
    logger.info("Script beendet.")