"""
Telegram-бот + HTTP API для Mini App.
Запуск: python main.py
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MenuButtonWebApp,
    BufferedInputFile,
)
from aiogram.utils.web_app import safe_parse_webapp_init_data
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip().strip('"').strip("'")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL", "")
if WEBAPP_URL and not WEBAPP_URL.endswith("/"):
    WEBAPP_URL += "/"
if not WEBAPP_URL:
    WEBAPP_URL = "https://username.github.io/tg-portfolio/"
NOTIFY_BOT_TOKEN = os.getenv("NOTIFY_BOT_TOKEN")
NOTIFY_CHAT_ID = int(os.getenv("NOTIFY_CHAT_ID", "0") or "0") or ADMIN_ID
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise ValueError("Укажите BOT_TOKEN в .env")

bot = Bot(token=BOT_TOKEN)
notify_bot = Bot(token=NOTIFY_BOT_TOKEN) if NOTIFY_BOT_TOKEN else bot
dp = Dispatcher()

ASSETS_DIR = Path(__file__).parent / "assets"
MAX_FILE_SIZE = 1024 * 1024
ALLOWED_FILE_EXT = {".pdf", ".doc", ".docx", ".txt", ".zip", ".png", ".jpg", ".jpeg"}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
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


APP_HINT = (
    "\n\n💡 Mini App может прогружаться до 5 сек — это нормально. "
    "Если бот не работает или что-то пошло не так — напишите @KZENOF в тг."
)

WELCOME = (
    "👋 <b>Привет! Я бот Антона — разработчика Python & C++</b>\n\n"
    "Здесь вы можете:\n"
    "• Выбрать услугу и оформить заявку\n"
    "• Рассчитать ориентировочную стоимость\n"
    "• Отправить своё ТЗ с файлом\n"
    "• Посмотреть портфолио и кейсы\n\n"
    "⏰ Отвечаю на заявки: <b>10:00 – 23:00</b> ежедневно\n"
    "🔧 Работаю над задачами: <b>8:30 – 22:00</b>"
    f"{APP_HINT}\n\n"
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
    try:
        parsed = safe_parse_webapp_init_data(BOT_TOKEN, init_data)
    except ValueError:
        logger.warning("initData: invalid signature (len=%s)", len(init_data))
        return None
    if not parsed.user:
        return None
    return parsed.user.model_dump()


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
            lines.append(f"📎 <b>Файл:</b> {data['file_name']} (вложение ниже)")

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


async def notify_admin_file(file_bytes: bytes, file_name: str, caption: str) -> bool:
    chat_id = NOTIFY_CHAT_ID or ADMIN_ID
    if not chat_id:
        return False
    try:
        document = BufferedInputFile(file_bytes, filename=file_name)
        await notify_bot.send_document(chat_id, document=document, caption=caption)
        logger.info("Файл %s отправлен админу %s", file_name, chat_id)
        return True
    except Exception as e:
        logger.error("Ошибка отправки файла админу: %s", e)
        return False


async def process_order(
    data: dict,
    user,
    source: str = "api",
    file_bytes: bytes | None = None,
    file_name: str | None = None,
) -> bool:
    text = format_request(data, user)
    delivered = await notify_admin(text, user)

    if file_bytes and file_name:
        user_obj = make_user(user)
        username = f"@{user_obj.username}" if user_obj.username else user_obj.full_name
        file_ok = await notify_admin_file(
            file_bytes,
            file_name,
            f"📎 ТЗ от {username}",
        )
        delivered = delivered and file_ok

    logger.info("Заявка [%s] от %s: delivered=%s", source, user.id, delivered)

    try:
        await bot.send_message(
            user.id,
            "✅ <b>Заявка отправлена!</b>\n\nАнтон получил заявку и ответит "
            f"(10:00 – 23:00).\n\nСвязь в тг - @KZENOF{APP_HINT}",
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


def get_init_data(request, body: dict | None = None) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("tma "):
        return auth[4:].strip()
    if body:
        return body.get("initData", "")
    return ""


async def parse_submit_request(request):
    """JSON или multipart/form-data с полем data и опциональным file."""
    content_type = request.content_type or ""

    if content_type.startswith("multipart/form-data"):
        reader = await request.multipart()
        data: dict = {}
        file_bytes: bytes | None = None
        file_name: str | None = None

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "data":
                raw = await part.text()
                data = json.loads(raw) if raw else {}
            elif part.name == "file":
                file_bytes = await part.read(decode=False)
                file_name = part.filename or "file"

        return data, file_bytes, file_name

    body = await request.json()
    return body.get("data", {}), None, None


async def api_submit(request):
    content_type = request.content_type or ""
    init_data = ""

    try:
        if content_type.startswith("multipart/form-data"):
            init_data = get_init_data(request)
            data, file_bytes, file_name = await parse_submit_request(request)
        else:
            body = await request.json()
            init_data = get_init_data(request, body)
            data = body.get("data", {})
            file_bytes = None
            file_name = None
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("api_submit parse error: %s", e)
        return web.json_response({"ok": False, "error": "Invalid request"}, status=400, headers=CORS_HEADERS)

    user_data = validate_init_data(init_data)
    if not user_data:
        logger.warning("api_submit: invalid initData (len=%s)", len(init_data))
        return web.json_response({"ok": False, "error": "Invalid initData"}, status=403, headers=CORS_HEADERS)

    if file_bytes is not None:
        if len(file_bytes) > MAX_FILE_SIZE:
            return web.json_response({"ok": False, "error": "File too large"}, status=400, headers=CORS_HEADERS)
        ext = Path(file_name or "").suffix.lower()
        if ext not in ALLOWED_FILE_EXT:
            return web.json_response({"ok": False, "error": "File type not allowed"}, status=400, headers=CORS_HEADERS)
        data["file_name"] = file_name

    user = user_from_init(user_data)
    logger.info("api_submit от user %s, type=%s, file=%s", user.id, data.get("type"), bool(file_bytes))
    delivered = await process_order(data, user, source="api", file_bytes=file_bytes, file_name=file_name)
    return web.json_response({"ok": delivered}, headers=CORS_HEADERS)


async def serve_index(_request):
    index = ASSETS_DIR / "index.html"
    if not index.exists():
        return web.Response(text="index.html not found", status=404)
    return web.FileResponse(index)


async def health(_request):
    return web.json_response({"ok": True})


async def start_web_server():
    app = web.Application(client_max_size=MAX_FILE_SIZE + 512 * 1024)
    app.router.add_get("/", serve_index)
    app.router.add_get("/index.html", serve_index)
    app.router.add_get("/health", health)
    app.router.add_post("/api/submit", api_submit)
    app.router.add_route("OPTIONS", "/api/submit", api_options)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("HTTP: 0.0.0.0:%s  Mini App: %s", PORT, WEBAPP_URL)


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
    me = await bot.get_me()
    logger.info("Bot: @%s (id=%s)", me.username, me.id)
    await set_menu_button()
    logger.info("Бот запущен. Mini App: %s", WEBAPP_URL)
    await dp.start_polling(bot, handle_signals=False)


if __name__ == "__main__":
    asyncio.run(main())
