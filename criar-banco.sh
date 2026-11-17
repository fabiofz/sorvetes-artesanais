#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

[[ $# == 0 ]] || { echo 'Execute sem argumentos.' >&2; exit 1; }
[[ ! -e .env ]] || { echo 'O arquivo .env já existe. Nada foi alterado.'; exit 0; }
sudo -v
if [[ ! -x /usr/sbin/mysqld ]] && ! command -v mysqld >/dev/null; then
  echo 'Instalando MySQL...'
  sudo apt-get update -qq
  sudo apt-get install -y -qq mysql-server
fi
if [[ -d /run/systemd/system ]]; then
  sudo systemctl start mysql
else
  sudo service mysql start
fi

SG_TMP="$(mktemp -d "${TMPDIR:-/tmp}/segredo-mysql.XXXXXXXX")"
trap 'rm -rf -- "$SG_TMP"' EXIT
python3 - "$SG_TMP" <<'PY'
from pathlib import Path
import os,secrets,sys
folder=Path(sys.argv[1])
user='segredo_app_'+secrets.token_hex(4)
password=secrets.token_hex(32)
sql=("CREATE DATABASE IF NOT EXISTS segredo_gelado CHARACTER SET utf8mb4;\n"
     f"CREATE USER '{user}'@'localhost' IDENTIFIED BY '{password}';\n"
     f"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON segredo_gelado.* TO '{user}'@'localhost';\n")
env=(f'DATABASE_URL=mysql+pymysql://{user}:{password}@127.0.0.1:3306/segredo_gelado?charset=utf8mb4\n'
     f'JWT_SECRET={secrets.token_hex(32)}\nJWT_MINUTES=30\nPAYMENT_MODE=mock\n')
client=(f'[client]\nuser={user}\npassword={password}\nhost=127.0.0.1\nport=3306\n'
        'protocol=tcp\ndatabase=segredo_gelado\n')
for name,value in [('create.sql',sql),('.env',env),('client.cnf',client)]:
    fd=os.open(folder/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as file:file.write(value)
PY
sudo mysql --protocol=socket < "$SG_TMP/create.sql"
mysql --defaults-extra-file="$SG_TMP/client.cnf" --batch --skip-column-names -e 'SELECT 1' >/dev/null
(umask 077; set -C; cat "$SG_TMP/.env" > .env)
echo 'Banco pronto.'
