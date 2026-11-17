#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

[[ $# == 0 ]] || { echo 'Execute sem argumentos.' >&2; exit 1; }
[[ -f .env ]] || { echo 'Execute ./criar-banco.sh primeiro.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3,12))' || { echo 'Python 3.12 ou mais atualizado.' >&2; exit 1; }

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
SG_PYTHON='.venv/bin/python'
SG_MARKER='.venv/segredo-shell-dependencias.sha256'
SG_DIGEST="$(cat requirements.txt constraints-tested.txt | sha256sum | cut -d ' ' -f 1)"
if [[ ! -f "$SG_MARKER" ]] || [[ "$(cat "$SG_MARKER")" != "$SG_DIGEST" ]]; then
  echo 'Instalando dependências...'
  "$SG_PYTHON" -m pip install -q -r requirements.txt -c constraints-tested.txt
  printf '%s\n' "$SG_DIGEST" > "$SG_MARKER"
fi

SG_STATE="$("$SG_PYTHON" - <<'PY'
import socket,sys
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.db import Base,engine
from app.models import User,Offer
try:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',8000))
except OSError:
    sys.exit('A porta 8000 já está em uso.')
try:
    Base.metadata.create_all(engine())
    with Session(engine()) as db:
        admin=db.scalar(select(func.count()).select_from(User).where(User.role=='ADMIN',User.active.is_(True)))
        offers=db.scalar(select(func.count()).select_from(Offer))
    print(int(admin>0),int(offers==0))
except Exception:
    sys.exit('Confira o MySQL e a conexão no arquivo .env.')
PY
)"
read -r SG_ADMIN SG_EMPTY <<< "$SG_STATE"
if [[ "$SG_ADMIN" == 0 ]]; then
  "$SG_PYTHON" -m app.cli create-admin
fi
if [[ "$SG_EMPTY" == 1 ]]; then
  read -r -p 'Cadastrar dados de exemplo? [S/n]: ' SG_SEED
  case "${SG_SEED,,}" in ''|s|sim) "$SG_PYTHON" -m app.cli seed-demo >/dev/null ;; esac
fi

echo 'Segredo Gelado: http://localhost:8000/docs'
exec "$SG_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
