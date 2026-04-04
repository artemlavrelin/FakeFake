from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import REPORT_CHANNEL_TITLE, REPORT_CHANNEL_URL
from database import repository
from keyboards.inline import (
    atm_confirm_keyboard,
    atm_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
    contest_not_participating_keyboard,
    contest_participating_keyboard,
    main_menu_keyboard,
    participate_confirm_keyboard,
    public_stats_keyboard,
    report_keyboard,
    top_list_keyboard,
)
from states.contest import ATMInput
from utils.formatters import (
    calc_chance,
    format_personal_stats,
    format_public_stats,
    format_top_participants,
    format_top_winners,
    format_winner,
    stats_bar,
)
from utils.logger import get_logger
from utils.time_utils import time_ago

logger = get_logger(__name__)
router = Router()

_MENU_TEXT = "Выбери раздел:"


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    # Always clear any active FSM — /start is a universal reset
    await state.clear()

    await repository.get_or_create_user(
        session, message.from_user.id, message.from_user.username
    )
    args = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else ""

    if payload.startswith("contest_"):
        await _show_raffle_screen(message, session, edit=False)
        return

    await message.answer(_MENU_TEXT, reply_markup=main_menu_keyboard())


# ─── Menu ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(_MENU_TEXT, reply_markup=main_menu_keyboard())
    await call.answer()


# ─── 🤹🏻 Розыгрыш ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "raffle")
async def cb_raffle(call: CallbackQuery, session: AsyncSession) -> None:
    await _show_raffle_screen(call, session, edit=True)


async def _show_raffle_screen(
    event: Message | CallbackQuery,
    session: AsyncSession,
    edit: bool,
) -> None:
    is_call = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    msg = event.message if is_call else event

    user = await repository.get_or_create_user(session, user_id, event.from_user.username)
    contest = await repository.get_active_contest(session)

    if not contest:
        text = "🤹🏻 <b>РОЗЫГРЫШ</b>\n\nСейчас нет активного конкурса.\nСледите за обновлениями!"
        kb = back_to_menu_keyboard()
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        if is_call:
            await event.answer()
        return

    count = await repository.get_participant_count(session, contest.id)
    already = await repository.is_participant(session, contest.id, user_id)
    chance = calc_chance(contest.winners_count, count, already)
    bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)

    if already:
        status = "👉 Вы участвуете в конкурсе, удачи 🤞🏻"
        kb = contest_participating_keyboard()
    elif user.is_banned:
        status = "❌ Вы заблокированы"
        kb = back_to_menu_keyboard()
    else:
        status = "❌ Вы не участвуете"
        kb = contest_not_participating_keyboard()

    text = (
        f"🤹🏻 <b>#{contest.id} ТЕКУЩИЙ КОНКУРС</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        f"{status}"
    )

    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)
    if is_call:
        await event.answer()


# ─── 🔥 Участвовать (кнопка на экране конкурса) → экран подтверждения ─────────

@router.callback_query(F.data == "contest_participate")
async def cb_contest_participate(call: CallbackQuery, session: AsyncSession) -> None:
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.is_banned:
        await call.answer("🚫 Вы заблокированы.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Конкурс уже завершён.", show_alert=True)
        return

    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True)
        return

    count = await repository.get_participant_count(session, contest.id)
    # Hypothetical chance if user joins now
    chance = calc_chance(contest.winners_count, count + 1, True)
    bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)

    await call.message.edit_text(
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        "Принять участие?",
        parse_mode="HTML",
        reply_markup=participate_confirm_keyboard(contest.id),
    )
    await call.answer()


# ─── ✅ Подтвердить участие ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("confirm_participate:"))
async def cb_confirm_participate(call: CallbackQuery, session: AsyncSession) -> None:
    contest_id = int(call.data.split(":")[1])

    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.is_banned:
        await call.answer("🚫 Вы заблокированы.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.message.edit_text("Конкурс завершён.", reply_markup=back_to_menu_keyboard())
        await call.answer()
        return

    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True)
        return

    await repository.add_participant(session, contest.id, call.from_user.id)
    count = await repository.get_participant_count(session, contest.id)
    chance = calc_chance(contest.winners_count, count, True)
    bar = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)

    await call.message.edit_text(
        f"✅ <b>Вы зарегистрированы!</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        "👉 Ожидайте результатов. Удачи! 🤞🏻",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer("✅ Вы участвуете!")


# ─── 🧲 Участвовать из группы (inline callback в группе) ──────────────────────

@router.callback_query(F.data.startswith("group_join:"))
async def cb_group_join(call: CallbackQuery, session: AsyncSession) -> None:
    """
    Triggered by the 🧲 Участвовать button in the group announcement.
    The user must have already started the bot (to have a DB record).
    """
    contest_id = int(call.data.split(":")[1])

    # Auto-register user if not yet known
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)

    if user.is_banned:
        await call.answer("🚫 Вы заблокированы.", show_alert=True)
        return

    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.answer("❌ Конкурс уже завершён.", show_alert=True)
        return

    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True)
        return

    await repository.add_participant(session, contest.id, call.from_user.id)
    count = await repository.get_participant_count(session, contest.id)
    await call.answer(
        f"✅ Вы зарегистрированы!\n👥 Участников: {count}",
        show_alert=True,
    )


# ─── ⭐️ Отчет ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "report")
async def cb_report(call: CallbackQuery) -> None:
    text = (
        f"⭐️ <b>ОТЧЕТ</b>\n\n"
        f"<b>{REPORT_CHANNEL_TITLE}</b> — прозрачная отчётность системы:\n\n"
        "• ✅ Подтверждения выплат\n"
        "• 🏆 Результаты розыгрышей\n"
        "• 💬 Отзывы участников\n"
        "• 📊 Статистика победителей\n"
        "• 🔍 Данные, подтверждающие прозрачность работы\n\n"
        f"Перейди в канал, чтобы убедиться в честности системы:"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=report_keyboard(REPORT_CHANNEL_URL),
    )
    await call.answer()


# ─── 👀 Моя статистика ────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_stats")
async def cb_my_stats(call: CallbackQuery, session: AsyncSession) -> None:
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    stats = await repository.get_user_stats(session, call.from_user.id)
    await call.message.edit_text(
        format_personal_stats(stats, user.user_number),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer()


# ─── 👥 Общая статистика ──────────────────────────────────────────────────────

@router.callback_query(F.data == "public_stats")
async def cb_public_stats(call: CallbackQuery, session: AsyncSession) -> None:
    stats = await repository.get_public_stats(session)
    await call.message.edit_text(
        format_public_stats(stats),
        parse_mode="HTML",
        reply_markup=public_stats_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "top_winners")
async def cb_top_winners(call: CallbackQuery, session: AsyncSession) -> None:
    rows = await repository.get_top_winners(session)
    await call.message.edit_text(
        format_top_winners(rows), parse_mode="HTML", reply_markup=top_list_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "top_participants")
async def cb_top_participants(call: CallbackQuery, session: AsyncSession) -> None:
    rows = await repository.get_top_participants(session)
    await call.message.edit_text(
        format_top_participants(rows), parse_mode="HTML", reply_markup=top_list_keyboard()
    )
    await call.answer()


# ─── 🧲 АТМ — просмотр и ввод платёжных данных ───────────────────────────────

@router.callback_query(F.data == "atm")
async def cb_atm(call: CallbackQuery, session: AsyncSession) -> None:
    from config import ATM_INTRO
    pd = await repository.get_payment_data(session, call.from_user.id)
    has_data = pd is not None and (pd.binance_id or pd.stake_id)

    binance = f"`{pd.binance_id}`" if pd and pd.binance_id else "—"
    stake   = f"`{pd.stake_id}`"   if pd and pd.stake_id   else "—"

    text = (
        f"🧲 <b>АТМ «МАГНИТ»</b>\n\n"
        f"📌 {ATM_INTRO}\n\n"
        f"💛 <b>Binance ID:</b> {binance}\n"
        f"🎰 <b>Stake ID:</b> {stake}"
    )
    await call.message.edit_text(
        text, parse_mode="HTML", reply_markup=atm_keyboard(has_data)
    )
    await call.answer()


@router.callback_query(F.data == "atm_input")
async def cb_atm_input(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ATMInput.waiting_binance)
    await call.message.edit_text(
        "💛 <b>Введите ваш Binance ID:</b>\n\n"
        "Если не используете — отправьте <code>-</code>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


@router.message(ATMInput.waiting_binance)
async def atm_binance(message: Message, state: FSMContext) -> None:
    val = message.text.strip() if message.text else ""
    await state.update_data(binance=None if val == "-" else val)
    await state.set_state(ATMInput.waiting_stake)
    await message.answer(
        "🎰 <b>Введите ваш Stake ID:</b>\n\n"
        "Если не используете — отправьте <code>-</code>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ATMInput.waiting_stake)
async def atm_stake(message: Message, state: FSMContext) -> None:
    val = message.text.strip() if message.text else ""
    await state.update_data(stake=None if val == "-" else val)
    await state.set_state(ATMInput.confirm)

    data = await state.get_data()
    binance = data.get("binance") or "—"
    stake   = data.get("stake")   or "—"

    await message.answer(
        f"📋 <b>Проверьте данные перед сохранением:</b>\n\n"
        f"💛 Binance ID: <code>{binance}</code>\n"
        f"🎰 Stake ID: <code>{stake}</code>",
        parse_mode="HTML",
        reply_markup=atm_confirm_keyboard(),
    )


@router.callback_query(ATMInput.confirm, F.data == "atm_confirm")
async def atm_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await state.clear()

    await repository.upsert_payment_data(
        session,
        telegram_id=call.from_user.id,
        binance_id=data.get("binance"),
        stake_id=data.get("stake"),
    )

    await call.message.edit_text(
        "✅ <b>Данные сохранены!</b>\n\n"
        "Ваши платёжные данные привязаны к аккаунту и будут использованы при выплатах.",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )
    await call.answer("✅ Сохранено!")


@router.callback_query(F.data == "atm")
async def cb_atm_back(call: CallbackQuery, session: AsyncSession) -> None:
    # re-uses cb_atm above; defined separately to catch back from confirm
    pass
