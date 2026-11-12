#!/usr/bin/env bash
# Preparacion inicial de una instancia EC2 (Ubuntu 24.04, t3.medium).
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
mkdir -p "$HOME/edutrack"
echo "Cierra sesion y vuelve a entrar para usar docker sin sudo."
echo "Luego clona los 3 repos en ~/edutrack y crea edutrack-backend/.env"
