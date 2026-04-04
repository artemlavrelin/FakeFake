# 🏆 ContestBot — Telegram-бот для конкурсов

Telegram-бот для закрытого комьюнити с системой конкурсов и розыгрышей.

---

## ⚡ Быстрый старт (локально)

### 1. Клонируй и перейди в папку
```bash
cd contest_bot
```

### 2. Создай виртуальное окружение
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# или
.venv\Scripts\activate      # Windows
```

### 3. Установи зависимости
```bash
pip install -r requirements.txt
```

### 4. Создай `.env` из примера
```bash
cp .env.example .env
```

Отредактируй `.env`:
```env
BOT_TOKEN=your_token_here
ADMIN_IDS=123456789        # твой Telegram ID
DATABASE_URL=sqlite+aiosqlite:///./contest.db
```

> 💡 Узнать свой Telegram ID: напиши @userinfobot

### 5. Запусти бота
```bash
python bot.py
```

---

## 🚀 Деплой на Railway

### Шаг 1 — Создай проект на Railway
1. Зайди на [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo (или пустой проект + папка через CLI)

### Шаг 2 — Добавь PostgreSQL
1. В проекте: **+ New** → **Database** → **PostgreSQL**
2. Railway автоматически создаст переменную `DATABASE_URL`

### Шаг 3 — Настрой переменные окружения
В разделе **Variables** добавь:
```
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
```
`DATABASE_URL` Railway добавит сам из PostgreSQL-сервиса.

### Шаг 4 — Деплой
Запушь код в репозиторий — Railway подхватит `railway.toml` и запустит бота.

---

## 📁 Структура проекта

```
contest_bot/
├── bot.py                  # Точка входа, запуск Dispatcher
├── config.py               # Конфигурация из .env
├── requirements.txt
├── Procfile                # Для Railway
├── railway.toml            # Настройки деплоя
├── .env.example
│
├── database/
│   ├── __init__.py
│   ├── engine.py           # Создание AsyncEngine и сессий
│   ├── models.py           # SQLAlchemy ORM-модели
│   └── repository.py       # Вся логика работы с БД
│
├── handlers/
│   ├── __init__.py
│   ├── user.py             # Пользовательские команды (/start, кнопки)
│   └── admin.py            # Админ-команды (/create_contest, /draw, ...)
│
├── keyboards/
│   ├── __init__.py
│   └── reply.py            # ReplyKeyboard кнопки
│
├── middlewares/
│   └── db.py               # Middleware: инъекция DB-сессии в хендлеры
│
└── states/
    └── contest.py          # FSM-состояния для создания конкурса
```

---

## 🎮 Функционал

### Пользователь
| Действие | Описание |
|---|---|
| `/start` | Регистрация + главное меню |
| 🎯 Участвовать | Участие в активном конкурсе |
| 🏆 Текущий конкурс | Просмотр активного конкурса |
| 📋 Результаты | История завершённых конкурсов |

### Администратор
| Команда | Описание |
|---|---|
| `/create_contest` | Создать конкурс (3 шага: название → приз → кол-во победителей) |
| `/draw` | Провести розыгрыш и закрыть конкурс |
| `/ban <id>` | Заблокировать пользователя |
| `/unban <id>` | Разблокировать пользователя |
| `/list_users` | Список всех пользователей |

---

## 🗄️ База данных

| Таблица | Описание |
|---|---|
| `users` | Зарегистрированные пользователи |
| `contests` | Конкурсы (active / finished) |
| `contest_participants` | Участники конкурсов |
| `winners` | Победители |

---

## 🔐 Безопасность
- Администраторы определяются через `ADMIN_IDS` в `.env`
- Повторное участие в одном конкурсе игнорируется
- Заблокированные пользователи не могут участвовать
- Новый конкурс нельзя создать, пока предыдущий активен
