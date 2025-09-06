import json, os

nb = {
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": """# Bot do Telegram com Memória de Curto Prazo (baseado em mikusec)

Este notebook monta um Bot do Telegram em Google Colab com long polling usando `python-telegram-bot` e implementa uma memória de curto prazo por chat para permitir perguntas dependentes de contexto.

- Tutorial oficial: https://core.telegram.org/bots/tutorial
- Samples: https://core.telegram.org/bots/samples
- Base de referência: https://github.com/vthayashi/mikusec (estrutura e execução em notebook)

Siga os passos: 1) Instalar dependências, 2) Inserir o token do BotFather, 3) Executar o bot.
'''
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {"id": "install-deps"},
      "outputs": [],
      "source": "# 1) Instalar dependências\n!pip -q install python-telegram-bot==20.7 nest_asyncio==1.6.0\n"
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {"id": "token-input"},
      "outputs": [],
      "source": "# 2) Inserir o token do BotFather com segurança\nfrom getpass import getpass\nTOKEN = getpass('Insira o token do seu bot (BotFather): ')\nassert TOKEN and TOKEN.strip(), 'Token vazio. Obtenha o token com o @BotFather.'\n"
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {"id": "bot-code"},
      "outputs": [],
      "source": r'''# 3) Código do bot com memória de curto prazo
import asyncio
import re
import time
import unicodedata
from collections import deque

import nest_asyncio
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
    """Memória simples por chat com TTL (segundos) e janela limitada.
    Armazena: histórico curto, último assunto (subject) e timestamp.
    """
    def __init__(self, ttl_seconds: int = 600, max_messages: int = 10):
        self.ttl = ttl_seconds
        self.max_messages = max_messages
        self.sessions = {}  # chat_id -> dict(subject: str|None, messages: deque, last_ts: float)

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
            # Expira a sessão
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

# Pequena base de conhecimento para demonstração
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
    # tentativa simples: reduzir espaços
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
    await update.message.reply_text(f'Assunto atual: {subj or "(nenhum)"}. Última pergunta: {last_user or "(nenhuma)"}.')

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text or ''
    memory.remember_message(chat_id, 'user', user_text)

    # 1) Extrair atributo e assunto da pergunta
    attr = detect_attribute(user_text)
    subj_raw = extract_subject(user_text)
    subj_key = resolve_subject(subj_raw) if subj_raw else None

    # 2) Verificar continuação baseada em memória
    used_memory = False
    if (not subj_key) and (attr or memory.is_followup(user_text)):
        last_subj = memory.get_subject(chat_id)
        if last_subj:
            subj_key = last_subj
            used_memory = True

    # 3) Persistir assunto detectado
    if subj_key:
        memory.set_subject(chat_id, subj_key)

    # 4) Montar resposta com contexto (se possível)
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

async def main_async():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('reset', cmd_reset))
    app.add_handler(CommandHandler('status', cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print('Iniciando polling... Pare a célula para encerrar.')
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

def run_bot():
    nest_asyncio.apply()
    try:
        asyncio.get_running_loop()
        return asyncio.create_task(main_async())
    except RuntimeError:
        asyncio.run(main_async())

print('Código carregado. Execute a célula abaixo para iniciar o bot.')
"""
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {"id": "run-bot"},
      "outputs": [],
      "source": "# 4) Executar o bot (long polling)\nrun_bot()\n"
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": """## Dicas
- Comandos úteis: `/start`, `/reset`, `/status`.
- Exemplos de interação:
  - Qual é a capital do Brasil?
  - E a moeda? (usa o assunto anterior automaticamente)
  - Qual o idioma de Portugal?
- Para parar o bot, interrompa a execução da célula.
"""
    }
  ],
  "metadata": {
    "colab": {"provenance": []},
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"}
  },
  "nbformat": 4,
  "nbformat_minor": 5
}

os.makedirs('colab', exist_ok=True)
with open('colab/telegram_bot_memory.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=2)
print('Wrote colab/telegram_bot_memory.ipynb')

