#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
echo "[1/2] Running AuraLoop VTO unit, privacy, CIEDE2000 & budget ledger tests..."
python3 -m unittest discover -s tests -v

echo "[2/2] Running 6-stage AuraLoop VTO consultation demo..."
python3 -m auraloop_vto.cli demo --mode simulated --seed 42 --out-dir artifacts
echo "Done. Artifacts written to artifacts/latest_consultation.json and artifacts/latest_consultation.md."
