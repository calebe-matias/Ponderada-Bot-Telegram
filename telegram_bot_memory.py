#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram bot with short-term memory (per chat).
- Requires: python-telegram-bot>=20
- Run: set TELEGRAM_BOT_TOKEN=your_token && python telegram_bot_memory.py
"""
import asyncio
import os
import re
import sys
import time
import unicodedata
from collections import deque
from getpass import getpass

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)


def normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return s


class MemoryStore:
    """Simple per-chat memory with TTL and sliding window."""
    def __init__(self, ttl_seconds: int = 600, max_messages: int = 10):
        self.ttl = ttl_seconds
        self.max_messages = max_messages
        self.sessions = {}  # chat_id -> dict(subject, messages, last_ts)

    def _ensure(self, chat_id: int):
        if chat_id not in self.sessions:
            self.sessions[chat_id] = {
                'subject': None,
                'messages': deque(maxlen=self.max_messages),
                'last_ts': time.time(),
            }

    def _purge_if_expired(self, chat_id: int):
        sess = self.sessions.get(chat_id)
        if not sess:
            return
        if time.time() - sess['last_ts'] > self.ttl:
            self.sessions[chat_id] = {
                'subject': None,
                'messages': deque(maxlen=self.max_messages),
                'last_ts': time.time(),
            }

    def touch(self, chat_id: int):
        self._ensure(chat_id)
        self.sessions[chat_id]['last_ts'] = time.time()

    def remember_message(self, chat_id: int, role: str, text: str):
        self._ensure(chat_id)
        self._purge_if_expired(chat_id)
        self.sessions[chat_id]['messages'].append((time.time(), role, text))
        self.touch(chat_id)

    def set_subject(self, chat_id: int, subject: str | None):
        self._ensure(chat_id)
        self.sessions[chat_id]['subject'] = subject
        self.touch(chat_id)

    def get_subject(self, chat_id: int) -> str | None:
        self._ensure(chat_id)
        self._purge_if_expired(chat_id)
        return self.sessions[chat_id]['subject']

    def last_user_message(self, chat_id: int) -> str | None:
        self._ensure(chat_id)
        msgs = list(self.sessions[chat_id]['messages'])
        for _, role, text in reversed(msgs):
            if role == 'user':
                return text
        return None

    def clear(self, chat_id: int):
        self.sessions[chat_id] = {
            'subject': None,
            'messages': deque(maxlen=self.max_messages),
            'last_ts': time.time(),
        }

    def is_followup(self, text: str) -> bool:
        t = normalize_text(text)
        starters = (
            'e ', 'e a', 'e o', 'e os', 'e as',
            'e de', 'e do', 'e da', 'e dos', 'e das',
            'agora', 'sobre ', 'e quanto', 'e mais'
        )
        return any(t.startswith(s) for s in starters)


memory = MemoryStore(ttl_seconds=600, max_messages=10)

# Simple demo knowledge base
KNOWLEDGE = {
    'brasil': {
        'nome': 'Brasil',
        'capital': 'Brasília',
        'moeda': 'real (BRL)',
        'idioma': 'português',
    },
    'portugal': {
        'nome': 'Portugal',
        'capital': 'Lisboa',
        'moeda': 'euro (EUR)',
        'idioma': 'português',
    },
    'estados unidos': {
        'nome': 'Estados Unidos',
        'capital': 'Washington, D.C.',
        'moeda': 'dólar americano (USD)',
        'idioma': 'inglês',
    },
    'sao paulo': {
        'nome': 'São Paulo',
        'capital': 'São Paulo',
        'moeda': 'real (BRL)',
        'idioma': 'português',
    },
    'rio de janeiro': {
        'nome': 'Rio de Janeiro',
        'capital': 'Rio de Janeiro',
        'moeda': 'real (BRL)',
        'idioma': 'português',
    },
}

SUBJECT_ALIASES = {
    'eua': 'estados unidos',
    'estados unidos da america': 'estados unidos',
    'são paulo': 'sao paulo',
}

ATTR_SYNONYMS = {
    'capital': ['capital'],
    'moeda': ['moeda', 'currency', 'dinheiro'],
    'idioma': ['idioma', 'lingua', 'língua', 'language'],
}


def resolve_subject(raw: str | None) -> str | None:
    if not raw:
        return None
    n = normalize_text(raw)
    n = SUBJECT_ALIASES.get(n, n)
    if n in KNOWLEDGE:
        return n
    n2 = re.sub(r'\s+', ' ', n)
    return n2 if n2 in KNOWLEDGE else None


def detect_attribute(text: str) -> str | None:
    t = normalize_text(text)
    for key, words in ATTR_SYNONYMS.items():
        for w in words:
            if re.search(r'\b' + re.escape(w) + r'\b', t):
                return key
    if 'capital' in t:
        return 'capital'
    return None


def extract_subject(text: str) -> str | None:
    t = normalize_text(text)
    m = re.search(r'\b(dos|das|do|da|de)\s+([\w\s\.\-]+?)(\?|\!|\.|,|$)', t)
    if m:
        subj = m.group(2).strip()
        subj = re.sub(r'\s+', ' ', subj)
        return subj
    return None


def build_answer(subject_key: str, attr: str) -> str | None:
    data = KNOWLEDGE.get(subject_key)
    if not data:
        return None
    pretty = data.get('nome', subject_key.title())
    if attr in data:
        value = data[attr]
        if attr == 'capital':
            return f'A capital de {pretty} é {value}.'
        elif attr == 'moeda':
            return f'Falando de {pretty}, a moeda é {value}.'
        elif attr == 'idioma':
            return f'Em {pretty}, o idioma predominante é {value}.'
    return None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    memory.clear(chat_id)
    text = (
        'Olá! Sou um bot com memória de curto prazo.\n'
        'Exemplos: - Qual é a capital do Brasil? - E a moeda?\n'
        'Use /reset para limpar o contexto.'
    )
    await update.message.reply_text(text)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    memory.clear(chat_id)
    await update.message.reply_text('Contexto limpo! Podemos recomeçar.')


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subj = memory.get_subject(chat_id)
    last_user = memory.last_user_message(chat_id)
    await update.message.reply_text(
        f'Assunto atual: {subj or "(nenhum)"}. Última pergunta: {last_user or "(nenhuma)"}.'
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text or ''
    memory.remember_message(chat_id, 'user', user_text)

    # 1) Extract attribute and subject
    attr = detect_attribute(user_text)
    subj_raw = extract_subject(user_text)
    subj_key = resolve_subject(subj_raw) if subj_raw else None

    # 2) Use memory for follow-ups
    used_memory = False
    if (not subj_key) and (attr or memory.is_followup(user_text)):
        last_subj = memory.get_subject(chat_id)
        if last_subj:
            subj_key = last_subj
            used_memory = True

    # 3) Persist detected subject
    if subj_key:
        memory.set_subject(chat_id, subj_key)

    # 4) Build reply
    reply = None
    if subj_key and attr:
        reply = build_answer(subj_key, attr)
    elif subj_key and not attr:
        pretty = KNOWLEDGE[subj_key]['nome']
        reply = (
            f'Você está falando de {pretty}. Posso responder sobre capital, moeda ou idioma. '
            f'Por exemplo: "Qual a capital?" ou "E a moeda?"'
        )
    elif attr and not subj_key:
        reply = 'Qual o país/estado/cidade? Diga, por exemplo: "... do Brasil".'
    else:
        last_subj = memory.get_subject(chat_id)
        if last_subj:
            pretty = KNOWLEDGE[last_subj]['nome']
            reply = (
                f'Antes falávamos de {pretty}. Quer saber capital, moeda ou idioma? '
                f'Você também pode usar \'E a moeda?\''
            )
        else:
            reply = 'Em que posso ajudar? Exemplos: capital do Brasil; moeda de Portugal.'

    if used_memory and attr and subj_key:
        extra = build_answer(subj_key, attr) or ''
        if extra:
            reply = f'(Usando o contexto anterior) {extra}'

    memory.remember_message(chat_id, 'assistant', reply)
    await update.message.reply_text(reply)


def get_token() -> str:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        return token
    if sys.stdin.isatty():
        return getpass('Insira o token do seu bot (BotFather): ')
    raise RuntimeError('Defina a variável de ambiente TELEGRAM_BOT_TOKEN com seu token')


async def main_async():
    token = get_token()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('reset', cmd_reset))
    app.add_handler(CommandHandler('status', cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print('Iniciando polling... Ctrl+C para encerrar.')
    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(1)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print('\nEncerrado pelo usuário')


if __name__ == '__main__':
    main()
