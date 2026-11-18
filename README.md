# Agente di monitoraggio VPS

L'agente gira sul **server del cliente** (VPS), legge le risorse con `psutil`
e le invia in PUSH a Gestionagile tramite l'endpoint `POST /api/agent/report`.

## Prerequisiti

- Python 3.8+
- Accesso al server VPS (root o utente con permessi per leggere le metriche di sistema)

## Installazione

```bash
# 1. Copia la cartella agent/ sul server del cliente
# 2. Installa le dipendenze
pip install -r agent/requirements.txt

# 3. Configura le variabili d'ambiente (esempio)
export AGENT_TOKEN="il_token_generato_da_gestionagile"
export AGENT_URL="https://gestione.tuodominio.com/api/agent/report"
export AGENT_INTERVAL=60
export AGENT_DISK_PATH="/"

# 4. Avvia l'agente
python agent/agent.py
```

## Variabili d'ambiente

| Variabile | Obbligatorio | Default | Descrizione |
|-----------|-------------|---------|-------------|
| `AGENT_TOKEN` | Sì | — | Token del server generato in Gestionagile |
| `AGENT_URL` | Sì | — | URL completa dell'endpoint `/api/agent/report` |
| `AGENT_INTERVAL` | No | `60` | Secondi tra una rilevazione e l'altra |
| `AGENT_DISK_PATH` | No | `/` | Percorso da monitorare per lo spazio disco |
| `AGENT_STATE_FILE` | No | `~/.local/state/monitor-agent/state.json` | File di stato per i contatori di rete |

## systemd (per tenere l'agente attivo)

Crea `/etc/systemd/system/monitor-agent.service`:

```ini
[Unit]
Description=Gestionagile Monitor Agent
After=network.target

[Service]
Type=simple
User=monitor-agent
WorkingDirectory=/opt/monitor-agent
Environment=AGENT_TOKEN=il_token
Environment=AGENT_URL=https://gestione.tuodominio.com/api/agent/report
ExecStart=/usr/bin/python3 agent/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Poi:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-agent
```

## Come funziona la banda

`psutil.net_io_counters()` restituisce byte totali **cumulativi dal boot**.
L'agente salva i valori precedenti in un file di stato e invia la **differenza**
tra due letture consecutive. Dopo un reboot del server i contatori ripartono da
zero: l'agente lo rileva (valore attuale minore del precedente) e resetta il
baseline, evitando valori negativi o sballati.

## Sicurezza

- Il token viaggia in `Authorization: Bearer <token>` su **HTTPS**.
- Il token non è mai salvato in chiaro da Gestionagile (solo hash bcrypt).
- Il file di stato contiene solo contatori di rete, nessun dato sensibile.
