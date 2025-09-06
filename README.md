# Ponderada-Bot-Telegram
Ponderada da Semana 05 - Bot de Telegram

## Como rodar no Google Colab

1) Crie um bot com o BotFather e copie o TOKEN.
2) Abra o Google Colab e envie o arquivo `colab/telegram_bot_memory.ipynb` (ou abra-o direto do GitHub se publicar).
3) Execute as células na ordem:
   - Instalar dependências
   - Inserir o token (colado com segurança no prompt)
   - Executar o bot (long polling)
4) No Telegram, envie mensagens para o seu bot. Exemplos:
   - "Qual é a capital do Brasil?"
   - "E a moeda?" (usa o contexto anterior automaticamente)

### Memória de curto prazo
- O bot mantém, por chat, um assunto recente (ex.: Brasil) e um histórico curto com TTL (padrão 10 minutos).
- Perguntas iniciadas por "E ..." ou que tragam apenas o atributo (ex.: "a moeda?") herdam o assunto.
- Comandos: `/start`, `/reset`, `/status`.

### Observações
- Este projeto segue o tutorial oficial de bots do Telegram e utiliza `python-telegram-bot` com long polling, adequado para Colab.
- A estrutura em notebook é inspirada no repositório base (mikusec), privilegiando simplicidade para execução e testes.

## Executar localmente (sem Notebook)

1) Instale as dependências:
   pip install python-telegram-bot==20.7
2) Defina o token do Bot:
   - Windows (PowerShell): `$env:TELEGRAM_BOT_TOKEN="SEU_TOKEN"`
   - Linux/macOS: `export TELEGRAM_BOT_TOKEN=SEU_TOKEN`
3) Rode o bot:
   python telegram_bot_memory.py

Comandos: /start, /reset, /status. A memória de curto prazo mantém o assunto por chat e permite perguntas de acompanhamento como "E a moeda?".
