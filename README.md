# Telegram Message Monitor Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Telethon](https://img.shields.io/badge/Telethon-1.25+-green.svg)](https://docs.telethon.dev)
[![Aiogram](https://img.shields.io/badge/Aiogram-2.23+-yellowgreen.svg)](https://docs.aiogram.dev)

Бот для мониторинга удаленных и измененных сообщений в Telegram чатах с возможностью:
- Отслеживания удаленных сообщений
- Фиксации редактирования сообщений
- Ограничения хранимой истории сообщений
- Управления через Telegram-бота

## 📌 Пререквизиты

- Python 3.8+
- Telegram API ID и Hash (можно получить на [my.telegram.org](https://my.telegram.org))
- Токен Telegram бота ([@BotFather](https://t.me/BotFather))

## 🛠 Установка

1.Клонируйте репозиторий:
```bash
git clone https://github.com/fan1omas/telegram-monitor-bot.git
cd telegram-monitor-bot
```
2.Создайте и заполните файл .env:
```bash
touch .env
```

