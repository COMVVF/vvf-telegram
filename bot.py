"""Monitor pubblico VVF: nessuna API a pagamento, nessun accesso intranet."""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

BASE = 'https://www.vigilfuoco.it'
STATE = Path('state.json')

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.main = False; self.href = None; self.parts = []; self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main': self.main = True
        if self.main and tag == 'a': self.href = attrs.get('href'); self.parts = []
    def handle_data(self, text):
        if self.href: self.parts.append(text)
    def handle_endtag(self, tag):
        if tag == 'a' and self.href:
            self.links.append((self.href, clean(' '.join(self.parts)))); self.href = None
        if tag == 'main': self.main = False

def clean(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', text))).strip()

def canonical(url):
    p = urllib.parse.urlsplit(urllib.parse.urljoin(BASE, url))
    if p.hostname not in ('www.vigilfuoco.it', 'vigilfuoco.it'): return None
    return urllib.parse.urlunsplit(('https', 'www.vigilfuoco.it', p.path.rstrip('/'), p.query, ''))

def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'VVF-public-news-monitor/1.0'})
    with urllib.request.urlopen(req, timeout=35) as response:
        data = response.read(8_000_001)
        if len(data) > 8_000_000: raise RuntimeError('Risposta fonte troppo grande')
        return data

def telegram(method, payload):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        raise RuntimeError('Manca TELEGRAM_BOT_TOKEN nei Secrets')

    total_wait = 0

    for attempt in range(4):
        if method == 'sendMessage':
            last = getattr(telegram, '_last_send', 0)
            pause = 3.5 - (time.monotonic() - last)
            if pause > 0:
                time.sleep(pause)
            telegram._last_send = time.monotonic()

        req = urllib.request.Request(
            'https://api.telegram.org/bot' + token + '/' + method,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.load(response)

        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise RuntimeError(
                    'Telegram HTTP ' + str(e.code)
                ) from None

            try:
                details = json.loads(e.read().decode())
                wait = int(
                    details.get('parameters', {}).get(
                        'retry_after', 10 * (2 ** attempt)
                    )
                )
            except Exception:
                wait = 10 * (2 ** attempt)

            wait = max(1, wait) + 1

            if attempt == 3 or total_wait + wait > 180:
                raise RuntimeError(
                    'Telegram 429: riprovare tra almeno '
                    + str(wait) + ' secondi'
                ) from None

            print(
                'Telegram 429: attesa di',
                wait,
                'secondi; tentativo',
                attempt + 1
            )
            time.sleep(wait)
            total_wait += wait
            continue

        except Exception:
            raise RuntimeError(
                'Connessione Telegram fallita; '
                'verificare prima di riprovare'
            ) from None

        if not result.get('ok'):
            raise RuntimeError('Telegram ha rifiutato la richiesta')

def category(title, description, url):
    text = (title + ' ' + description).lower()
    rules = [
        ('Concorsi e mobilità', ['concorso', 'concorsi', 'mobilità', 'graduatoria', 'bando', 'assunzion']),
        ('Circolari del Dipartimento', ['circolare', 'circolari', 'nota dipartimentale']),
        ('Normativa e prevenzione incendi', ['prevenzione incendi', 'normativa', 'decreto', 'scia', 'regola tecnica', 'rtv', 'gpl', 'codice di prevenzione']),
        ('Formazione e personale', ['formazione', 'corso', 'corsi', 'personale', 'ordinamento', 'addestramento']),
        ('Soccorso tecnico e procedure operative', ['procedura', 'procedure', 'linee guida', 'soccorso tecnico', 'manuale operativo', 'direttiva']),
    ]
    for label, keywords in rules:
        if any(k in text for k in keywords): return label
    if any(k in text for k in ['dipartimento', 'istituzional', 'capo del corpo', 'protocollo', 'convenzione', 'open data']):
        return 'Notizie istituzionali'
    if '/media/notizie/' in url: return 'Notizie istituzionali'
    return None  # Esclude, di norma, cronaca locale e risultati sportivi.

def rss(data):
    root = ET.fromstring(data)
    items = []
    for node in root.findall('.//item'):
        url = canonical(node.findtext('link', ''))
        title = clean(node.findtext('title', ''))
        desc = clean(node.findtext('description', ''))
        if not url or not title: continue
        label = category(title, desc, url)
        if label: items.append({'url': url, 'title': title, 'description': desc[:500],
            'date': node.findtext('pubDate') or node.findtext('pubdate') or '', 'category': label})
    if not root.findall('.//item'): raise RuntimeError('Feed RSS senza elementi')
    return items

def page_items(data, source):
    parser = Links(); parser.feed(data.decode('utf-8'))
    if not parser.links: raise RuntimeError('Nessun collegamento nel contenuto principale: verificare il sito')
    result = []
    for href, title in parser.links:
        url = canonical(href)
        if not url or url == source['url']: continue
        path = urllib.parse.urlsplit(url).path
        if not (path.startswith(source['prefix']) or path.endswith(('.pdf', '.p7m'))): continue
        if title.lower() in ('home', 'successivo', 'precedente'): continue
        if not title or title.lower() in ('apri', 'leggi tutto', 'scarica', 'download'):
            title = urllib.parse.unquote(path.rsplit('/', 1)[-1]).replace('-', ' ').replace('_', ' ')
        result.append({'url': url, 'title': title[:500], 'description': '', 'date': '', 'category': source['category']})
    if not result: raise RuntimeError('Nessun documento pertinente: verificare configurazione/selettore')
    return result

def fingerprint(item):
    return hashlib.sha256((item['title'] + '\n' + item['description']).encode()).hexdigest()

def save(state):
    temporary = STATE.with_suffix('.tmp'); temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n'); temporary.replace(STATE)

def message(item, updated=False):
    text = '🚒 VVF – Aggiornamenti\n' + item['category'] + '\n\n'
    if updated: text += 'Contenuto aggiornato\n'
    text += item['title'] + '\n'
    if item['description']: text += '\nEstratto della fonte: ' + item['description'] + '\n'
    if item['date']: text += '\nData riportata dalla fonte: ' + item['date'] + '\n'
    return text + '\nFonte ufficiale:\n' + item['url'] + '\n\nBot informativo non ufficiale.'

def run(dry=False):
    config = json.loads(Path('sources.json').read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {'sources': {}, 'seen': {}}
    failures = 0
    for source in config:
        try:
            data = download(source['url'])
            items = rss(data) if source['kind'] == 'rss' else page_items(data, source)
        except Exception:
            print('ERRORE fonte:', source['url']); failures += 1; continue
        initialized = source['url'] in state['sources']
        sent = 0
        for item in reversed(items):
            key, value = item['url'], fingerprint(item)
            old = state['seen'].get(key)
            if old == value: continue
            if initialized:
                if dry:
                    print(message(item, old is not None)); continue
                chat = os.environ.get('TELEGRAM_CHAT_ID')
                if not chat: raise RuntimeError('Manca TELEGRAM_CHAT_ID nei Secrets')
                telegram('sendMessage', {'chat_id': chat, 'text': message(item, old is not None),
                    'link_preview_options': {'is_disabled': True}})
                sent += 1; time.sleep(1.1)
            state['seen'][key] = value
            if not dry: save(state)  # Conserva ogni invio riuscito anche se il successivo fallisce.
        state['sources'][source['url']] = True
        if not dry: save(state)
        print(source['kind'], 'elementi:', len(items), 'inviati:', sent,
              'stato:', 'attivo' if initialized else 'inizializzato senza invii')
    if failures: raise RuntimeError(str(failures) + ' fonti non disponibili; controllare il log')

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--mode', choices=['monitor', 'connect', 'test', 'dry-run'], default='monitor'); args = parser.parse_args()
    if args.mode == 'connect':
        me = telegram('getMe', {})
        updates = telegram('getUpdates', {'timeout': 0, 'allowed_updates': ['message']})
        count = 0
        for update in updates:
            msg = update.get('message', {}); command = msg.get('text', '').split()
            if command and command[0].lower() in ('/id', '/id@' + me['username'].lower()) and msg.get('chat', {}).get('type') in ('group', 'supergroup'):
                chat = msg['chat']['id']
                telegram('sendMessage', {'chat_id': chat, 'text': 'ID di questo gruppo: ' + str(chat) + '\nInseriscilo nel Secret TELEGRAM_CHAT_ID su GitHub.'}); count += 1
        if updates: telegram('getUpdates', {'offset': max(u['update_id'] for u in updates) + 1, 'timeout': 0})
        if not count: raise RuntimeError('Inviare /id@nome_bot nel gruppo e ripetere connect entro 24 ore')
        print('ID inviato nel gruppo, nessun dato del gruppo stampato nel log.')
    elif args.mode == 'test':
        chat = os.environ.get('TELEGRAM_CHAT_ID')
        if not chat: raise RuntimeError('Manca TELEGRAM_CHAT_ID')
        telegram('sendMessage', {'chat_id': chat, 'text': '🚒 VVF – test di collegamento riuscito. Bot informativo non ufficiale; monitoraggio delle fonti pubbliche.'})
    else: run(args.mode == 'dry-run')

if __name__ == '__main__':
    try: main()
    except Exception as e:
        # Non stampare traceback di rete: potrebbero contenere il token Telegram.
        print('ERRORE:', str(e) if isinstance(e, RuntimeError) else type(e).__name__); sys.exit(1)
