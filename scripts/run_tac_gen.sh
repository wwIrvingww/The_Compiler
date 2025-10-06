#!/usr/bin/env bash
set -e
echo "[RUN_TAC_GEN] Ejecutando DriverGen.py y redirigiendo salidas..."
# Salida estándar -> pretty_tac, stderr -> server.log
python3 src/DriverGen.py input.cps

