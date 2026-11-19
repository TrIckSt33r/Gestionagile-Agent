# Installazione Agent su VPS Cliente (Linux + systemd)

## 1. Preparazione utente e directory
```bash
# Utente di servizio (senza shell, no login)
sudo useradd -r -s /bin/false -d /opt/monitor-agent monitor-agent

# Directory applicazione
sudo mkdir -p /opt/monitor-agent
sudo chown monitor-agent:monitor-agent /opt/monitor-agent

# Directory stato (persistenza contatori rete)
sudo mkdir -p /var/lib/monitor-agent
sudo chown monitor-agent:monitor-agent /var/lib/monitor-agent

# Directory config (solo root + monitor-agent possono leggere)
sudo mkdir -p /etc/monitor-agent
sudo chown root:monitor-agent /etc/monitor-agent
sudo chmod 750 /etc/monitor-agent
```

## 2. Deploy codice
```bash
# Come root o utente con sudo
cd /opt/monitor-agent

# Clona solo la cartella agent/ del repo (o copia i file manualmente)
git clone --filter=blob:none --sparse https://github.com/BrizioFab/Gestionagile.git .
git sparse-checkout set agent
mv agent/* .
rm -rf agent .git

# Virtualenv e dipendenze
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install psutil requests
```

## 3. Configurazione
```bash
# Copia esempio e modifica
sudo cp .env.example /etc/monitor-agent/.env
sudo chown root:monitor-agent /etc/monitor-agent/.env
sudo chmod 640 /etc/monitor-agent/.env

# EDIT con i valori dalla UI Gestionagile:
# - AGENT_TOKEN = token mostrato in "Nuove credenziali agente"
# - AGENT_HMAC_KEY = chiave HMAC mostrata insieme al token
# - AGENT_URL = https://tuo-gestionagile.example.com/api/agent/report
sudoedit /etc/monitor-agent/.env
```

## 4. Installa servizio systemd
```bash
sudo cp monitor-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-agent
```

## 5. Verifica
```bash
# Stato servizio
systemctl status monitor-agent

# Log in tempo reale
journalctl -u monitor-agent -f

# Ultimi 50 log
journalctl -u monitor-agent -n 50
```

## 6. Aggiornamenti futuri
```bash
cd /opt/monitor-agent
git pull origin main   # se hai clona il repo completo
# oppure ricopia i file aggiornati
sudo systemctl restart monitor-agent
```

## Variabili d'ambiente supportate
| Variabile | Obbligatoria | Default | Descrizione |
|-----------|-------------|---------|-------------|
| `AGENT_TOKEN` | Sì | — | Token Bearer (da UI) |
| `AGENT_URL` | Sì | — | Endpoint POST /api/agent/report |
| `AGENT_HMAC_KEY` | No | — | Chiave HMAC per-server (da UI) |
| `AGENT_INTERVAL` | No | `4` | Secondi tra invii (min 4) |
| `AGENT_DISK_PATH` | No | `/` | Path per `disk_percent` |
| `AGENT_STATE_FILE` | No | `~/.local/state/monitor-agent/state.json` | File persistenza contatori rete |

## Sicurezza
- Il file `/etc/monitor-agent/.env` contiene segreti: **permessi 640**, owner `root:monitor-agent`
- L'agente gira come utente `monitor-agent` (no root, no shell)
- systemd hardening: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`
- Comunicazione solo HTTPS verso endpoint Gestionagile
- HMAC stateless: integrità + anti-replay (±60s tolleranza timestamp)