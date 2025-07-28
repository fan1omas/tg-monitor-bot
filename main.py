from telethon import TelegramClient, events
from telethon.errors import (ChannelPrivateError, ChatIdInvalidError)
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv
from os import getenv
from collections import OrderedDict
import asyncio

load_dotenv()
phone = getenv("PHONE")
api_id = getenv("API_ID")
api_hash = getenv("API_HASH")
session_name = getenv("SESSION_NAME")
bot_api = getenv("BOT_API")

"""
нужен id чата!!!
"""

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
        if not event.out and event.chat_id in self.chats:
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
        if not event.out and event.chat_id in self.chats:
            async with self.chats_lock:
                sender = await event.get_sender()
                await self.bot.send_message(self.me, f"Изменили сообщение {event.id} в чате {event.chat_id} ({sender.first_name} {'' if sender.username is None else '@' + sender.username}): «{self.chats[event.chat_id][event.id]}» на «{event.text}»")
                self.chats[event.chat_id][event.id] = event.text

    async def handler_turn(self, event):
        if event.out:
            async with self.chats_lock:
                command = event.text.split()[1]
                if command.is_digit():
                    command = bool(int(command))
                    id_ = event.chat_id

                    if command:
                        if id_ in self.chats:
                            await self.bot.send_message(self.me, f'Id {id_} уже есть в списке чатов')
                        else:
                            self.chats[id_] = OrderedDict()
                            await self.bot.send_message(id_, 'Обработчик сообщений успешно активирован!')

                    else:
                        if id_ in self.chats:
                            self.chats.pop(id_)
                            await self.bot.send_message(id_, 'Обработчик сообщений успешно отключён!')
                        else:
                            await self.bot.send_message(self.me, f'Id {id_} нет в списке чатов')
                else:
                    await self.bot.send_message(self.me, f'Неверная введена команда в чате {event.chat_id}')


    async def setup_handlers(self):
        client.add_event_handler(self.new_msg, events.NewMessage())
        client.add_event_handler(self.edited_msg, events.MessageEdited())
        client.add_event_handler(self.handler_turn, events.NewMessage(pattern=r'^/handler'))

async def main():
    monitor = Monitor(bot)
    await monitor.async_init()
    await client.start(phone)
    await monitor.setup_handlers()

    await asyncio.gather(
        dp.start_polling(bot),
        client.run_until_disconnected()
    )

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🚫 Мониторинг остановлен.")
    finally:
        client.loop.close()