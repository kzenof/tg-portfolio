# Telegram Mini App — Портфолио Антона

Telegram-бот + Mini App для приёма заявок на разработку: конфигуратор услуг, калькулятор стоимости, быстрый бриф, портфолио GitHub.

## Структура проекта

```
tg-portfolio/
├── main.py              # Telegram-бот (aiogram)
├── assets/
│   └── index.html       # Mini App (фронтенд)
├── requirements.txt
├── .env.example
└── .github/workflows/   # Автодеплой на GitHub Pages
```

## Шаг 1. Создайте бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather)
2. `/newbot` → задайте имя и username
3. Скопируйте **токен**
4. `/mybots` → ваш бот → **Bot Settings** → **Menu Button** → укажите URL Mini App (после деплоя)
5. `/mybots` → **Configure Mini App** → включите Mini App и укажите URL

## Шаг 2. Настройка окружения

```bash
cd tg-portfolio
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Отредактируйте `.env`:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от BotFather |
| `ADMIN_ID` | Ваш Telegram ID ([@userinfobot](https://t.me/userinfobot)) |
| `GITHUB_USERNAME` | Логин GitHub для вкладки «Портфолио» |
| `WEBAPP_URL` | URL Mini App после деплоя |

## Шаг 3. Настройка Mini App

Откройте `assets/index.html` и при необходимости измените:

```javascript
const GITHUB_USERNAME = 'ваш_github_логин';
```

## Шаг 4. Деплой Mini App на GitHub Pages

1. Создайте репозиторий на GitHub (например, `tg-portfolio`)
2. Загрузите код:

```bash
git init
git add .
git commit -m "Initial commit: Telegram Mini App"
git remote add origin https://github.com/ВАШ_ЛОГИН/tg-portfolio.git
git push -u origin main
```

3. **Settings → Pages → Build and deployment → Source: GitHub Actions**
4. После push workflow автоматически задеплоит Mini App
5. URL будет: `https://ВАШ_ЛОГИН.github.io/tg-portfolio/`

6. Обновите `.env`:
```
WEBAPP_URL=https://ВАШ_ЛОГИН.github.io/tg-portfolio/
```

7. В BotFather укажите этот же URL как Mini App URL

## Шаг 5. Запуск бота

Бот должен работать **24/7** на сервере (VPS, Railway, Render и т.д.):

```bash
python main.py
```

GitHub Pages хостит только фронтенд (HTML). Бот запускается отдельно.

### Бесплатный хостинг бота

**Railway / Render:**
1. Загрузите репозиторий
2. Start command: `python main.py`
3. Добавьте переменные окружения из `.env`

**Локально (для тестов):**
```bash
python main.py
```

## Функции Mini App

| Вкладка | Описание |
|---|---|
| **Обо мне** | Информация, режим работы |
| **Услуги** | Конфигуратор: Python, C++, Деплой, БД + опции |
| **Калькулятор** | Интерактивный прайс-лист с фото |
| **Бриф** | Пошаговая форма ТЗ (задача, ссылка, дедлайн, файл) |
| **Портфолио** | Публичные репозитории GitHub |
| **Контакты** | Telegram, VK, Gmail, Mail.ru, GitHub |

## Как работает отправка заявок

1. Пользователь открывает Mini App через бота (`/start`)
2. Заполняет форму и нажимает «Оформить заявку»
3. Данные отправляются боту через `Telegram.WebApp.sendData()`
4. Бот форматирует заявку и пересылает вам в ЛС
5. Пользователь получает подтверждение

Пример сообщения:
```
📩 Новая заявка
👤 От: @username (ID: 123456)
🔧 Услуга: Разработка на Python
➕ Опции: База данных (PostgreSQL/MySQL)
💰 Ориентир: от 5 500 ₽
```

## Локальное тестирование Mini App

```bash
# Простой HTTP-сервер
cd assets
python -m http.server 8080
```

Откройте `http://localhost:8080` — отправка заявок работает только внутри Telegram.

## Контакты

- Telegram: [@KZENOF](https://t.me/KZENOF)
- VK: [vk.ru/antonkalinskiy](https://vk.ru/antonkalinskiy)
- Gmail: antonkalinskij@gmail.com
