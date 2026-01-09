#!/bin/bash
# Script de ayuda para ejecutar AppTwitter

# Asegurar que Poetry esté en el PATH
export PATH="$HOME/.local/bin:$PATH"

# Ejecutar comando
poetry run app "$@"
