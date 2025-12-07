import json
import os
import subprocess

def install_sudo():
    print("sudo wird installiert...")
    subprocess.check_call(["apt", "install", "sudo"])

def update_upgrade():
    print("Führe apt update durch...")
    subprocess.check_call(["sudo", "apt", "update"])
    print("Führe apt upgrade durch...")
    subprocess.check_call(["sudo", "apt", "upgrade"])

def check_and_install_module(module_name):
    try:
        __import__(module_name)
        print(f"{module_name} ist bereits installiert.")
    except ImportError:
        print(f"{module_name} wird installiert...")
        subprocess.check_call(["sudo", "apt", "install", f"python3-{module_name}"])

def check_and_install_modules(module_names):
    for module_name in module_names:
        check_and_install_module(module_name)
    print("Alle erforderlichen Module sind installiert.")

def create_service():
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

    # Reload systemd daemon
    os.system("sudo systemctl daemon-reload")

    # Starte den Dienst
    os.system("sudo systemctl start divera_websocket")
    print("Divera WebSocket Dienst erfolgreich gestartet!")

    # Aktiviere den Dienst, um beim Booten zu starten
    os.system("sudo systemctl enable divera_websocket")
    print("Divera WebSocket Dienst aktiviert, um beim Booten zu starten!")

    # Überprüfe den Status des Dienstes
    os.system("sudo systemctl status divera_websocket")

def create_config():
    config = {}
    print("DIVERA 24/7 Setup Hilfe.")
    print("Dieses Setup hilft dir die korrekte Config Datei für das Divera Script zu erstellen. Bitte trage deine Daten Schritt für Schritt ein.")
    # Die folgende Zeile setzt den Standardwert auf "DEIN-API-KEY", falls keine Eingabe erfolgt
    config["api_key"] = input("Bitte geben Sie den Privaten API-Schlüssel aus deinem Divera Account ein. (default: DEIN-API-KEY): ") or "DEIN-API-KEY"
    config["max_log_file_size"] = input("Bitte geben Sie die maximale Logfile größe ein. (default: 5MB): ") or 5
    config["backup_count"] = input("Bitte geben Sie die Anzahl der maximalen Logfile Dateien ein. (default: 5): ") or 5
    print("Modus 1 = Wenn sich der Status von 6 auf != 6 oder von !=6 auf 6 eine Mitteilung senden.")
    print("Modus 2 = Bei jeder Statusänderung eine Mitteilung senden.")
    print("Modus 3 = Wenn in den wunsch Status gewechselt wird.")
    # Die folgende Zeile setzt den Standardwert auf 2, falls keine Eingabe erfolgt
    config["mode"] = int(input("Bitte wählen Sie einen Modus. (default: 1): ") or 1)
    print("Bitte wählen deinen Ziel Status falls du Modus 3 gewählt hast.")
    # Die folgende Zeile setzt den Standardwert auf 2, falls keine Eingabe erfolgt
    config["destination_fms"] = int(input("Bitte geben Sie den Ziel-FMS-Status ein. (default: 2): ") or 2)
    # Die folgende Zeile setzt den Standardwert auf False, falls keine Eingabe erfolgt
    config["auto_archiv"] = input("Soll die Autoarchivierung für die Mitteilungen aktiviert werden? (true/false, default: false): ").lower() == "true"
    # Die folgende Zeile setzt den Standardwert auf 1, falls keine Eingabe erfolgt
    config["autoarchive_days"] = int(input("Bitte geben Sie die Anzahl der Tage für die Autoarchivierung ein. (default: 1): ") or 1)
    # Die folgende Zeile setzt den Standardwert auf 0, falls keine Eingabe erfolgt
    config["autoarchive_hours"] = int(input("Bitte geben Sie die Anzahl der Stunden für die Autoarchivierung ein. (default: 0): ") or 0)
    # Die folgende Zeile setzt den Standardwert auf 0, falls keine Eingabe erfolgt
    config["autoarchive_minutes"] = int(input("Bitte geben Sie die Anzahl der Minuten für die Autoarchivierung ein. (default: 0): ") or 0)
    # Die folgende Zeile setzt den Standardwert auf 0, falls keine Eingabe erfolgt
    config["autoarchive_seconds"] = int(input("Bitte geben Sie die Anzahl der Sekunden für die Autoarchivierung ein. (default: 0): ") or 0)
    # Die folgende Zeile setzt den Standardwert auf True, falls keine Eingabe erfolgt
    config["send_push"] = input("Soll das Senden von Push-Benachrichtigungen aktiviert werden? (true/false, default: false): ").lower() == "true"
    # Die folgende Zeile setzt den Standardwert auf False, falls keine Eingabe erfolgt
    config["send_mail"] = input("Soll das Senden von E-Mails aktiviert werden? (true/false, default: false): ").lower() == "true"
    print("Benachrichtigungs ID")
    print("2 = Alle des Standortes, 3 = Ausgewählte Gruppen, 4 = Ausgewählte Benutzer")
    print("Bei ID = 3 müssen Sie die Gruppen-ID eingeben die Sie benachrichtigen möchten.")
    print("Bei ID = 4 müssen Sie den Primärschlüssel des Benutzers eingeben der benachrichtigt werden soll. Mehrere Benutzer können durch Kommas getrennt eingeben werden.")
    # Die folgende Zeile setzt den Standardwert auf 4, falls keine Eingabe erfolgt
    config["notification_type"] = input("Bitte geben Sie den Benachrichtigungstyp ein (default: 4): ") or "4"
    # Die folgende Zeile setzt den Standardwert auf True, falls keine Eingabe erfolgt
    config["private_mode"] = input("Soll der private Modus für die Mitteilung aktiviert werden? (true/false, default: false): ").lower() == "true"
    # Die folgende Zeile setzt den Standardwert auf ["220053"], falls keine Eingabe erfolgt
    config["users_primaerschluessel"] = [input("Bitte geben Sie den Primärschlüssel des Benutzers ein. (default: 220053): ") or "220053"]
    # Die folgende Zeile setzt den Standardwert auf ["138728"], falls keine Eingabe erfolgt
    config["groups_divera"] = [input("ID der Gruppe (bedingt Benachrichtigungstyp = 3). Bitte geben Sie die Divera-Gruppen-ID ein. (default: 138728): ") or "138728"]
    # Die folgende Zeile setzt den Standardwert auf "Änderung Fahrzeugstatus!", falls keine Eingabe erfolgt
    config["message_titel"] = input("ID des Benutzers (bedingt Benachrichtigungstyp = 4). Bitte geben Sie den Titel der Nachricht ein. (default: Änderung Fahrzeugstatus!): ") or "Änderung Fahrzeugstatus!"
    config["status_dict"] = {}

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

def main():
    # Installiere sudo
    install_sudo()

    # Update und Upgrade
    update_upgrade()

    # Überprüfe und installiere erforderliche Module
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

    # Erstelle Konfigurationsdatei
    create_config()

    # Erstelle den Dienst
    create_service()

if __name__ == "__main__":
    main()