from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from app.config import settings
from app.db import get_db
from app.models import User

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash('dummy-password-for-timing-only')
oauth = OAuth2PasswordBearer(tokenUrl='/auth/token')

def issue_token(user_id):
    cfg = settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user_id), 'iat': now, 'exp': now + timedelta(minutes=cfg.jwt_minutes),
                       'iss': 'segredo-gelado', 'aud': 'segredo-api'}, cfg.jwt_secret, algorithm='HS256')

def current_user(token=Depends(oauth), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, settings().jwt_secret, algorithms=['HS256'],
                             issuer='segredo-gelado', audience='segredo-api',
                             options={'require': ['sub', 'iat', 'exp', 'iss', 'aud']})
        user = db.get(User, int(payload['sub']))
        if not user or not user.active:
            raise ValueError('Usuário indisponível')
        return user
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(401, 'Token inválido ou expirado.', headers={'WWW-Authenticate': 'Bearer'})

def roles(*allowed):
    def check(user=Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, 'Sem permissão para esta operação.')
        return user
    return check
