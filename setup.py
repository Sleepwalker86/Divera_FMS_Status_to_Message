import json
import os
import subprocess
import asyncio
import base64
import platform

DIVERA_CORE_URL = "https://app.divera247.com"
IS_LINUX = platform.system() == "Linux"


def install_sudo():
    if not IS_LINUX:
        return
    print("Prüfe sudo...")
    try:
        subprocess.check_call(["which", "sudo"])
    except subprocess.CalledProcessError:
        print("sudo wird installiert...")
        subprocess.check_call(["apt", "install", "-y", "sudo"])


def ensure_aiohttp():
    """Installiert aiohttp falls nicht vorhanden – plattformabhängig."""
    try:
        import aiohttp
        return aiohttp
    except ImportError:
        print("aiohttp wird installiert...")
        if IS_LINUX:
            subprocess.check_call(["sudo", "apt", "install", "-y", "python3-aiohttp"])
        else:
            subprocess.check_call(["pip3", "install", "aiohttp", "websockets"])
        import aiohttp
        return aiohttp


def check_and_install_module(module_name):
    try:
        __import__(module_name)
        print(f"  ✓ {module_name} ist bereits installiert.")
    except ImportError:
        print(f"  → {module_name} wird installiert...")
        if IS_LINUX:
            subprocess.check_call(["sudo", "apt", "install", "-y", f"python3-{module_name}"])
        else:
            subprocess.check_call(["pip3", "install", module_name])


def check_and_install_modules(module_names):
    print("\nPrüfe erforderliche Module:")
    for module_name in module_names:
        check_and_install_module(module_name)
    print("Alle erforderlichen Module sind installiert.\n")


def create_service():
    if not IS_LINUX:
        print("\nHinweis: Service-Installation wird nur auf Linux unterstützt.")
        print("Auf dem Raspberry Pi setup.py erneut ausführen um den Service einzurichten.")
        return
    current_directory = os.getcwd()
    service_content = f'''[Unit]
Description=Divera WebSocket Dienst
After=network.target

[Service]
ExecStart=/usr/bin/python3 {current_directory}/main.py
WorkingDirectory={current_directory}
Restart=always
RuntimeMaxSec=86400

[Install]
WantedBy=multi-user.target
'''
    with open("/etc/systemd/system/divera_websocket.service", "w") as f:
        f.write(service_content)

    os.system("sudo systemctl daemon-reload")
    os.system("sudo systemctl start divera_websocket")
    print("Divera WebSocket Dienst erfolgreich gestartet!")
    os.system("sudo systemctl enable divera_websocket")
    print("Divera WebSocket Dienst aktiviert (startet beim Boot).")
    os.system("sudo systemctl status divera_websocket")


async def fetch_organizations(api_key):
    """Ruft alle verfügbaren Organisationen/Cluster aus dem JWT-Payload ab."""
    aiohttp = ensure_aiohttp()
    url = f"{DIVERA_CORE_URL}/api/v2/auth/jwt?accesskey={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Fehler beim Abrufen des JWT-Tokens. HTTP-Status: {response.status}")
                    return {}
                data = await response.json()

        jwt_ws = data.get("data", {}).get("jwt_ws", "")
        if not jwt_ws:
            print("Kein JWT-Token in der Antwort gefunden. API-Key prüfen.")
            return {}

        # JWT-Payload dekodieren
        payload_b64 = jwt_ws.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        ucr_map = {}
        for ucr_id, info in payload.get("allowed_ucr", {}).items():
            ucr_map[ucr_id] = {
                "cluster_id": info["cluster_id"],
                "name": info.get("name", f"Cluster {info['cluster_id']}")
            }
        return ucr_map

    except Exception as e:
        print(f"Fehler beim Abrufen der Organisationen: {e}")
        return {}


def configure_recipients(org_name):
    """Fragt Empfänger-Einstellungen für eine Organisation ab."""
    print(f"\n  Empfänger für '{org_name}':")
    print("  Benachrichtigungstyp:")
    print("    3 = Ausgewählte Gruppen")
    print("    4 = Ausgewählte Benutzer")
    while True:
        notification_type = input("  Bitte Benachrichtigungstyp eingeben (3 oder 4, default: 4): ").strip() or "4"
        if notification_type in ("3", "4"):
            break
        print(f"  Ungueltige Eingabe '{notification_type}' - bitte nur 3 oder 4 eingeben.")

    groups_divera = []
    users_primaerschluessel = []

    if notification_type == "3":
        print("  Gruppen-IDs eingeben (eine pro Zeile, leere Zeile zum Beenden):")
        while True:
            gid = input("    Gruppen-ID: ").strip()
            if not gid:
                break
            groups_divera.append(gid)
        if not groups_divera:
            groups_divera = ["138728"]
            print(f"  Keine Eingabe – Standardwert verwendet: {groups_divera}")
    else:
        print("  Benutzer-Primärschlüssel eingeben (einer pro Zeile, leere Zeile zum Beenden):")
        while True:
            uid = input("    Primärschlüssel: ").strip()
            if not uid:
                break
            users_primaerschluessel.append(uid)
        if not users_primaerschluessel:
            users_primaerschluessel = ["220053"]
            print(f"  Keine Eingabe – Standardwert verwendet: {users_primaerschluessel}")

    return notification_type, groups_divera, users_primaerschluessel


def create_config():
    config = {}
    print("=" * 60)
    print("  DIVERA 24/7 – Setup Hilfe  v4.0.0")
    print("=" * 60)
    print("Dieses Setup hilft dir, die config.json zu erstellen.\n")

    # API-Key
    config["api_key"] = input("Privaten API-Schlüssel aus deinem Divera-Account eingeben\n(default: DEIN-API-KEY): ") or "DEIN-API-KEY"

    # Organisationen automatisch abrufen
    print("\nOrganisationen werden automatisch aus deinem Account abgerufen...")
    ucr_map = asyncio.run(fetch_organizations(config["api_key"]))

    if not ucr_map:
        print("Keine Organisationen gefunden oder API-Key ungültig.")
        print("Du kannst die Organisationen später manuell in der config.json eintragen.")
        ucr_map = {}
    else:
        print(f"\nGefundene Organisationen ({len(ucr_map)}):")
        for i, (ucr_id, info) in enumerate(ucr_map.items(), 1):
            print(f"  [{i}] {info['name']} (Cluster-ID: {info['cluster_id']}, UCR: {ucr_id})")

        # Auswahl welche Organisationen überwacht werden sollen
        print("\nWelche Organisationen sollen überwacht werden?")
        print("  [a] Alle")
        print("  [m] Manuelle Auswahl")
        selection = input("Auswahl (default: a): ").strip().lower() or "a"

        if selection == "m":
            selected_ucr = {}
            ucr_list = list(ucr_map.items())
            print("Nummern der gewünschten Organisationen eingeben (kommagetrennt, z.B. 1,3):")
            raw = input("Auswahl: ").strip()
            try:
                indices = [int(x.strip()) - 1 for x in raw.split(",")]
                for idx in indices:
                    if 0 <= idx < len(ucr_list):
                        ucr_id, info = ucr_list[idx]
                        selected_ucr[ucr_id] = info
            except ValueError:
                print("Ungültige Eingabe – alle Organisationen werden verwendet.")
                selected_ucr = ucr_map
            ucr_map = selected_ucr

    # Modus
    print("\n" + "-" * 40)
    print("Modus auswählen:")
    print("  1 = Statuswechsel von/nach Status 6 meldet")
    print("  2 = Jede Statusänderung meldet")
    print("  3 = Nur bestimmten Zielstatus melden")
    while True:
        mode_input = input("Modus (default: 1): ").strip() or "1"
        if mode_input in ("1", "2", "3"):
            config["mode"] = int(mode_input)
            break
        print(f"  Ungültige Eingabe '{mode_input}' - bitte nur 1, 2 oder 3 eingeben.")

    config["destination_fms"] = 2
    if config["mode"] == 3:
        config["destination_fms"] = int(input("Ziel-FMS-Status eingeben (default: 2): ") or 2)

    # Archivierung
    print("\n" + "-" * 40)
    config["auto_archiv"] = input("Autoarchivierung aktivieren? (true/false, default: false): ").lower() == "true"
    config["autoarchive_days"] = int(input("Archivierung nach X Tagen (default: 1): ") or 1)
    config["autoarchive_hours"] = int(input("+ X Stunden (default: 0): ") or 0)
    config["autoarchive_minutes"] = int(input("+ X Minuten (default: 0): ") or 0)
    config["autoarchive_seconds"] = int(input("+ X Sekunden (default: 0): ") or 0)

    # Benachrichtigungsoptionen
    print("\n" + "-" * 40)
    config["send_push"] = input("Push-Benachrichtigungen senden? (true/false, default: false): ").lower() == "true"
    config["send_mail"] = input("E-Mail-Benachrichtigungen senden? (true/false, default: false): ").lower() == "true"
    config["private_mode"] = input("Privaten Modus für Mitteilungen aktivieren? (true/false, default: false): ").lower() == "true"
    config["message_titel"] = input("Titel der Nachricht (default: Änderung Fahrzeugstatus!): ") or "Änderung Fahrzeugstatus!"

    # Benachrichtigungsziel
    print("\n" + "-" * 40)
    print("Benachrichtigungsziel:")
    print("  global  = Alle Statusänderungen → Empfänger der Hauptorganisation")
    print("  source  = Nachricht geht an die Org, aus der das Fahrzeug stammt")
    print("  cluster = Nur Fahrzeuge eines bestimmten Clusters melden")
    print("  all     = Nachricht an alle konfigurierten Organisationen senden")
    while True:
        notification_target = input("Ziel eingeben (default: source): ").strip().lower() or "source"
        if notification_target in ("global", "source", "cluster", "all"):
            break
        print(f"  Ungültige Eingabe '{notification_target}' - bitte nur global, source, cluster oder all eingeben.")
    config["notification_target"] = notification_target

    config["notification_target_cluster_id"] = None
    if notification_target == "cluster":
        print("\nVerfügbare Cluster-IDs:")
        for ucr_id, info in ucr_map.items():
            print(f"  {info['cluster_id']} → {info['name']}")
        config["notification_target_cluster_id"] = input("Ziel-Cluster-ID eingeben: ").strip()

    # Pro Organisation Empfänger konfigurieren
    print("\n" + "-" * 40)
    print("Empfänger pro Organisation konfigurieren:\n")
    organizations = {}
    for ucr_id, info in ucr_map.items():
        notification_type, groups_divera, users_primaerschluessel = configure_recipients(info["name"])
        organizations[ucr_id] = {
            "cluster_id": info["cluster_id"],
            "name": info["name"],
            "notification_type": notification_type,
            "groups_divera": groups_divera,
            "users_primaerschluessel": users_primaerschluessel
        }

    config["organizations"] = organizations
    config["status_dict"] = {}

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print("\n✓ config.json wurde erfolgreich erstellt.")


def main():
    install_sudo()

    required_modules = [
        "websockets",
        "aiohttp",
        "asyncio",
        "json",
        "logging",
        "os",
        "time",
        "urllib",
        "datetime"
    ]
    check_and_install_modules(required_modules)

    create_config()
    create_service()

    print("\n" + "=" * 60)
    print("  Setup abgeschlossen!")
    print("  Der Dienst läuft bereits im Hintergrund.")
    print("  Logs: log.txt")
    print("=" * 60)


if __name__ == "__main__":
    main()