"""
Admin task management: /createtask, /deletetask, /taskinfo
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS
from database import repository
from states.contest import CreateTaskFSM
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

PLATFORMS   = ["Twitter", "Facebook", "Instagram", "Threads", "Join", "Share"]
ACTION_TYPES = ["лайк", "лайк + комментарий", "лайк + комментарий + репост",
                "лайк + комментарий + репост + подписка"]
NEEDS_COMMENTS = {"лайк + комментарий", "лайк + комментарий + репост",
                  "лайк + комментарий + репост + подписка"}


def _admin_only(uid: int) -> bool:
    return uid in ADMIN_IDS


def _platform_keyboard():
    b = InlineKeyboardBuilder()
    for p in PLATFORMS:
        b.button(text=p, callback_data=f"tp:{p.lower()}")
    b.adjust(3)
    b.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_fsm"))
    return b.as_markup()


def _action_keyboard():
    b = InlineKeyboardBuilder()
    for i, a in enumerate(ACTION_TYPES):
        b.button(text=f"{i+1}. {a}", callback_data=f"ta:{i}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_fsm"))
    return b.as_markup()


# ─── /createtask ──────────────────────────────────────────────────────────────

@router.message(Command("createtask"))
async def cmd_createtask(message: Message, state: FSMContext) -> None:
    if not _admin_only(message.from_user.id):
        await message.answer("⛔ Нет доступа"); return
    await state.set_state(CreateTaskFSM.waiting_platform)
    await message.answer(
        "🃏 <b>Создание задания — шаг 1</b>\n\nВыберите платформу:",
        parse_mode="HTML", reply_markup=_platform_keyboard(),
    )


@router.callback_query(CreateTaskFSM.waiting_platform, F.data.startswith("tp:"))
async def fsm_platform(call: CallbackQuery, state: FSMContext) -> None:
    platform = call.data.split(":")[1]
    await state.update_data(platform=platform)
    await state.set_state(CreateTaskFSM.waiting_link)
    await call.message.edit_text(
        f"Платформа: <b>{platform.capitalize()}</b>\n\n"
        "Шаг 2 — Введите <b>ссылку</b> на пост/канал:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(CreateTaskFSM.waiting_link)
async def fsm_link(message: Message, state: FSMContext) -> None:
    link = (message.text or "").strip()
    if not link.startswith("http"):
        await message.answer("⚠️ Введите корректную ссылку (начинается с http):"); return
    await state.update_data(link=link)
    await state.set_state(CreateTaskFSM.waiting_max_users)
    await message.answer("Шаг 3 — Введите <b>количество пользователей</b> (например: 15):",
                         parse_mode="HTML")


@router.message(CreateTaskFSM.waiting_max_users)
async def fsm_max_users(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        await message.answer("⚠️ Введите целое число ≥ 1:"); return
    await state.update_data(max_users=int(raw))
    await state.set_state(CreateTaskFSM.waiting_action_type)
    await message.answer("Шаг 4 — Выберите <b>тип действий</b>:",
                         parse_mode="HTML", reply_markup=_action_keyboard())


@router.callback_query(CreateTaskFSM.waiting_action_type, F.data.startswith("ta:"))
async def fsm_action_type(call: CallbackQuery, state: FSMContext) -> None:
    idx    = int(call.data.split(":")[1])
    action = ACTION_TYPES[idx]
    await state.update_data(action_type=action)
    await state.set_state(CreateTaskFSM.waiting_description)
    await call.message.edit_text(
        f"Действие: <b>{action}</b>\n\nШаг 5 — Введите <b>описание задания</b>:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(CreateTaskFSM.waiting_description)
async def fsm_description(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    await state.update_data(description=desc)
    await state.set_state(CreateTaskFSM.waiting_reward)
    await message.answer("Шаг 6 — Введите <b>награду</b> в $ (например: 0.20):",
                         parse_mode="HTML")


@router.message(CreateTaskFSM.waiting_reward)
async def fsm_reward(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        reward = float(raw)
        if reward <= 0: raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите положительное число (например: 0.20):"); return

    data = await state.get_data()
    await state.update_data(reward=reward)
    action = data.get("action_type", "")

    if action in NEEDS_COMMENTS:
        max_u = data.get("max_users", 15)
        await state.set_state(CreateTaskFSM.waiting_comments)
        await message.answer(
            f"Шаг 7 — Введите <b>{max_u} уникальных комментариев</b>, "
            f"по одному в строке (всего {max_u} строк):",
            parse_mode="HTML",
        )
    else:
        await state.set_state(CreateTaskFSM.confirm)
        await _show_task_preview(message, state)


@router.message(CreateTaskFSM.waiting_comments)
async def fsm_comments(message: Message, state: FSMContext) -> None:
    comments = [c.strip() for c in (message.text or "").split("\n") if c.strip()]
    data     = await state.get_data()
    max_u    = data.get("max_users", 15)

    if len(comments) < max_u:
        await message.answer(
            f"⚠️ Нужно минимум <b>{max_u}</b> комментариев, вы ввели {len(comments)}. "
            f"Введите ещё раз:",
            parse_mode="HTML",
        ); return

    await state.update_data(comments=comments[:max_u])
    await state.set_state(CreateTaskFSM.confirm)
    await _show_task_preview(message, state)


async def _show_task_preview(message: Message, state: FSMContext) -> None:
    data     = await state.get_data()
    comments = data.get("comments", [])
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Создать",  callback_data="task:create_confirm"),
        InlineKeyboardButton(text="❌ Отмена",   callback_data="cancel_fsm"),
    )
    await message.answer(
        f"📋 <b>Предпросмотр задания</b>\n\n"
        f"Платформа: <b>{data.get('platform','').capitalize()}</b>\n"
        f"Ссылка: {data.get('link','')}\n"
        f"Пользователей: <b>{data.get('max_users',0)}</b>\n"
        f"Действие: <b>{data.get('action_type','')}</b>\n"
        f"Описание: {data.get('description','')}\n"
        f"Награда: <b>${data.get('reward',0):.2f}</b>\n"
        f"Комментариев: <b>{len(comments)}</b>",
        parse_mode="HTML",
        reply_markup=b.as_markup(),
    )


@router.callback_query(CreateTaskFSM.confirm, F.data == "task:create_confirm")
async def cb_task_create_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await state.clear()

    task = await repository.create_task(
        session,
        platform    = data.get("platform", ""),
        link        = data.get("link", ""),
        max_users   = data.get("max_users", 15),
        action_type = data.get("action_type", ""),
        description = data.get("description", ""),
        reward      = data.get("reward", 0.20),
        admin_id    = call.from_user.id,
    )

    comments = data.get("comments", [])
    if comments:
        await repository.add_task_comments(session, task.id, comments)

    await call.message.edit_text(
        f"✅ <b>Задание #{task.id} создано!</b>\n"
        f"Платформа: {task.platform} | Пользователей: {task.max_users} | "
        f"Награда: ${task.reward:.2f}",
        parse_mode="HTML",
    )
    await call.answer("✅ Создано!")
    logger.info("Task created | id=%s | admin=%s", task.id, call.from_user.id)


# ─── /deletetask ──────────────────────────────────────────────────────────────

@router.message(Command("deletetask"))
async def cmd_deletetask(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        await message.answer("⛔ Нет доступа"); return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("📖 /deletetask <task_id>"); return
    ok = await repository.delete_task(session, int(args[1]))
    await message.answer("✅ Задание деактивировано." if ok else "❓ Не найдено.")


# ─── /taskinfo ────────────────────────────────────────────────────────────────

@router.message(Command("taskinfo"))
async def cmd_taskinfo(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        await message.answer("⛔ Нет доступа"); return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("📖 /taskinfo <task_id>"); return

    info = await repository.get_task_info(session, int(args[1]))
    if not info:
        await message.answer("❓ Задание не найдено"); return

    task      = info["task"]
    completed = info["completed"]
    logs      = info["logs"]

    lines = [
        f"📋 <b>Task #{task.id}</b>",
        f"Платформа: {task.platform} | Действие: {task.action_type}",
        f"Выполнено: <b>{completed}/{task.max_users}</b>\n",
        "Список:"
    ]
    for log in logs[-20:]:  # last 20
        icon = "✅" if log.status == "completed" else \
               "☑️" if log.status in ("accepted", "pending_review") else "❌"
        lines.append(f"ID <code>{log.telegram_id}</code> {icon} ({log.status})")

    await message.answer("\n".join(lines), parse_mode="HTML")
