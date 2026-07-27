"""
Telegram-бот + HTTP API для Mini App.
Запуск: python main.py
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl

from aiohttp import web
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
NOTIFY_BOT_TOKEN = os.getenv("NOTIFY_BOT_TOKEN")
NOTIFY_CHAT_ID = int(os.getenv("NOTIFY_CHAT_ID", "0") or "0") or ADMIN_ID
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise ValueError("Укажите BOT_TOKEN в .env")

bot = Bot(token=BOT_TOKEN)
notify_bot = Bot(token=NOTIFY_BOT_TOKEN) if NOTIFY_BOT_TOKEN else bot
dp = Dispatcher()

ASSETS_DIR = Path(__file__).parent / "assets"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


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


def make_user(obj) -> SimpleNamespace:
    if isinstance(obj, SimpleNamespace):
        return obj
    return SimpleNamespace(
        id=obj.id,
        username=getattr(obj, "username", None),
        full_name=getattr(obj, "full_name", None) or "Пользователь",
    )


def validate_init_data(init_data: str) -> dict | None:
    """Проверяет подпись Telegram WebApp initData."""
    if not init_data:
        return None
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if calculated != received_hash:
        return None

    user_raw = parsed.get("user")
    if not user_raw:
        return None
    return json.loads(user_raw)


def user_from_init(user_data: dict) -> SimpleNamespace:
    name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
    return SimpleNamespace(
        id=user_data["id"],
        username=user_data.get("username"),
        full_name=name or "Пользователь",
    )


def format_request(data: dict, user) -> str:
    user = make_user(user)
    req_type = data.get("type", "unknown")
    username = f"@{user.username}" if user.username else user.full_name
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    lines = [
        "📩 <b>Новая заявка</b>",
        f"👤 От: {username} (ID: {user.id})",
        f"🕐 {now}",
        "",
    ]

    if req_type == "service":
        lines += [
            "📋 <b>Тип:</b> Конфигуратор услуг",
            f"🔧 <b>Услуга:</b> {data.get('service', '—')}",
        ]
        opts = data.get("options", [])
        if opts:
            lines.append(f"➕ <b>Опции:</b> {', '.join(opts)}")
        if data.get("estimated_price"):
            lines.append(f"💰 <b>Ориентир:</b> {data['estimated_price']}")

    elif req_type == "calculator":
        lines.append("📋 <b>Тип:</b> Расчёт стоимости")
        items = data.get("items", [])
        if items:
            lines.append("📦 <b>Выбрано:</b>")
            for item in items:
                lines.append(
                    f"  • {item.get('category', '')}: {item.get('name', '')} — {item.get('price', '')}"
                )
        else:
            lines += [
                f"📁 <b>Категория:</b> {data.get('category', '—')}",
                f"📦 <b>Позиция:</b> {data.get('item', '—')}",
            ]
        lines.append(f"💰 <b>Итого:</b> {data.get('price', '—')}")
        extras = data.get("extras", [])
        if extras:
            lines.append(f"➕ <b>Дополнительно:</b> {', '.join(extras)}")

    elif req_type == "brief":
        lines += [
            "📋 <b>Тип:</b> Быстрый бриф",
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

    else:
        lines.append(f"📦 <b>Данные:</b>\n<code>{json.dumps(data, ensure_ascii=False)}</code>")

    return "\n".join(lines)


async def notify_admin(text: str, user) -> bool:
    chat_id = NOTIFY_CHAT_ID or ADMIN_ID
    if not chat_id:
        return False
    try:
        await notify_bot.send_message(chat_id, text, parse_mode="HTML")
        logger.info("Заявка отправлена админу %s от user %s", chat_id, user.id)
        return True
    except Exception as e:
        logger.error("Ошибка отправки админу: %s", e)
        return False


async def process_order(data: dict, user, source: str = "api") -> bool:
    text = format_request(data, user)
    delivered = await notify_admin(text, user)
    logger.info("Заявка [%s] от %s: delivered=%s", source, user.id, delivered)

    try:
        await bot.send_message(
            user.id,
            "✅ <b>Заявка отправлена!</b>\n\nАнтон получил заявку и ответит "
            "(10:00 – 23:00).\n\nПриоритет: @KZENOF",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Не удалось подтвердить пользователю: %s", e)

    return delivered


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=webapp_keyboard(), parse_mode="HTML")


@dp.message(Command("test"))
async def cmd_test(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Команда только для администратора.")
        return
    await message.answer("✅ Бот работает!")
    ok = await notify_admin("🔔 <b>Тест</b> — уведомления работают.", message.from_user)
    await message.answer("✅ Уведомление отправлено." if ok else "❌ Не удалось отправить.")


@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    user = message.from_user
    raw = message.web_app_data.data
    logger.info("web_app_data от %s: %s", user.id, raw[:200])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw}
    await process_order(data, user, source="sendData")


async def api_options(_request):
    return web.Response(headers=CORS_HEADERS)


async def api_submit(request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400, headers=CORS_HEADERS)

    user_data = validate_init_data(body.get("initData", ""))
    if not user_data:
        return web.json_response({"ok": False, "error": "Invalid initData"}, status=403, headers=CORS_HEADERS)

    user = user_from_init(user_data)
    data = body.get("data", {})
    delivered = await process_order(data, user, source="api")
    return web.json_response({"ok": delivered}, headers=CORS_HEADERS)


async def start_web_server():
    app = web.Application()
    app.router.add_post("/api/submit", api_submit)
    app.router.add_route("OPTIONS", "/api/submit", api_options)
    if ASSETS_DIR.exists():
        app.router.add_static("/", ASSETS_DIR, show_index=True)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("HTTP API: http://0.0.0.0:%s/api/submit", PORT)


async def set_menu_button():
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Портфолио",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )
    except Exception as e:
        logger.warning("Menu button: %s", e)


async def main():
    await start_web_server()
    await set_menu_button()
    logger.info("Бот запущен. Mini App: %s", WEBAPP_URL)
    await dp.start_polling(bot, handle_signals=False)


if __name__ == "__main__":
    asyncio.run(main())
