import email
import html
import hashlib
import imaplib
import json
import logging
import os
import re
import time
from email.header import decode_header, make_header
from email.utils import parseaddr
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
STATE = BASE / 'state.json'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def header(value):
    try:
        return str(make_header(decode_header(value or '')))
    except Exception:
        return value or ''


def body_text(msg):
    parts = msg.walk() if msg.is_multipart() else [msg]
    plain, rich = [], []
    for part in parts:
        if part.get_content_disposition() == 'attachment':
            continue
        typ = part.get_content_type()
        if typ not in ('text/plain', 'text/html'):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        encoding = part.get_content_charset() or 'utf-8'
        text = payload.decode(encoding, errors='replace')
        if typ == 'text/plain':
            plain.append(text)
        else:
            rich.append(text)
    if plain:
        text = '\n'.join(plain)
    else:
        text = '\n'.join(rich)
        text = re.sub(r'(?is)<(script|style).*?>.*?</\1>', '', text)
        text = re.sub(r'(?i)<br\s*/?>|</p>|</div>', '\n', text)
        text = html.unescape(re.sub(r'<[^>]+>', '', text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:650] + ('…' if len(text) > 650 else '')


def post(webhook, msg):
    sender = header(msg.get('From'))
    subject = header(msg.get('Subject')) or '(Pealkirjata)'
    include_preview = os.getenv('INCLUDE_BODY_PREVIEW', 'false').lower() == 'true'
    snippet = body_text(msg) or '(Kirja tekst puudub või sisaldab ainult manuseid)' if include_preview else None
    payload = {
        'username': 'Culine • Infomeil',
        'allowed_mentions': {'parse': []},
        'embeds': [{
            'title': ('📩 ' + subject)[:256],
            'color': 0x3B82F6,
            'fields': [
                {'name': 'Saatja', 'value': sender[:1024] or 'Teadmata'},
                *([{'name': 'Sisu eelvaade', 'value': snippet[:1024]}] if include_preview else []),
            ],
            'footer': {'text': 'Õpilasfirma • uus infomeil'}
        }]
    }
    req = Request(webhook, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json', 'User-Agent':'CulineMailNotifier/1.0'}, method='POST')
    for attempt in range(5):
        try:
            with urlopen(req, timeout=20) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f'Discord vastas {response.status}')
            return
        except HTTPError as exc:
            if exc.code == 429:
                delay = float(json.loads(exc.read().decode()).get('retry_after', 2))
                time.sleep(min(delay + .5, 60))
                continue
            raise
        except URLError:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError('Discordi teavitus ei õnnestunud')


def load_state():
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_state(state):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state), encoding='utf-8')
    tmp.replace(STATE)


def check():
    server = os.environ['IMAP_HOST']
    user = os.environ['MAIL_USER']
    pwd = os.environ['MAIL_PASSWORD']
    webhook = os.environ['DISCORD_WEBHOOK_URL']
    port = int(os.getenv('IMAP_PORT', '993'))
    folder = os.getenv('MAIL_FOLDER', 'INBOX')
    state = load_state()
    with imaplib.IMAP4_SSL(server, port) as client:
        client.login(user, pwd)
        typ, _ = client.select(folder, readonly=True)
        if typ != 'OK':
            raise RuntimeError('Postkasti avamine ebaõnnestus')
        typ, data = client.uid('search', None, 'ALL')
        if typ != 'OK':
            raise RuntimeError('Kirjade loend ebaõnnestus')
        uids = [int(x) for x in data[0].split()]
        typ, uidval = client.response('UIDVALIDITY')
        uid_validity = (uidval or [b''])[0]
        state_key = hashlib.sha256(f'{server}:{user}:{folder}:{uid_validity!r}'.encode()).hexdigest()
        if state.get('key') != state_key:
            # Esimesel käivitamisel ära saada vanade kirjade teavitusi.
            state = {'key': state_key, 'last_uid': max(uids, default=0)}
            save_state(state)
            logging.info('Postkast ühendatud. Jälgin ainult uusi kirju.')
            return
        last_uid = int(state.get('last_uid', 0))
        for uid in sorted(x for x in uids if x > last_uid):
            typ, content = client.uid('fetch', str(uid), '(BODY.PEEK[])')
            if typ != 'OK':
                raise RuntimeError(f'Kirja {uid} lugemine ebaõnnestus')
            raw = next((part[1] for part in content if isinstance(part, tuple)), None)
            if raw is None:
                raise RuntimeError(f'Kirja {uid} sisu puudub')
            msg = email.message_from_bytes(raw)
            post(webhook, msg)
            state['last_uid'] = uid
            save_state(state)
            logging.info('Teavitus saadetud: %s', header(msg.get('Subject')))
        client.logout()


def main():
    required = ('IMAP_HOST', 'MAIL_USER', 'MAIL_PASSWORD', 'DISCORD_WEBHOOK_URL')
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise SystemExit('Täida .env failis: ' + ', '.join(missing))
    if os.getenv('RUN_ONCE', '').lower() == 'true':
        check()
        return
    seconds = max(60, int(os.getenv('CHECK_INTERVAL_SECONDS', '120')))
    logging.info('Infomeili teavitaja käivitatud; kontroll iga %d sekundi järel', seconds)
    while True:
        try:
            check()
        except Exception as exc:
            logging.exception('Kontrolli viga: %s', exc)
        time.sleep(seconds)


if __name__ == '__main__':
    main()
