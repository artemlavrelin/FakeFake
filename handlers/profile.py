"""
Profile system with TikTok field, dynamic status, unique ID validation.
Social bonus: $0.10 per field (instagram, threads, facebook, twitter, tiktok) = max $0.50
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS
from database import repository
from database.models import STATUS_ICONS
from states.contest import AdminChangeFSM, ProfileFSM
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

STATUS_NAMES = {
    "new":      "…..",
    "pending":  "На рассмотрении",
    "verified": "Верифицирован",
    "fake":     "Фейк/мёртвый",
    "banned":   "Заблокирован",
    "girl":     "Девушка (верифицирована)",
    "guy":      "Парень (верифицирован)",
}

SOCIAL_BONUS_PER_FIELD = 0.10
SOCIAL_FIELDS = ["instagram", "threads", "facebook", "twitter", "tiktok"]


def _admin_only(uid: int) -> bool:
    return uid in ADMIN_IDS


def _fmt_profile(user, profile, pd) -> str:
    num    = f"▫️{user.user_number}" if user.user_number else "▫️—"
    status = STATUS_ICONS.get(profile.status if profile else "new", "…..")
    stake  = pd.stake_user if pd and pd.stake_user else "—"
    binance= pd.binance_id if pd and pd.binance_id else "—"
    insta  = f"@{profile.instagram}" if profile and profile.instagram else "—"
    threads= f"@{profile.threads}"   if profile and profile.threads   else "—"
    fb     = profile.facebook or "—" if profile else "—"
    tw     = f"@{profile.twitter}"   if profile and profile.twitter   else "—"
    tiktok = f"@{profile.tiktok}"    if profile and getattr(profile, "tiktok", None) else "—"
    return (
        f"🥼 <b>ПРОФИЛЬ</b> {status} {num}\n\n"
        f"♠️ Stake: {stake}\n"
        f"🟨 Binance: {binance}\n\n"
        f"🐦 X: {tw}\n"
        f"🔵 Facebook: {fb}\n"
        f"🔸 Instagram: {insta}\n"
        f"🧵 Threads: {threads}\n"
        f"🎶 TikTok: {tiktok}"
    )


def _verification_keyboard(telegram_id: int):
    b = InlineKeyboardBuilder()
    statuses = [
        ("🟩", "verified"), ("⬜️", "pending"), ("🟥", "fake"),
        ("⬛️", "banned"),   ("🟧", "girl"),    ("🟫", "guy"),  ("…..", "new"),
    ]
    for icon, status in statuses:
        b.button(text=icon, callback_data=f"ver:{telegram_id}:{status}")
    b.adjust(4)
    return b.as_markup()


# ─── Profile FSM — 5 steps (instagram, threads, facebook, twitter, tiktok) ───

@router.callback_query(F.data == "profile:fill")
async def cb_profile_fill(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileFSM.waiting_instagram)
    await call.message.edit_text(
        "🔸 <b>Шаг 1/5</b> — Instagram username (без @)\n\nЕсли нет — <code>-</code>",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ProfileFSM.waiting_instagram)
async def fsm_instagram(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(instagram="" if val == "-" else val.lstrip("@"))
    await state.set_state(ProfileFSM.waiting_threads)
    await message.answer(
        "🧵 <b>Шаг 2/5</b> — Threads username (без @)\n\nЕсли нет — <code>-</code>",
        parse_mode="HTML",
    )


@router.message(ProfileFSM.waiting_threads)
async def fsm_threads(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(threads="" if val == "-" else val.lstrip("@"))
    await state.set_state(ProfileFSM.waiting_facebook)
    await message.answer(
        "🔵 <b>Шаг 3/5</b> — Facebook ссылка\n\nЕсли нет — <code>-</code>",
        parse_mode="HTML",
    )


@router.message(ProfileFSM.waiting_facebook)
async def fsm_facebook(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(facebook="" if val == "-" else val)
    await state.set_state(ProfileFSM.waiting_twitter)
    await message.answer(
        "🐦 <b>Шаг 4/5</b> — Twitter/X username (без @)\n\nЕсли нет — <code>-</code>",
        parse_mode="HTML",
    )


@router.message(ProfileFSM.waiting_twitter)
async def fsm_twitter(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip()
    await state.update_data(twitter="" if val == "-" else val.lstrip("@"))
    await state.set_state(ProfileFSM.confirm)
    await message.answer(
        "🎶 <b>Шаг 5/5</b> — TikTok username (без @)\n\nЕсли нет — <code>-</code>",
        parse_mode="HTML",
    )


@router.message(ProfileFSM.confirm)
async def fsm_tiktok(message: Message, state: FSMContext, session: AsyncSession) -> None:
    val  = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()

    tiktok    = "" if val == "-" else val.lstrip("@")
    instagram = data.get("instagram", "")
    threads   = data.get("threads", "")
    facebook  = data.get("facebook", "")
    twitter   = data.get("twitter", "")

    profile = await repository.save_profile_v2(session, message.from_user.id,
                                                instagram, threads, facebook, twitter, tiktok)
    filled = sum(1 for v in [instagram, threads, facebook, twitter, tiktok] if v)
    bonus  = round(filled * SOCIAL_BONUS_PER_FIELD, 2)

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    await message.answer(
        f"✅ <b>Профиль сохранён!</b>\n\n"
        f"Статус: ⬜️ На рассмотрении\n"
        f"Заполнено: {filled}/5\n"
        f"⭐️ Начислено: <b>${bonus:.2f}</b>\n\n"
        f"⚠️ Редактирование только через администратора.",
        parse_mode="HTML",
        reply_markup=b.as_markup(),
    )


# ─── Admin commands ───────────────────────────────────────────────────────────

@router.message(Command("check"))
async def cmd_check(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("/check [id] или @username"); return

    target = args[1].strip()
    user   = (await repository.get_user_by_username(session, target)
               if target.startswith("@")
               else await repository.get_user(session, int(target))
               if target.lstrip("-").isdigit() else None)
    if not user:
        await message.answer("Пользователь не найден"); return

    profile = user.profile or await repository.get_or_create_profile(session, user.telegram_id)
    pd      = user.payment
    balance = user.balance or await repository.get_or_create_balance(session, user.telegram_id)
    text    = _fmt_profile(user, profile, pd)
    text   += (f"\n\n⭐️ Баланс: ${balance.balance:.2f}\n"
               f"💫 Выплачено: ${balance.paid_out:.2f}\n"
               f"🪫 Штрафы: ${balance.penalties:.2f}")
    await message.answer(text, parse_mode="HTML",
                         reply_markup=_verification_keyboard(user.telegram_id))


@router.message(Command("verification"))
async def cmd_verification(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("/verification [id] или @username"); return
    target = args[1].strip()
    user   = (await repository.get_user_by_username(session, target)
               if target.startswith("@")
               else await repository.get_user(session, int(target))
               if target.lstrip("-").isdigit() else None)
    if not user:
        await message.answer("Не найден"); return
    profile = user.profile or await repository.get_or_create_profile(session, user.telegram_id)
    current = STATUS_ICONS.get(profile.status, "…..")
    await message.answer(
        f"Смена статуса\nID: {user.telegram_id}\nТекущий: {current} {STATUS_NAMES.get(profile.status, '')}",
        reply_markup=_verification_keyboard(user.telegram_id),
    )


@router.callback_query(F.data.startswith("ver:"))
async def cb_verification(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True); return
    parts  = call.data.split(":")
    tid    = int(parts[1])
    status = parts[2]
    await repository.set_profile_status(session, tid, status)
    icon   = STATUS_ICONS.get(status, "…..")
    name   = STATUS_NAMES.get(status, status)
    await call.answer(f"Статус: {icon} {name}", show_alert=True)
    logger.info("Status | telegram_id=%s | status=%s | by=%s", tid, status, call.from_user.id)


@router.message(Command("change"))
async def cmd_change(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("/change [telegram_id]"); return
    target = args[1].strip()
    user   = (await repository.get_user_by_username(session, target)
               if target.startswith("@")
               else await repository.get_user(session, int(target))
               if target.lstrip("-").isdigit() else None)
    if not user:
        await message.answer("Не найден"); return
    await state.update_data(target_id=user.telegram_id)
    await state.set_state(AdminChangeFSM.waiting_field)
    b = InlineKeyboardBuilder()
    fields = [
        ("Instagram", "instagram"), ("Threads", "threads"),
        ("Facebook", "facebook"),   ("Twitter", "twitter"),
        ("TikTok", "tiktok"),       ("Binance ID", "binance_id"),
        ("Stake user", "stake_user"),
    ]
    for label, field in fields:
        b.button(text=label, callback_data=f"chfield:{field}")
    b.adjust(2)
    b.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_fsm"))
    await message.answer(
        f"Что изменить для {user.telegram_id}?",
        reply_markup=b.as_markup(),
    )


@router.callback_query(AdminChangeFSM.waiting_field, F.data.startswith("chfield:"))
async def cb_change_field(call: CallbackQuery, state: FSMContext) -> None:
    field = call.data.split(":")[1]
    await state.update_data(field=field)
    await state.set_state(AdminChangeFSM.waiting_value)
    await call.message.edit_text(f"Введите новое значение для {field}:")
    await call.answer()


@router.message(AdminChangeFSM.waiting_value)
async def fsm_change_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data  = await state.get_data()
    tid   = data["target_id"]
    field = data["field"]
    value = (message.text or "").strip()
    await state.clear()
    if field in ("instagram", "threads", "facebook", "twitter", "tiktok"):
        await repository.admin_update_profile(session, tid, **{field: value})
        await message.answer(f"OK: {field} = {value}")
    elif field in ("binance_id", "stake_user"):
        pd, err = await repository.upsert_payment_field(session, tid, field, value)
        await message.answer(err if err else f"OK: {field} = {value}")
    logger.info("Admin change | telegram_id=%s | field=%s | by=%s", tid, field, message.from_user.id)


@router.message(Command("allclear"))
async def cmd_allclear(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("/allclear [telegram_id]"); return
    ok = await repository.delete_user_completely(session, int(args[1]))
    await message.answer("Пользователь удалён" if ok else "Не найден")
