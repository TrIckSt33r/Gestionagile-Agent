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

# Clona il repo dell'agente
git clone https://github.com/TrIckSt33r/Gestionagile-Agent.git .

# Virtualenv e dipendenze
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 3. Configurazione
```bash
# Copia esempio e modifica
sudo cp .env.example /etc/monitor-agent/.env
sudo chown root:monitor-agent /etc/monitor-agent/.env
sudo chmod 640 /etc/monitor-agent/.env

# EDIT con i valori dalla UI Gestionagile (pagina dettaglio server → "Nuovo token"):
# - AGENT_TOKEN = token mostrato (Authorization: Bearer)
# - AGENT_HMAC_KEY = chiave HMAC mostrata (X-Signature) — **obbligatoria se hai rigenerato il token**
# - AGENT_URL = https://tuo-gestionagile.example.com/api/agent/report
sudoedit /etc/monitor-agent/.env
```

> **Nota HMAC:** Dal momento in cui clicchi "Nuovo token" nella UI, il server genera una coppia **token + chiave HMAC**. Da quel momento l'agente **deve** inviare `AGENT_HMAC_KEY` (header `X-Signature`). Senza, il server rifiuta con 401.

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
sudo git pull
sudo systemctl restart monitor-agent
```

## Variabili d'ambiente supportate
| Variabile | Obbligatoria | Default | Descrizione |
|-----------|-------------|---------|-------------|
| `AGENT_TOKEN` | Sì | — | Token Bearer (da UI) |
| `AGENT_URL` | Sì | — | Endpoint POST /api/agent/report |
| `AGENT_HMAC_KEY` | **Sì\*** | — | Chiave HMAC per-server (da UI, generata con "Nuovo token") |
| `AGENT_INTERVAL` | No | `4` | Secondi tra invii (min 4) |
| `AGENT_DISK_PATH` | No | `/` | Path per `disk_percent` |
| `AGENT_STATE_FILE` | No | `~/.local/state/monitor-agent/state.json` | File persistenza contatori rete |

\* Obbligatoria se il server ha HMAC key (generata cliccando "Nuovo token" in UI). Server senza HMAC key (vecchi token) la saltano per backward compat.

## Sicurezza
- Il file `/etc/monitor-agent/.env` contiene segreti: **permessi 640**, owner `root:monitor-agent`
- L'agente gira come utente `monitor-agent` (no root, no shell)
- systemd hardening: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`
- Comunicazione solo HTTPS verso endpoint Gestionagile
- HMAC stateless: integrità + anti-replay (±60s tolleranza timestamp)