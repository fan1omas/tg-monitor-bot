from telethon import TelegramClient, events
from telethon.errors import (ChannelPrivateError, ChatIdInvalidError)
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from os import getenv
from collections import OrderedDict
import asyncio
import json

phone = getenv("PHONE")
api_id = getenv("API_ID")
api_hash = getenv("API_HASH")
session_name = getenv("SESSION_NAME")
bot_api = getenv("BOT_API")

bot = Bot(token=bot_api)
dp = Dispatcher()

# Создаем клиент
client = TelegramClient(session_name, api_id, api_hash, system_version='4.16.30-vxCUSTOM')

class Monitor:
    def __init__(self, bot: Bot):
        self.active_tasks = {}
        self.bot = bot
        self.me = None
        self.chats = {}
        self.chats_lock = asyncio.Lock() # формат чатов: {chat_id: {message_id: 'text1', another_message_id: 'text2'}}
        self.MAX_MESSAGES = 100
        self.handlers = []

    async def async_init(self):
        self.me = (await client.get_me()).id
        await self.bot.send_message(self.me, f"🔎 Мониторинг сообщений запущен... (Ctrl+C для выхода). Твой ID: {self.me}")

    async def check_deleted_messages(self, chat_id):
        """Фоновая задача для проверки удалённых сообщений"""
        while chat_id in self.chats:
            try:
                messages = await client.get_messages(chat_id, limit=50)
                messages_ids = {msg.id for msg in messages}

                for msg_id in list(self.chats[chat_id].keys()):
                    if msg_id not in messages_ids:
                        deleted_text = self.chats[chat_id].pop(msg_id, None)
                        if deleted_text:
                            await self.bot.send_message(self.me, f"Удалено сообщение: {deleted_text}")

                await asyncio.sleep(60)


            except (ChannelPrivateError, ChatIdInvalidError) as e:
                print(f"Чат {chat_id} недоступен: {e}")
                break

            except Exception as e:
                print(f"Ошибка в check_deleted_messages: {e}")
                await asyncio.sleep(10)  # Пауза перед повтором

    async def new_msg(self, event):
        if event.chat_id in self.chats:
            async with self.chats_lock:
                self.chats[event.chat_id][event.id] = event.text

                if event.text is not None:
                    await self.bot.send_message(self.me, f"Новое сообщение: {event.text}")

                if len(self.chats[event.chat_id]) > self.MAX_MESSAGES:
                    oldest_msg_id, oldest_msg_text = self.chats[event.chat_id].popitem(last=False)
                    await self.bot.send_message(self.me, f"Удалено старое сообщение {oldest_msg_id} в чате {event.chat_id}: {oldest_msg_text}")

                if event.chat_id not in self.active_tasks: #добавляем один раз
                    self.active_tasks[event.chat_id] = asyncio.create_task(self.check_deleted_messages(event.chat_id))

    async def edited_msg(self, event):
        if event.chat_id in self.chats:
            async with self.chats_lock:
                sender = await event.get_chat()
                await self.bot.send_message(self.me, f"Изменили сообщение {event.id} в чате {event.chat_id} ({sender.first_name} {'' if sender.username is None else '@' + sender.username}): «{self.chats[event.chat_id][event.id]}» на «{event.text}»")
                self.chats[event.chat_id][event.id] = event.text

    async def handler_turn(self, event):
        async with self.chats_lock:
            command = event.text.split()

            if len(command) < 2:
                await client.send_message(self.me, f'Неверно введена команда в чате {event.chat_id}')
                return

            command = command[1]
            if command.isdigit():
                command = int(command)
                id_ = event.chat_id

                if command == 10:
                    print('start')
                    await self.prepare_json(id_, 10, event)
                    return

                if command == 1:
                    if id_ in self.chats:
                        await self.bot.send_message(self.me, f'Id {id_} уже есть в списке чатов')
                    else:
                        self.chats[id_] = OrderedDict()
                        await client.send_message(id_, 'Обработчик сообщений успешно активирован!')

                elif command == 0:
                    if id_ in self.chats:
                        self.chats.pop(id_)
                        await client.send_message(id_, 'Обработчик сообщений успешно отключён!')
                    else:
                        await self.bot.send_message(self.me, f'Id {id_} нет в списке чатов')
            else:
                 await self.bot.send_message(self.me, f'Неверная введена команда в чате {event.chat_id}')

    async def shutdown(self):
        """Завершение работы монитора"""
        print("\n🔴 Остановка монитора...")

        for task in self.active_tasks.values():
            task.cancel()

        for handler in self.handlers:
            client.remove_event_handler(handler)

        self.chats.clear()
        self.active_tasks.clear()

        print("✅ Монитор остановлен")

    @staticmethod
    async def prepare_json(chat_id, limit, event):
        chat = await client.get_entity(chat_id)
        messages = await client.get_messages(chat, limit=limit)
        data = []
        current_block = {}
        last_sender = None

        for message in messages:
            sender = message.sender
            if not hasattr(message, 'sender_id') or not hasattr(message, 'text'):
                continue  # пропускаем некорректные сообщения

            if sender.first_name != last_sender and len(current_block) == 2:
                data.append(current_block)
                current_block = {}

            if sender.first_name in current_block:
                current_block[sender.first_name] += '\n' + message.text
            else:
                current_block[sender.first_name] = message.text
            last_sender = sender.first_name

        if current_block:
            data.append(current_block)

        data = data[::-1]

        with open("train_ai/dataset.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        return data

    async def setup_handlers(self):
        self.handlers = [
            client.add_event_handler(self.new_msg, events.NewMessage(outgoing=True)),
            client.add_event_handler(self.edited_msg, events.MessageEdited(outgoing=True)),
            client.add_event_handler(self.handler_turn, events.NewMessage(pattern=r'^/handler', outgoing=True))
        ]

async def main():
    try:
        monitor = Monitor(bot)
        await client.start(phone)
        await monitor.async_init()
        await monitor.setup_handlers()

        await asyncio.gather(
            dp.start_polling(bot),
            client.run_until_disconnected()
        )
    except KeyboardInterrupt:
        await monitor.shutdown()

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🚫 Мониторинг остановлен.")
    finally:
        pass