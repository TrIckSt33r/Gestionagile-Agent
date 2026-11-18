#!/bin/sh
# Entry point per il container dell'agent VPS.
# Legge AGENT_TOKEN e AGENT_URL dalle variabili d'ambiente.
exec python agent.py
