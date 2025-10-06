#!/usr/bin/env bash
set -e
echo "[RUN_TAC_GEN] Ejecutando DriverGen.py y redirigiendo salidas..."
# Salida estándar -> pretty_tac, stderr -> server.log
python3 src/DriverGen.py input.cps > input.cps.pretty_tac 2> input.cps.server.log
# Fallback: si hace falta, generar raw_tac (aquí usamos copia del pretty como fallback)
cp -f input.cps.pretty_tac input.cps.raw_tac
echo "[RUN_TAC_GEN] Hecho. Archivos generados:"
ls -l input.cps.*
