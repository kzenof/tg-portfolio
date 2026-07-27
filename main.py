"""
Telegram-бот для Mini App портфолио Антона.
Обрабатывает /start и заявки из Web App.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MenuButtonWebApp,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://username.github.io/tg-portfolio/")

if not BOT_TOKEN:
    raise ValueError("Укажите BOT_TOKEN в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def webapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть портфолио",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )


WELCOME = (
    "👋 <b>Привет! Я бот Антона — разработчика Python & C++</b>\n\n"
    "Здесь вы можете:\n"
    "• Выбрать услугу и оформить заявку\n"
    "• Рассчитать ориентировочную стоимость\n"
    "• Оставить быстрый бриф с ТЗ\n"
    "• Посмотреть портфолио и кейсы\n\n"
    "⏰ Отвечаю на заявки: <b>10:00 – 23:00</b> ежедневно\n"
    "🔧 Работаю над задачами: <b>8:30 – 22:00</b>\n\n"
    "Нажмите кнопку ниже, чтобы открыть Mini App 👇"
)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=webapp_keyboard(), parse_mode="HTML")


@dp.message(Command("app"))
async def cmd_app(message: Message):
    await message.answer("Открыть приложение:", reply_markup=webapp_keyboard())


def format_request(data: dict, user) -> str:
    """Форматирует заявку из Mini App в читаемое сообщение."""
    req_type = data.get("type", "unknown")
    username = f"@{user.username}" if user.username else user.full_name
    user_id = user.id
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    lines = [
        f"📩 <b>Новая заявка</b>",
        f"👤 От: {username} (ID: {user_id})",
        f"🕐 {now}",
        "",
    ]

    if req_type == "service":
        lines += [
            f"📋 <b>Тип:</b> Конфигуратор услуг",
            f"🔧 <b>Услуга:</b> {data.get('service', '—')}",
        ]
        opts = data.get("options", [])
        if opts:
            lines.append(f"➕ <b>Опции:</b> {', '.join(opts)}")
        if data.get("estimated_price"):
            lines.append(f"💰 <b>Ориентир:</b> {data['estimated_price']}")

    elif req_type == "calculator":
        lines += [
            f"📋 <b>Тип:</b> Расчёт стоимости",
            f"📁 <b>Категория:</b> {data.get('category', '—')}",
            f"📦 <b>Позиция:</b> {data.get('item', '—')}",
            f"💰 <b>Сумма:</b> {data.get('price', '—')}",
        ]
        extras = data.get("extras", [])
        if extras:
            lines.append(f"➕ <b>Дополнительно:</b> {', '.join(extras)}")

    elif req_type == "brief":
        lines += [
            f"📋 <b>Тип:</b> Быстрый бриф",
            f"📝 <b>Задача:</b>\n{data.get('task', '—')}",
        ]
        if data.get("tz_link"):
            lines.append(f"🔗 <b>ТЗ:</b> {data['tz_link']}")
        if data.get("deadline"):
            lines.append(f"📅 <b>Дедлайн:</b> {data['deadline']}")
        if data.get("contact"):
            lines.append(f"📞 <b>Контакт:</b> {data['contact']}")
        if data.get("file_name"):
            lines.append(f"📎 <b>Файл:</b> {data['file_name']}")

    elif req_type == "contact":
        lines += [
            f"📋 <b>Тип:</b> Обратная связь",
            f"💬 <b>Сообщение:</b>\n{data.get('message', '—')}",
        ]

    else:
        lines.append(f"📦 <b>Данные:</b>\n<code>{json.dumps(data, ensure_ascii=False, indent=2)}</code>")

    return "\n".join(lines)


@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    user = message.from_user
    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        data = {"raw": message.web_app_data.data}

    text = format_request(data, user)

    # Подтверждение пользователю
    await message.answer(
        "✅ <b>Заявка отправлена!</b>\n\n"
        "Антон получил вашу заявку и ответит в ближайшее время "
        "(10:00 – 23:00).\n\n"
        "Приоритетный канал связи: @KZENOF",
        parse_mode="HTML",
    )

    # Уведомление админу
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
        except Exception as e:
            logger.error("Не удалось отправить админу: %s", e)
    else:
        logger.warning("ADMIN_ID не задан — заявка только подтверждена пользователю")


async def set_menu_button():
    """Устанавливает кнопку Mini App в меню бота."""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Портфолио",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )
    except Exception as e:
        logger.warning("Не удалось установить menu button: %s", e)


async def main():
    await set_menu_button()
    logger.info("Бот запущен. Mini App: %s", WEBAPP_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
