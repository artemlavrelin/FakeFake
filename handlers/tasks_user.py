"""
User task flow: 🃏 ЗАДАНИЯ button, accept/reject, complete, AFK system, /report
"""
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS, MODER_GROUP_ID
from database import repository
from states.contest import ReportFSM, TaskUserFSM
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

REJECT_COOLDOWN_MINUTES = 30
RESET_COOLDOWN_MINUTES  = 300
CATEGORY_COOLDOWN_MINUTES = 90
TASK_DEADLINE_MINUTES   = 60
AFK_TIMEOUT_MINUTES     = 60
REPORT_COOLDOWN_HOURS   = 24


def _admin_only(uid: int) -> bool:
    return uid in ADMIN_IDS


# ─── AFK guard ────────────────────────────────────────────────────────────────

async def _check_afk(session: AsyncSession, telegram_id: int) -> bool:
    user = await repository.get_user(session, telegram_id)
    return user.is_afk if user else False


async def _afk_block(message: Message) -> None:
    await message.answer("👅 Вам доступна только команда /report")


# ─── 🃏 ЗАДАНИЯ entry ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "tasks")
async def cb_tasks(call: CallbackQuery, session: AsyncSession) -> None:
    if await _check_afk(session, call.from_user.id):
        await call.answer("👅 Вам доступна только команда /report", show_alert=True); return

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🟢 Принимать задания", callback_data="tasks:get"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="menu"))
    await call.message.edit_text("🃏 <b>ЗАДАНИЯ</b>\n\nНажмите кнопку чтобы получить задание:",
                                  parse_mode="HTML", reply_markup=b.as_markup())
    await call.answer()


@router.callback_query(F.data == "tasks:get")
async def cb_tasks_get(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if await _check_afk(session, call.from_user.id):
        await call.answer("👅 Вам доступна только команда /report", show_alert=True); return

    # Check if already has active task
    active = await repository.get_active_task_log(session, call.from_user.id)
    if active:
        await call.answer("⚠️ У вас уже есть активное задание!", show_alert=True); return

    task = await repository.get_random_available_task(session, call.from_user.id)
    if not task:
        await call.answer("😔 Нет доступных заданий. Попробуйте позже.", show_alert=True); return

    await state.update_data(task_id=task.id, show_time=datetime.utcnow().isoformat())
    await state.set_state(TaskUserFSM.viewing)

    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"task:accept:{task.id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"task:reject:{task.id}"),
    )

    await call.message.edit_text(
        f"🃏 <b>ЗАДАНИЕ #{task.id}</b>\n\n"
        f"Тип: <b>{task.platform.capitalize()}</b>\n"
        f"Действие: <b>{task.action_type}</b>\n"
        f"Лимит: {task.max_users} пользователей\n"
        f"Награда: <b>${task.reward:.2f}</b>\n\n"
        f"У вас есть {TASK_DEADLINE_MINUTES} минут на решение.",
        parse_mode="HTML",
        reply_markup=b.as_markup(),
    )
    await call.answer()


# ─── Accept task ──────────────────────────────────────────────────────────────

@router.callback_query(TaskUserFSM.viewing, F.data.startswith("task:accept:"))
async def cb_task_accept(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    task_id = int(call.data.split(":")[2])

    # Check again for double-take
    active = await repository.get_active_task_log(session, call.from_user.id)
    if active:
        await call.answer("У вас уже есть активное задание!", show_alert=True); return

    log = await repository.accept_task(session, task_id, call.from_user.id)
    if not log:
        await call.answer("Задание недоступно.", show_alert=True); return

    await state.update_data(log_id=log.id, task_id=task_id)
    await state.set_state(TaskUserFSM.doing)

    task    = await repository.get_task(session, task_id)
    comment = ""
    if log.comment_id:
        from sqlalchemy import select
        from database.models import TaskComment
        from database.engine import AsyncSessionLocal
        async with AsyncSessionLocal() as s2:
            r = await s2.execute(select(TaskComment).where(TaskComment.id == log.comment_id))
            c = r.scalar_one_or_none()
            if c:
                comment = f"\n\n💬 <b>Ваш уникальный комментарий:</b>\n<code>{c.text}</code>"

    expires = log.expires_at.strftime("%H:%M") if log.expires_at else "—"
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👍 Завершить", callback_data="task:finish"),
        InlineKeyboardButton(text="👎 Сбросить",  callback_data="task:reset"),
    )
    await call.message.edit_text(
        f"✅ <b>Задание принято!</b>\n\n"
        f"🔗 {task.link}\n"
        f"Действие: <b>{task.action_type}</b>\n"
        f"{task.description or ''}"
        f"{comment}\n\n"
        f"⏰ Дедлайн: {expires} UTC\n"
        f"Нажмите <b>👍 Завершить</b> после выполнения.",
        parse_mode="HTML",
        reply_markup=b.as_markup(),
    )
    await call.answer("✅ Принято!")
    logger.info("Task accepted | task_id=%s | user=%s", task_id, call.from_user.id)


# ─── Reject task ──────────────────────────────────────────────────────────────

@router.callback_query(TaskUserFSM.viewing, F.data.startswith("task:reject:"))
async def cb_task_reject(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    # 30-min cooldown (stored in FSM data for simplicity — no DB field needed for this)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    await call.message.edit_text(
        f"❌ Задание отклонено.\n⏰ Вы сможете взять новое задание через {REJECT_COOLDOWN_MINUTES} минут.",
        reply_markup=b.as_markup(),
    )
    await call.answer()


# ─── Finish task ──────────────────────────────────────────────────────────────

@router.callback_query(TaskUserFSM.doing, F.data == "task:finish")
async def cb_task_finish(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.set_state(TaskUserFSM.waiting_screenshot)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="task:reset"))
    await call.message.edit_text(
        "📸 Отправьте скриншот выполненного задания:",
        reply_markup=b.as_markup(),
    )
    await call.answer()


@router.message(TaskUserFSM.waiting_screenshot, F.photo | F.document)
async def fsm_task_screenshot(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    data   = await state.get_data()
    log_id = data.get("log_id")
    if not log_id:
        await state.clear(); return

    log  = await repository.get_task_log_by_id(session, log_id)
    if not log:
        await state.clear(); return

    await repository.update_task_log(session, log_id, "pending_review")
    await state.clear()

    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    uname = f"@{user.username}" if user.username else f"id{user.telegram_id}"
    num   = f"▫️{user.user_number}" if user.user_number else ""

    moder_text = (
        f"#finish\n"
        f"Task ID: <b>{log.task_id}</b>\n"
        f"User ID: <code>{message.from_user.id}</code> {uname} {num}"
    )
    moder_kb = InlineKeyboardBuilder()
    moder_kb.row(
        InlineKeyboardButton(text="⭐️ Выплатить", callback_data=f"tf:pay:{log_id}"),
        InlineKeyboardButton(text="🚫 Отказ",      callback_data=f"tf:no:{log_id}"),
    )

    if MODER_GROUP_ID:
        try:
            if message.photo:
                sent = await bot.send_photo(MODER_GROUP_ID, message.photo[-1].file_id,
                                             caption=moder_text, parse_mode="HTML",
                                             reply_markup=moder_kb.as_markup())
            else:
                sent = await bot.send_document(MODER_GROUP_ID, message.document.file_id,
                                                caption=moder_text, parse_mode="HTML",
                                                reply_markup=moder_kb.as_markup())
            await repository.update_task_log(session, log_id, "pending_review", sent.message_id)
        except Exception as e:
            logger.warning("Task finish notify failed | %s", e)

    await message.answer(
        "✅ Скриншот отправлен на проверку. Ожидайте начисления.",
    )


# ─── Moderator task approval ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("tf:pay:"))
async def cb_tf_pay(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not _admin_only(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    log_id = int(call.data.split(":")[2])
    log    = await repository.get_task_log_by_id(session, log_id)
    if not log or log.status != "pending_review":
        await call.answer("Уже обработано.", show_alert=True); return

    reward = log.task.reward if log.task else 0
    await repository.update_task_log(session, log_id, "completed")
    await repository.add_balance(session, log.telegram_id, reward)

    try:
        await call.message.edit_caption(
            call.message.caption + f"\n\n⭐️ Выплачено ${reward:.2f} | @{call.from_user.username}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        await bot.send_message(log.telegram_id,
            f"⭐️ Задание #{log.task_id} выполнено! Начислено <b>${reward:.2f}</b>.",
            parse_mode="HTML")
    except Exception as e:
        logger.warning("Task pay notify fail | %s", e)

    await call.answer("⭐️ Выплачено")
    logger.info("Task paid | log_id=%s | reward=%s | user=%s", log_id, reward, log.telegram_id)


@router.callback_query(F.data.startswith("tf:no:"))
async def cb_tf_no(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not _admin_only(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    log_id = int(call.data.split(":")[2])
    log    = await repository.get_task_log_by_id(session, log_id)
    if not log or log.status != "pending_review":
        await call.answer("Уже обработано.", show_alert=True); return

    await repository.update_task_log(session, log_id, "rejected")
    if log.comment_id:
        await repository.release_task_comment(session, log.comment_id)

    try:
        await call.message.edit_caption(
            call.message.caption + f"\n\n🚫 Отказано | @{call.from_user.username}", parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        await bot.send_message(log.telegram_id,
            f"🚫 Задание #{log.task_id} не принято. Обратитесь к администратору.")
    except Exception:
        pass

    await call.answer("🚫 Отказ")


# ─── Reset task ───────────────────────────────────────────────────────────────

@router.callback_query(TaskUserFSM.doing, F.data == "task:reset")
@router.callback_query(TaskUserFSM.waiting_screenshot, F.data == "task:reset")
async def cb_task_reset(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data   = await state.get_data()
    log_id = data.get("log_id")
    await state.clear()

    if log_id:
        log = await repository.get_task_log_by_id(session, log_id)
        if log:
            await repository.update_task_log(session, log_id, "reset")
            if log.comment_id:
                await repository.release_task_comment(session, log.comment_id)

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    await call.message.edit_text(
        f"👎 Задание сброшено.\n⏰ Кулдаун {RESET_COOLDOWN_MINUTES} минут.",
        reply_markup=b.as_markup(),
    )
    await call.answer()


# ─── AFK system ───────────────────────────────────────────────────────────────

@router.message(Command("afkoff"))
async def cmd_afkoff(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        await message.answer("⛔ Нет доступа"); return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("📖 /afkoff <id> или @username"); return
    target = args[1]
    if target.startswith("@"):
        user = await repository.get_user_by_username(session, target)
    elif target.lstrip("-").isdigit():
        user = await repository.get_user(session, int(target))
    else:
        await message.answer("⚠️ Неверный формат"); return
    if not user:
        await message.answer("❓ Не найден"); return
    await repository.set_afk(session, user.telegram_id, False)
    await message.answer(f"✅ AFK снят для <code>{user.telegram_id}</code>", parse_mode="HTML")


@router.message(Command("afklist"))
async def cmd_afklist(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        await message.answer("⛔ Нет доступа"); return
    users = await repository.get_afk_users(session)
    if not users:
        await message.answer("🚩 AFK пользователей нет."); return
    lines = ["🚩 <b>AFK список:</b>\n"]
    for u in users:
        name = f"@{u.username}" if u.username else f"▫️{u.user_number}"
        since = u.afk_since.strftime("%d.%m %H:%M") if u.afk_since else "—"
        lines.append(f"• <code>{u.telegram_id}</code> {name} с {since}")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ─── /report ──────────────────────────────────────────────────────────────────

@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext, session: AsyncSession) -> None:
    can, remaining = await repository.check_cooldown(
        session, message.from_user.id, "last_report_at", REPORT_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h    = secs // 3600
        await message.answer(f"⏳ Следующий репорт через {h}ч."); return

    await state.set_state(ReportFSM.waiting_content)
    await message.answer(
        "📣 Отправьте текст, фото или видео для репорта.\n"
        "Лимит: 1 репорт в 24 часа."
    )


@router.message(ReportFSM.waiting_content, F.text | F.photo | F.video)
async def fsm_report(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    await state.clear()
    await repository.set_timestamp(session, message.from_user.id, "last_report_at")

    # Remove AFK if user reports
    user = await repository.get_user(session, message.from_user.id)
    if user and user.is_afk:
        await repository.set_afk(session, message.from_user.id, False)

    if MODER_GROUP_ID:
        uname = f"@{message.from_user.username}" if message.from_user.username else f"id{message.from_user.id}"
        header = f"#репорт\n👤 {uname} | <code>{message.from_user.id}</code>"
        try:
            await bot.send_message(MODER_GROUP_ID, header, parse_mode="HTML")
            if message.photo:
                await bot.send_photo(MODER_GROUP_ID, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(MODER_GROUP_ID, message.video.file_id, caption=message.caption or "")
            elif message.text:
                await bot.send_message(MODER_GROUP_ID, message.text)
        except Exception as e:
            logger.warning("Report forward failed | moder=%s | %s", MODER_GROUP_ID, e)

    await message.answer("✅ Репорт отправлен.")
