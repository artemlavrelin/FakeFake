from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    BINANCE_URL, BOT_GREETING, MODER_GROUP_ID,
    PAYMENT_CHANGE_COOLDOWN_DAYS,
    REPORT_CHANNEL_TITLE, REPORT_CHANNEL_URL,
    REVIEW_COOLDOWN_HOURS, STAKE_URL,
)
from database import repository
from strings import t
from keyboards.inline import (
    back_to_menu_keyboard, binance_delete_confirm_keyboard, binance_keyboard,
    cancel_keyboard, contest_not_participating_keyboard, contest_participating_keyboard,
    lang_keyboard, main_menu_keyboard, participate_confirm_keyboard,
    public_stats_keyboard, report_keyboard, stake_delete_confirm_keyboard,
    stake_keyboard, top_list_keyboard,
)
from states.contest import BinanceInput, ReviewInput, StakeInput
from utils.formatters import (
    calc_chance, format_personal_stats, format_public_stats,
    format_top_participants, format_top_winners, stats_bar,
)
from utils.logger import get_logger
from utils.time_utils import time_ago

logger = get_logger(__name__)
router = Router()


async def _lang(session: AsyncSession, telegram_id: int) -> str:
    user = await repository.get_user(session, telegram_id)
    return (user.lang or "ru") if user else "ru"


async def _notify_payment_change(
    bot: Bot,
    lang: str,
    user,
    field_label: str,
    new_value: str,
) -> None:
    """Send payment change notification to moderator group."""
    if not MODER_GROUP_ID:
        return
    uname = user.username or "(нет username)"
    num   = user.user_number or "—"
    try:
        await bot.send_message(
            MODER_GROUP_ID,
            t(lang, "payment_changed_moder",
              username=uname, uid=user.telegram_id,
              num=num, field=field_label, value=new_value),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Payment change notify failed | moder_group=%s | %s", MODER_GROUP_ID, e)


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await repository.get_or_create_user(
        session, message.from_user.id, message.from_user.username
    )
    if not user.lang:
        await message.answer(
            f"{BOT_GREETING}\n\n{t('ru', 'choose_language')}",
            reply_markup=lang_keyboard(),
        )
        return

    args    = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else ""
    if payload.startswith("contest_"):
        await _show_raffle(message, session, user.lang, edit=False)
        return

    await message.answer(
        f"{BOT_GREETING}\n\n{t(user.lang, 'menu_text')}",
        reply_markup=main_menu_keyboard(user.lang),
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(call: CallbackQuery, session: AsyncSession) -> None:
    lang = call.data.split(":")[1]
    await repository.set_lang(session, call.from_user.id, lang)
    await call.message.edit_text(
        f"{BOT_GREETING}\n\n{t(lang, 'menu_text')}",
        reply_markup=main_menu_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "switch_lang")
async def cb_switch_lang(call: CallbackQuery, session: AsyncSession) -> None:
    current  = await _lang(session, call.from_user.id)
    new_lang = "en" if current == "ru" else "ru"
    await repository.set_lang(session, call.from_user.id, new_lang)
    await call.message.edit_text(
        f"{BOT_GREETING}\n\n{t(new_lang, 'menu_text')}",
        reply_markup=main_menu_keyboard(new_lang),
    )
    await call.answer()


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        f"{BOT_GREETING}\n\n{t(lang, 'menu_text')}",
        reply_markup=main_menu_keyboard(lang),
    )
    await call.answer()


# ─── 🤹🏻 Raffle ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "raffle")
async def cb_raffle(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await _show_raffle(call, session, lang, edit=True)


async def _show_raffle(event, session: AsyncSession, lang: str, edit: bool) -> None:
    is_call = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    msg     = event.message if is_call else event

    user    = await repository.get_or_create_user(session, user_id, event.from_user.username)
    contest = await repository.get_active_contest(session)

    if not contest:
        text = t(lang, "raffle_no_contest")
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_keyboard(lang))
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=back_to_menu_keyboard(lang))
        if is_call:
            await event.answer()
        return

    count   = await repository.get_participant_count(session, contest.id)
    already = await repository.is_participant(session, contest.id, user_id)
    chance  = calc_chance(contest.winners_count, count, already)
    bar     = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)

    if already:
        status = t(lang, "raffle_participating")
        kb     = contest_participating_keyboard(lang)
    elif user.is_banned:
        status = t(lang, "raffle_banned")
        kb     = back_to_menu_keyboard(lang)
    else:
        status = t(lang, "raffle_not_participating")
        kb     = contest_not_participating_keyboard(lang)

    text = t(lang, "raffle_header", id=contest.id, title=contest.title, bar=bar, status=status)
    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)
    if is_call:
        await event.answer()


@router.callback_query(F.data == "contest_participate")
async def cb_participate(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.is_banned:
        await call.answer(t(lang, "raffle_banned_alert"), show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer(t(lang, "raffle_finished"), show_alert=True)
        return
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer(t(lang, "raffle_already"), show_alert=True)
        return
    count  = await repository.get_participant_count(session, contest.id)
    chance = calc_chance(contest.winners_count, count + 1, True)
    bar    = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)
    await call.message.edit_text(
        t(lang, "raffle_confirm_text", title=contest.title, bar=bar),
        parse_mode="HTML",
        reply_markup=participate_confirm_keyboard(lang, contest.id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm_participate:"))
async def cb_confirm(call: CallbackQuery, session: AsyncSession) -> None:
    contest_id = int(call.data.split(":")[1])
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    if user.is_banned:
        await call.answer(t(lang, "raffle_banned_alert"), show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.message.edit_text(t(lang, "raffle_finished"), reply_markup=back_to_menu_keyboard(lang))
        await call.answer()
        return
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer(t(lang, "raffle_already"), show_alert=True)
        return
    await repository.add_participant(session, contest.id, call.from_user.id)
    count  = await repository.get_participant_count(session, contest.id)
    chance = calc_chance(contest.winners_count, count, True)
    bar    = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)
    await call.message.edit_text(
        t(lang, "raffle_joined", title=contest.title, bar=bar),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(lang),
    )
    await call.answer(t(lang, "btn_confirm"))


@router.callback_query(F.data.startswith("group_join:"))
async def cb_group_join(call: CallbackQuery, session: AsyncSession) -> None:
    contest_id = int(call.data.split(":")[1])
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    lang = user.lang or "ru"
    if user.is_banned:
        await call.answer(t(lang, "raffle_banned_alert"), show_alert=True)
        return
    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.answer(t(lang, "group_finished"), show_alert=True)
        return
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer(t(lang, "raffle_already"), show_alert=True)
        return
    await repository.add_participant(session, contest.id, call.from_user.id)
    count = await repository.get_participant_count(session, contest.id)
    await call.answer(t(lang, "group_joined", n=count), show_alert=True)


# ─── ⭐️ Report + Reviews ──────────────────────────────────────────────────────

@router.callback_query(F.data == "report")
async def cb_report(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "report_text", title=REPORT_CHANNEL_TITLE),
        parse_mode="HTML",
        reply_markup=report_keyboard(lang, REPORT_CHANNEL_URL),
    )
    await call.answer()


@router.callback_query(F.data == "review:start")
async def cb_review_start(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    can, remaining = await repository.check_cooldown(
        session, call.from_user.id, "last_review_at", REVIEW_COOLDOWN_HOURS
    )
    if not can:
        secs = int(remaining.total_seconds())
        h, m = secs // 3600, (secs % 3600) // 60
        await call.answer(t(lang, "review_cooldown", h=h, m=m), show_alert=True)
        return
    await state.set_state(ReviewInput.waiting_content)
    await call.message.edit_text(
        t(lang, "review_prompt"), parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="report"),
    )
    await call.answer()


@router.message(ReviewInput.waiting_content, F.text | F.photo | F.video)
async def fsm_review(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, message.from_user.id)
    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    can, _ = await repository.check_cooldown(session, message.from_user.id, "last_review_at", REVIEW_COOLDOWN_HOURS)
    if not can:
        await state.clear()
        await message.answer(t(lang, "review_sent"), parse_mode="HTML", reply_markup=back_to_menu_keyboard(lang))
        return
    await state.clear()
    await repository.set_timestamp(session, message.from_user.id, "last_review_at")
    if MODER_GROUP_ID:
        uname  = message.from_user.username or t(lang, "review_moder_no_username")
        num    = user.user_number or "—"
        header = t(lang, "review_moder_header", username=uname, uid=message.from_user.id, num=num)
        try:
            await bot.send_message(MODER_GROUP_ID, header, parse_mode="HTML")
            if message.photo:
                await bot.send_photo(MODER_GROUP_ID, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(MODER_GROUP_ID, message.video.file_id, caption=message.caption or "")
            elif message.text:
                await bot.send_message(MODER_GROUP_ID, message.text)
        except Exception as e:
            logger.warning("Review forward failed | moder=%s | %s", MODER_GROUP_ID, e)
    await message.answer(t(lang, "review_sent"), parse_mode="HTML", reply_markup=back_to_menu_keyboard(lang))


# ─── 👀 Stats ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_stats")
async def cb_my_stats(call: CallbackQuery, session: AsyncSession) -> None:
    lang  = await _lang(session, call.from_user.id)
    user  = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    stats = await repository.get_user_stats(session, call.from_user.id)
    await call.message.edit_text(
        format_personal_stats(stats, user.user_number, lang),
        parse_mode="HTML", reply_markup=back_to_menu_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "public_stats")
async def cb_public_stats(call: CallbackQuery, session: AsyncSession) -> None:
    lang  = await _lang(session, call.from_user.id)
    stats = await repository.get_public_stats(session)
    await call.message.edit_text(
        format_public_stats(stats, lang), parse_mode="HTML",
        reply_markup=public_stats_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "top_winners")
async def cb_top_winners(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    rows = await repository.get_top_winners(session)
    await call.message.edit_text(
        format_top_winners(rows, lang), parse_mode="HTML",
        reply_markup=top_list_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "top_participants")
async def cb_top_participants(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    rows = await repository.get_top_participants(session)
    await call.message.edit_text(
        format_top_participants(rows, lang), parse_mode="HTML",
        reply_markup=top_list_keyboard(lang),
    )
    await call.answer()


# ─── 🤞🏻 Stake — with weekly cooldown + mod notification ─────────────────────

@router.callback_query(F.data == "atm:stake")
async def cb_stake(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    pd   = await repository.get_payment_data(session, call.from_user.id)
    num      = f"▫️{user.user_number}" if user.user_number else ""
    val      = f"<code>{pd.stake_user}</code>" if pd and pd.stake_user else t(lang, "stake_no_data")
    has_data = bool(pd and pd.stake_user)
    await call.message.edit_text(
        t(lang, "stake_header", num=num, val=val),
        parse_mode="HTML",
        reply_markup=stake_keyboard(lang, STAKE_URL, has_data),
    )
    await call.answer()


@router.callback_query(F.data == "stake:edit")
async def cb_stake_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    # Check weekly cooldown
    can, remaining = await repository.check_payment_change_cooldown(
        session, call.from_user.id, "last_stake_change_at", PAYMENT_CHANGE_COOLDOWN_DAYS
    )
    if not can:
        secs = int(remaining.total_seconds())
        d, h = secs // 86400, (secs % 86400) // 3600
        await call.answer(
            t(lang, "payment_cooldown_stake", d=d, h=h),
            show_alert=True,
        )
        return
    await state.set_state(StakeInput.waiting_value)
    await call.message.edit_text(
        t(lang, "stake_enter"), parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:stake"),
    )
    await call.answer()


@router.message(StakeInput.waiting_value)
async def fsm_stake(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, message.from_user.id)
    val  = (message.text or "").strip()
    if not val:
        await message.answer(t(lang, "stake_enter"), parse_mode="HTML")
        return
    await state.clear()
    await repository.upsert_payment_data(session, message.from_user.id, stake_user=val)
    await repository.set_payment_change_timestamp(session, message.from_user.id, "last_stake_change_at")

    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    pd   = await repository.get_payment_data(session, message.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    display = f"<code>{pd.stake_user}</code>" if pd and pd.stake_user else t(lang, "stake_no_data")

    await message.answer(
        t(lang, "stake_saved", val=val) + "\n\n" + t(lang, "stake_header", num=num, val=display),
        parse_mode="HTML",
        reply_markup=stake_keyboard(lang, STAKE_URL, True),
    )
    # Notify mod group
    await _notify_payment_change(bot, lang, user, "Stake username", val)


@router.callback_query(F.data == "stake:delete")
async def cb_stake_delete(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "stake_delete_confirm"),
        reply_markup=stake_delete_confirm_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "stake:delete_confirm")
async def cb_stake_delete_confirm(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, call.from_user.id)
    await repository.clear_payment_field(session, call.from_user.id, "stake_user")
    await repository.set_payment_change_timestamp(session, call.from_user.id, "last_stake_change_at")
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    await call.message.edit_text(
        t(lang, "stake_deleted") + "\n\n" + t(lang, "stake_header", num=num, val=t(lang, "stake_no_data")),
        parse_mode="HTML",
        reply_markup=stake_keyboard(lang, STAKE_URL, False),
    )
    await call.answer()
    await _notify_payment_change(bot, lang, user, "Stake username", "УДАЛЕНО")


# ─── 🟡 Binance — with weekly cooldown + mod notification ────────────────────

@router.callback_query(F.data == "atm:binance")
async def cb_binance(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    pd   = await repository.get_payment_data(session, call.from_user.id)
    num      = f"▫️{user.user_number}" if user.user_number else ""
    val      = f"<code>{pd.binance_id}</code>" if pd and pd.binance_id else t(lang, "stake_no_data")
    has_data = bool(pd and pd.binance_id)
    await call.message.edit_text(
        t(lang, "binance_header", num=num, val=val),
        parse_mode="HTML",
        reply_markup=binance_keyboard(lang, BINANCE_URL, has_data),
    )
    await call.answer()


@router.callback_query(F.data == "binance:edit")
async def cb_binance_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    # Check weekly cooldown
    can, remaining = await repository.check_payment_change_cooldown(
        session, call.from_user.id, "last_binance_change_at", PAYMENT_CHANGE_COOLDOWN_DAYS
    )
    if not can:
        secs = int(remaining.total_seconds())
        d, h = secs // 86400, (secs % 86400) // 3600
        await call.answer(
            t(lang, "payment_cooldown_binance", d=d, h=h),
            show_alert=True,
        )
        return
    await state.set_state(BinanceInput.waiting_value)
    await call.message.edit_text(
        t(lang, "binance_enter"), parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:binance"),
    )
    await call.answer()


@router.message(BinanceInput.waiting_value)
async def fsm_binance(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, message.from_user.id)
    val  = (message.text or "").strip()
    if not val:
        await message.answer(t(lang, "binance_enter"), parse_mode="HTML")
        return
    await state.clear()
    await repository.upsert_payment_data(session, message.from_user.id, binance_id=val)
    await repository.set_payment_change_timestamp(session, message.from_user.id, "last_binance_change_at")

    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    pd   = await repository.get_payment_data(session, message.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    display = f"<code>{pd.binance_id}</code>" if pd and pd.binance_id else t(lang, "stake_no_data")

    await message.answer(
        t(lang, "binance_saved", val=val) + "\n\n" + t(lang, "binance_header", num=num, val=display),
        parse_mode="HTML",
        reply_markup=binance_keyboard(lang, BINANCE_URL, True),
    )
    # Notify mod group
    await _notify_payment_change(bot, lang, user, "Binance ID", val)


@router.callback_query(F.data == "binance:delete")
async def cb_binance_delete(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "binance_delete_confirm"),
        reply_markup=binance_delete_confirm_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "binance:delete_confirm")
async def cb_binance_delete_confirm(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, call.from_user.id)
    await repository.clear_payment_field(session, call.from_user.id, "binance_id")
    await repository.set_payment_change_timestamp(session, call.from_user.id, "last_binance_change_at")
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    await call.message.edit_text(
        t(lang, "binance_deleted") + "\n\n" + t(lang, "binance_header", num=num, val=t(lang, "stake_no_data")),
        parse_mode="HTML",
        reply_markup=binance_keyboard(lang, BINANCE_URL, False),
    )
    await call.answer()
    await _notify_payment_change(bot, lang, user, "Binance ID", "УДАЛЕНО")


# ─── FSM cancel ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_fsm")
async def cb_cancel_fsm(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        f"{BOT_GREETING}\n\n{t(lang, 'menu_text')}",
        reply_markup=main_menu_keyboard(lang),
    )
    await call.answer()
