# 🏆 ContestBot v2 — Telegram-бот для конкурсов

Telegram-бот с системой конкурсов и розыгрышей для закрытого комьюнити.

## ✨ Что нового в v2
- **Inline-кнопки** — навигация без reply-клавиатуры, clean UI
- **Уведомления участников** после `/draw` — победители получают поздравление, остальные — результаты
- **Redis FSM** — состояния пережигают перезапуск бота (автофоллбэк на MemoryStorage)
- **Webhook-режим** — для Railway (Production); polling — для локальной разработки
  - Режим выбирается автоматически по наличию `WEBHOOK_HOST`

---

## ⚡ Быстрый старт (локально, polling)

```bash
cd contest_bot_v2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполни BOT_TOKEN и ADMIN_IDS
python bot.py
```

---

## 🚀 Деплой на Railway

### Шаг 1 — Создай проект и подключи репозиторий
Railway → New Project → GitHub repo

### Шаг 2 — Добавь сервисы
| Сервис | Зачем |
|---|---|
| **PostgreSQL** | База данных (Railway добавит `DATABASE_URL` сам) |
| **Redis** | FSM-хранилище (Railway добавит `REDIS_URL` сам) |

### Шаг 3 — Переменные окружения (Variables)
```
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
WEBHOOK_HOST=https://your-project.up.railway.app
```
> `DATABASE_URL`, `REDIS_URL`, `PORT` — Railway добавит автоматически

### Шаг 4 — Expose порт
В настройках сервиса: **Settings → Networking → Public Networking → Generate Domain**
Скопируй URL → вставь в `WEBHOOK_HOST`

### Шаг 5 — Деплой
Пуш в репозиторий → Railway запустит бота через `railway.toml`

---

## 📁 Структура

```
contest_bot_v2/
├── bot.py                  ← точка входа; polling или webhook — по WEBHOOK_HOST
├── config.py               ← все настройки из .env
├── requirements.txt
├── Procfile / railway.toml
├── database/
│   ├── models.py           ← ORM: Users, Contests, Participants, Winners
│   ├── engine.py           ← AsyncEngine + init_db()
│   └── repository.py       ← вся логика БД
├── handlers/
│   ├── user.py             ← /start + inline callbacks (participate, results...)
│   └── admin.py            ← /create_contest, /draw + уведомления, /ban, /unban
├── keyboards/
│   ├── inline.py           ← InlineKeyboard кнопки
│   └── reply.py            ← ReplyKeyboard (cancel при FSM)
├── middlewares/db.py       ← инъекция DB-сессии
└── states/contest.py       ← FSM-состояния
```

---

## 🎮 Функционал

### Пользователь (inline-кнопки)
| Кнопка | Описание |
|---|---|
| 🎯 Участвовать | Preview конкурса → подтверждение → регистрация |
| 🏆 Текущий конкурс | Название, приз, количество победителей и участников |
| 📋 Результаты | История завершённых конкурсов с победителями |

### Администратор (команды)
| Команда | Описание |
|---|---|
| `/create_contest` | FSM-диалог: название → приз → кол-во победителей |
| `/draw` | Розыгрыш + уведомление всех участников |
| `/ban <id>` | Заблокировать пользователя |
| `/unban <id>` | Разблокировать |
| `/list_users` | Список всех пользователей |

---

## 📬 Уведомления после `/draw`

**Победители** получают:
> 🎉 Поздравляем! Вы победили! + информация о призе

**Остальные участники** получают:
> 📋 Конкурс завершён + список победителей

Рассылка с задержкой 50ms между сообщениями (лимит Telegram: ~30 msg/sec).

---

## 🔐 Безопасность
- Администраторы определяются через `ADMIN_IDS` в `.env`
- Повторное участие в одном конкурсе игнорируется
- Забаненные пользователи не могут участвовать
- Нельзя создать новый конкурс, пока активен предыдущий
