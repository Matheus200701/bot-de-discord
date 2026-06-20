# Bot de Discord

Bot Discord em Python com `discord.py 2.x`, comandos slash/híbridos em português, SQLite, sistema de Cogs, moderação, utilidades e tickets.

## Recursos

- `/ping` — mostra a latência do bot.
- `/ajuda` — mostra a central de comandos.
- `/avatar` — mostra o avatar de um membro.
- `/userinfo` — mostra informações de um membro.
- `/serverinfo` — mostra informações do servidor.
- `/botinfo` — mostra informações técnicas do bot.
- `/banir` — bane um membro.
- `/expulsar` — expulsa um membro.
- `/limpar` — apaga mensagens do canal.
- `/timeout` — silencia temporariamente um membro.
- `/untimeout` — remove o timeout.
- `/avisar` — registra um aviso no banco SQLite.
- `/avisos` — lista os avisos de um membro.
- `/ticketpainel` — cria painel com botão para abrir tickets.

## Estrutura

```txt
bot-de-discord/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── cogs/
│   ├── __init__.py
│   ├── utilidade.py
│   ├── moderacao.py
│   └── tickets.py
├── database/
│   ├── __init__.py
│   └── database.py
├── utils/
│   ├── __init__.py
│   └── embeds.py
└── data/
    └── .gitkeep
```

## Como configurar

### 1. Instale o Python

Use Python 3.11 ou superior.

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure o token

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
copy .env.example .env
```

Depois edite o `.env` e coloque o token real do bot:

```env
DISCORD_TOKEN=SEU_TOKEN_AQUI
PREFIX=!
DATABASE_PATH=data/bot.db
OWNER_ID=0
MESSAGE_CONTENT_INTENT=false
```

Nunca envie o arquivo `.env` para o GitHub.

### 4. Ative permissões no Discord Developer Portal

No painel do bot, ative estas permissões/intents conforme o uso:

- Server Members Intent: recomendado para comandos com membros.
- Message Content Intent: só precisa ativar se quiser usar comandos por prefixo, como `!ping`. Para usar apenas slash commands, pode deixar `false` no `.env`.

### 5. Convide o bot

Permissões recomendadas:

- Send Messages
- Embed Links
- Read Message History
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members
- Manage Channels
- Use Slash Commands

### 6. Inicie o bot

```bash
python main.py
```

Ao iniciar, o bot sincroniza os comandos slash automaticamente.

## Observações

- O banco SQLite fica em `data/bot.db` e é criado automaticamente.
- O sistema de tickets cria a categoria `Tickets` automaticamente se ela não existir.
- O projeto foi feito para ser simples de expandir com novas Cogs.
