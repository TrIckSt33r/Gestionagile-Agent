#!/usr/bin/env python3
"""AGENTE DI MONITORAGGIO VPS (Scenario A).

Gira sul server del cliente, legge le risorse con psutil e le invia in PUSH
a Gestionagile tramite POST /api/agent/report.

Variabili d'ambiente:
  AGENT_TOKEN      token univoco del server (generato da Gestionagile)
  AGENT_URL        URL dell'endpoint, es. https://gestione.example.com/api/agent/report
  AGENT_INTERVAL   secondi tra una rilevazione e l'altra (default 4)
  AGENT_DISK_PATH  percorso da monitorare per lo spazio disco (default /)
  AGENT_STATE_FILE file dove salvare lo stato dei contatori di rete
                   (default ~/.local/state/monitor-agent/state.json)
"""

import json
import os
import signal
import sys
import time
from pathlib import Path

import psutil
import requests


DEFAULT_INTERVAL = 4
DEFAULT_DISK_PATH = "/"
DEFAULT_STATE_FILE = str(
    Path.home() / ".local" / "state" / "monitor-agent" / "state.json"
)

running = True


def _handle_signal(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def load_config() -> dict:
    """Legge la configurazione dalle variabili d'ambiente."""
    token = os.getenv("AGENT_TOKEN")
    url = os.getenv("AGENT_URL")
    if not token or not url:
        print("ERRORE: AGENT_TOKEN e AGENT_URL sono obbligatori.", file=sys.stderr)
        sys.exit(1)

    try:
        interval = int(os.getenv("AGENT_INTERVAL", DEFAULT_INTERVAL))
    except ValueError:
        interval = DEFAULT_INTERVAL

    disk_path = os.getenv("AGENT_DISK_PATH", DEFAULT_DISK_PATH)
    state_file = os.getenv("AGENT_STATE_FILE", DEFAULT_STATE_FILE)

    return {
        "token": token,
        "url": url,
        "interval": max(interval, 4),
        "disk_path": disk_path,
        "state_file": state_file,
    }


def load_state(state_file: str) -> dict:
    """Carica lo stato precedente (contatori di rete) da file."""
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"net_sent_prev": None, "net_recv_prev": None}


def save_state(state_file: str, state: dict) -> None:
    """Salva lo stato su file."""
    try:
        Path(state_file).parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError as error:
        print(f"AVVISO: impossibile salvare lo stato: {error}", file=sys.stderr)


def collect_metrics(disk_path: str, state: dict) -> dict | None:
    """Raccoglie le metriche del sistema e aggiorna lo stato della banda.

    Restituisce None se non ci sono abbastanza dati (prima esecuzione senza
    stato precedente): in questo caso si salva lo stato e si riprova al ciclo
    successivo.
    """
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(disk_path).percent
        net = psutil.net_io_counters()
    except Exception as error:  # noqa: BLE001
        print(f"ERRORE raccolta metriche: {error}", file=sys.stderr)
        return None

    net_sent = net.bytes_sent
    net_recv = net.bytes_recv

    sent_prev = state.get("net_sent_prev")
    recv_prev = state.get("net_recv_prev")

    # Prima esecuzione: non abbiamo un riferimento precedente.
    if sent_prev is None or recv_prev is None:
        state["net_sent_prev"] = net_sent
        state["net_recv_prev"] = net_recv
        return None

    # Rilevamento reboot del server: i contatori di psutil ripartono da zero.
    # Se i valori attuali sono minori di quelli salvati, resettiamo il baseline.
    if net_sent < sent_prev or net_recv < recv_prev:
        sent_delta = net_sent
        recv_delta = net_recv
    else:
        sent_delta = net_sent - sent_prev
        recv_delta = net_recv - recv_prev

    state["net_sent_prev"] = net_sent
    state["net_recv_prev"] = net_recv

    return {
        "cpu_percent": round(cpu, 2),
        "ram_percent": round(ram, 2),
        "disk_percent": round(disk, 2),
        "net_sent": max(0, int(sent_delta)),
        "net_recv": max(0, int(recv_delta)),
    }


def send_report(url: str, token: str, metrics: dict) -> bool:
    """Invia le metriche all'endpoint. Restituisce True se successo."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, json=metrics, headers=headers, timeout=10)
        if response.status_code == 200:
            return True
        print(
            f"ERRORE invio metriche: HTTP {response.status_code} {response.text}",
            file=sys.stderr,
        )
        return False
    except requests.RequestException as error:
        print(f"ERRORE invio metriche: {error}", file=sys.stderr)
        return False


def main() -> None:
    config = load_config()
    state = load_state(config["state_file"])

    print(
        f"Agente avviato: intervallo {config['interval']}s, "
        f"disco {config['disk_path']}, endpoint {config['url']}"
    )

    while running:
        metrics = collect_metrics(config["disk_path"], state)

        if metrics is not None:
            if send_report(config["url"], config["token"], metrics):
                save_state(config["state_file"], state)
                print(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"CPU={metrics['cpu_percent']}% "
                    f"RAM={metrics['ram_percent']}% "
                    f"Disco={metrics['disk_percent']}% "
                    f"Sent={metrics['net_sent']}B Recv={metrics['net_recv']}B"
                )
            else:
                # In caso di errore non salviamo lo stato: riproviamo al ciclo
                # successivo con gli stessi contatori precedenti.
                pass
        else:
            # Prima esecuzione: salviamo il baseline e aspettiamo il prossimo ciclo.
            save_state(config["state_file"], state)
            print(
                f"[{time.strftime('%H:%M:%S')}] Prima rilevazione: baseline salvata."
            )

        time.sleep(config["interval"])

    print("Agente arrestato.")


if __name__ == "__main__":
    main()
