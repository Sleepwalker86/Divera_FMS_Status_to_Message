# Divera 24/7 Fahrzeugstatus → Mitteilung — v4.0.0

Da ich alle meine Bausteine kostenlos zur Verfügung stelle und ich das auch gerne beibehalten möchte, würde ich mich über eine kleine PayPal-Spende freuen. Vielen Dank für deine Unterstützung.

## ☕ Unterstützung

[Spende eine kleine Aufwandsentschädigung](https://www.paypal.com/donate/?hosted_button_id=SHU2PHYACRRMN)

---

# Beschreibung

Dieses Python-Skript überwacht Fahrzeugstatusänderungen in Divera 24/7 in Echtzeit über die WebSocket-Schnittstelle und versendet automatisch Divera-Mitteilungen an definierte Empfänger.

Das Skript unterstützt mehrere Organisationen (UCRs) gleichzeitig und erkennt die verfügbaren Organisationen automatisch über den hinterlegten API-Schlüssel.

---

# Funktionen

* Echtzeitüberwachung von Fahrzeugstatusänderungen
* Unterstützung mehrerer Organisationen (UCRs)
* Automatische Erkennung aller verfügbaren Organisationen
* Individuelle Empfänger je Organisation
* Versand an Gruppen oder Benutzer
* Mehrere Benachrichtigungsmodi
* Mehrere Benachrichtigungsziele
* Automatische Wiederverbindung bei Verbindungsabbrüchen
* Duplikat-Filter gegen doppelte Benachrichtigungen
* Automatische Service-Installation unter Linux
* Push-Benachrichtigungen optional
* E-Mail-Benachrichtigungen optional
* Automatische Archivierung von Mitteilungen

---

# Benachrichtigungsmodi

## Modus 1

Eine Mitteilung wird versendet, wenn sich der Fahrzeugstatus

* von Status 6 auf einen anderen Status ändert oder
* von einem anderen Status auf Status 6 ändert.

## Modus 2

Bei jeder Fahrzeugstatusänderung wird eine Mitteilung versendet.

## Modus 3

Eine Mitteilung wird versendet, sobald ein definierter Zielstatus erreicht wird.

Beispiel:

```text
Zielstatus = 2

1 → 2 = Nachricht
6 → 2 = Nachricht
3 → 2 = Nachricht
2 → 2 = keine Nachricht
```

---

# Benachrichtigungsziele

## source

Die Nachricht wird an die Empfänger der Organisation gesendet, aus der das Fahrzeug stammt.

Beispiel:

```text
Fahrzeug gehört zu Organisation A
→ Nachricht an Empfänger von Organisation A
```

## global

Alle Statusänderungen werden an die Empfänger der ersten konfigurierten Hauptorganisation gesendet.

Beispiel:

```text
Fahrzeug aus Organisation A
Fahrzeug aus Organisation B
Fahrzeug aus Organisation C

→ Alle Nachrichten gehen an dieselben Empfänger
```

## cluster

Es werden ausschließlich Fahrzeuge eines bestimmten Clusters berücksichtigt.

Beispiel:

```text
Ziel-Cluster-ID = 12345

Fahrzeug Cluster 12345 → Nachricht
Fahrzeug Cluster 67890 → keine Nachricht
```

## all

Jede Statusänderung wird an **alle** konfigurierten Organisationen gesendet – pro Organisation ein eigener API-Aufruf mit den jeweils hinterlegten Empfängern (Gruppen oder Benutzer).

Beispiel:

```text
Organisation A → Gruppen [101, 102]
Organisation B → Benutzer [220053]
Organisation C → Gruppen [305]

→ Statusänderung eines beliebigen Fahrzeugs sendet Nachrichten an A, B und C
```

---

# Voraussetzungen

* Linux (z. B. Raspberry Pi OS, Debian, Ubuntu)
* Python 3
* Git
* sudo

Die benötigten Python-Module werden während des Setups automatisch installiert.

---

# Installation

```bash
sudo apt update
sudo apt install git -y

git clone https://github.com/Sleepwalker86/Divera_FMS_Status_to_Message.git

cd Divera_FMS_Status_to_Message

sudo python3 setup.py
```

---

# Einrichtung

Der Setup-Assistent führt durch die komplette Konfiguration.

Folgende Einstellungen werden abgefragt:

* Privater Divera API-Key
* Zu überwachende Organisationen
* Benachrichtigungsmodus
* Zielstatus (bei Modus 3)
* Archivierungseinstellungen
* Push-Benachrichtigungen
* E-Mail-Benachrichtigungen
* Privater Modus
* Titel der Mitteilung
* Benachrichtigungsziel
* Empfänger pro Organisation

Am Ende werden automatisch erstellt:

* `config.json`
* `divera_websocket.service`

Anschließend wird der Dienst automatisch gestartet.

---

# Empfänger konfigurieren

Für jede Organisation können eigene Empfänger hinterlegt werden.

## Benachrichtigungstyp 3

Versand an ausgewählte Divera-Gruppen.

Beispiel:

```text
Gruppe Atemschutz
Gruppe Führung
Gruppe ELW
```

## Benachrichtigungstyp 4

Versand an ausgewählte Benutzer.

Beispiel:

```text
Max Mustermann
Erika Musterfrau
```

---

# Logs

Alle Meldungen und Fehler werden in der Datei

```text
log.txt
```

im Projektverzeichnis gespeichert.

---

# Serviceverwaltung

## Status anzeigen

```bash
sudo systemctl status divera_websocket
```

## Dienst starten

```bash
sudo systemctl start divera_websocket
```

## Dienst stoppen

```bash
sudo systemctl stop divera_websocket
```

## Dienst neu starten

```bash
sudo systemctl restart divera_websocket
```

## Dienst beim Systemstart aktivieren

```bash
sudo systemctl enable divera_websocket
```

## Dienst beim Systemstart deaktivieren

```bash
sudo systemctl disable divera_websocket
```

---

# Aktualisierung

```bash
cd Divera_FMS_Status_to_Message

git pull

sudo systemctl restart divera_websocket
```

---

# Fehlerbehebung

## Logdatei anzeigen

```bash
tail -f log.txt
```

## Service-Logs anzeigen

```bash
journalctl -u divera_websocket -f
```

## Service neu laden

```bash
sudo systemctl daemon-reload
sudo systemctl restart divera_websocket
```

---

# Sicherheitshinweis

Die Datei `config.json` enthält sensible Daten wie den Divera API-Key.

Es wird empfohlen, die Datei nicht zu veröffentlichen und in die `.gitignore` aufzunehmen.

Beispiel:

```gitignore
config.json
__pycache__/
*.log
```

---

# Lizenz

Dieses Projekt wird kostenlos zur Verfügung gestellt.

Die Nutzung erfolgt auf eigene Verantwortung.
