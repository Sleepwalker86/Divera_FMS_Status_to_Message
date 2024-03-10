# Fahrzeugstatusüberwachungs Skript für Divera 24/7

Dieses Python-Skript überwacht den Status von Fahrzeugen und benachrichtigt Benutzer per E-Mail und Push-Nachricht, wenn ein Fahrzeugstatus von oder zu 6 wechselt.

## Voraussetzungen
Python 3

Module: urllib.request, json, smtplib, email.mime, os, datetime, logging

## Konfiguration
Das Skript erwartet eine Konfigurationsdatei config.json, in der die erforderlichen Informationen wie API-Schlüssel, E-Mail-Einstellungen und Empfängeradressen festgelegt sind. Eine Beispieldatei example-config.json ist im Repository enthalten.
Mit dem Parametern "email_enable" und "push_enable" können die Funktionen aktiviert (true) bzw. deaktiviert (false) werden
Sie müssen diese Datei kopieren und entsprechend Ihren Informationen anpassen.
```bash
cp example-config.json config.json
```
```json
{
    "api_key": "YOUR-API-KEY",
    "email_enable": "true",
    "sender_email": "sender@example.de",
    "email_password": "YOUR-EMAIL-PASSWORD",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "receiver_emails": [
        "receiver1@example.de",
        "receiver2@example.de"
    ],
    "push_enable": "true",
    "message_users_fremdschluessel": "1000,1001",
    "message_rics": "group1, group2",
    "status_dict": {}
}
```

## Verwendung
Führen Sie das Skript aus, und verwenden Sie einen Cronjob, um regelmäßig den Fahrzeugstatus zu überprüfen.

```bash
crontab -e

*/5 * * * * /usr/bin/python3 /home/pi/Divera_FMS/main.py >> /home/pi/Divera_FMS/log.txt 2>&1
```

Dieser Cronjob überprüft alle 5 Minuten den Fahrzeugstatus und protokolliert die Ausgabe in die Datei log.txt.



# Vehicle Status Monitoring Script for Divera 24/7

This Python script monitors the status of vehicles and notifies users via email and push notification when a vehicle status changes to or from 6.

## Requirements
Python 3

Modules: urllib.request, json, smtplib, email.mime, os, datetime, logging

## Configuration
The script expects a configuration file `config.json` where the required information such as API key, email settings, and receiver addresses are set. An example file `example-config.json` is included in the repository.
The parameters 'email_enable' and 'push_enable' can be used to enable (true) or disable (false) the respective functionalities.
You need to copy this file and adjust it according to your information.

```bash
cp example-config.json config.json
```

```json
{
    "api_key": "YOUR-API-KEY",
    "email_enable": "true",
    "sender_email": "sender@example.de",
    "email_password": "YOUR-EMAIL-PASSWORD",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "receiver_emails": [
        "receiver1@example.de",
        "receiver2@example.de"
    ],
    "push_enable": "true",
    "message_users_fremdschluessel": "1000,1001",
    "message_rics": "group1, group2",
    "status_dict": {}
}
```
## Usage

Run the script and use a cron job to regularly check the vehicle status.

```bash
crontab -e

*/5 * * * * /usr/bin/python3 /home/pi/Divera_FMS/main.py >> /home/pi/Divera_FMS/log.txt 2>&1
```
This cron job checks the vehicle status every 5 minutes and logs the output to the file log.txt.

