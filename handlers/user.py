from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize, Video
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    BINANCE_URL, MODER_GROUP_ID, REPORT_CHANNEL_TITLE,
    REPORT_CHANNEL_URL, REVIEW_COOLDOWN_HOURS, STAKE_URL,
)
from database import repository
from i18n import t
from keyboards.inline import (
    atm_keyboard,
    back_to_menu_keyboard,
    binance_delete_confirm_keyboard,
    binance_keyboard,
    cancel_keyboard,
    contest_not_participating_keyboard,
    contest_participating_keyboard,
    lang_keyboard,
    main_menu_keyboard,
    participate_confirm_keyboard,
    public_stats_keyboard,
    report_keyboard,
    reviews_keyboard,
    stake_delete_confirm_keyboard,
    stake_keyboard,
    top_list_keyboard,
)
from states.contest import BinanceInput, ReviewInput, StakeInput
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


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _lang(session: AsyncSession, telegram_id: int) -> str:
    user = await repository.get_user(session, telegram_id)
    return (user.lang or "ru") if user else "ru"


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await repository.get_or_create_user(
        session, message.from_user.id, message.from_user.username
    )

    # New user or lang not set → show language picker
    if not user.lang:
        await message.answer(
            "Выберите язык / Choose language:",
            reply_markup=lang_keyboard(),
        )
        return

    args    = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else ""
    if payload.startswith("contest_"):
        await _show_raffle(message, session, user.lang, edit=False)
        return

    await message.answer(t(user.lang, "menu_text"), reply_markup=main_menu_keyboard(user.lang))


# ─── Language selection ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(call: CallbackQuery, session: AsyncSession) -> None:
    lang = call.data.split(":")[1]   # "ru" or "en"
    await repository.set_lang(session, call.from_user.id, lang)
    await call.message.edit_text(
        t(lang, "menu_text"), reply_markup=main_menu_keyboard(lang)
    )
    await call.answer()


@router.callback_query(F.data == "switch_lang")
async def cb_switch_lang(call: CallbackQuery, session: AsyncSession) -> None:
    current = await _lang(session, call.from_user.id)
    new_lang = "en" if current == "ru" else "ru"
    await repository.set_lang(session, call.from_user.id, new_lang)
    await call.message.edit_text(
        t(new_lang, "menu_text"), reply_markup=main_menu_keyboard(new_lang)
    )
    await call.answer()


# ─── Menu ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(t(lang, "menu_text"), reply_markup=main_menu_keyboard(lang))
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
        kb   = back_to_menu_keyboard(lang)
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
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


# ─── ⭐️ Report ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "report")
async def cb_report(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "report_text", title=REPORT_CHANNEL_TITLE),
        parse_mode="HTML",
        reply_markup=report_keyboard(lang, REPORT_CHANNEL_URL),
    )
    await call.answer()


# ─── 👀 My stats ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_stats")
async def cb_my_stats(call: CallbackQuery, session: AsyncSession) -> None:
    lang  = await _lang(session, call.from_user.id)
    user  = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    stats = await repository.get_user_stats(session, call.from_user.id)
    await call.message.edit_text(
        format_personal_stats(stats, user.user_number, lang),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(lang),
    )
    await call.answer()


# ─── 👥 Public stats ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "public_stats")
async def cb_public_stats(call: CallbackQuery, session: AsyncSession) -> None:
    lang  = await _lang(session, call.from_user.id)
    stats = await repository.get_public_stats(session)
    await call.message.edit_text(
        format_public_stats(stats, lang),
        parse_mode="HTML",
        reply_markup=public_stats_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "top_winners")
async def cb_top_winners(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    rows = await repository.get_top_winners(session)
    await call.message.edit_text(
        format_top_winners(rows, lang),
        parse_mode="HTML",
        reply_markup=top_list_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "top_participants")
async def cb_top_participants(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    rows = await repository.get_top_participants(session)
    await call.message.edit_text(
        format_top_participants(rows, lang),
        parse_mode="HTML",
        reply_markup=top_list_keyboard(lang),
    )
    await call.answer()


# ─── 🧲 ATM hub ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "atm")
async def cb_atm(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "atm_header"),
        parse_mode="HTML",
        reply_markup=atm_keyboard(lang),
    )
    await call.answer()


# ─── 🎰 Stake section ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "atm:stake")
async def cb_atm_stake(call: CallbackQuery, session: AsyncSession) -> None:
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
    await state.set_state(StakeInput.waiting_value)
    await call.message.edit_text(
        t(lang, "stake_enter"),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:stake"),
    )
    await call.answer()


@router.message(StakeInput.waiting_value)
async def fsm_stake_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, message.from_user.id)
    val  = (message.text or "").strip()
    if not val:
        await message.answer(t(lang, "stake_enter"), parse_mode="HTML")
        return
    await state.clear()
    await repository.upsert_payment_data(session, message.from_user.id, stake_user=val)
    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    pd   = await repository.get_payment_data(session, message.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    display = f"<code>{pd.stake_user}</code>" if pd and pd.stake_user else t(lang, "stake_no_data")
    await message.answer(
        t(lang, "stake_saved", val=val) + f"\n\n" + t(lang, "stake_header", num=num, val=display),
        parse_mode="HTML",
        reply_markup=stake_keyboard(lang, STAKE_URL, True),
    )


@router.callback_query(F.data == "stake:delete")
async def cb_stake_delete(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "stake_delete_confirm"),
        reply_markup=stake_delete_confirm_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "stake:delete_confirm")
async def cb_stake_delete_confirm(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await repository.clear_payment_field(session, call.from_user.id, "stake_user")
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    await call.message.edit_text(
        t(lang, "stake_deleted") + "\n\n" + t(lang, "stake_header", num=num, val=t(lang, "stake_no_data")),
        parse_mode="HTML",
        reply_markup=stake_keyboard(lang, STAKE_URL, False),
    )
    await call.answer()


# ─── 🟡 Binance section ───────────────────────────────────────────────────────

@router.callback_query(F.data == "atm:binance")
async def cb_atm_binance(call: CallbackQuery, session: AsyncSession) -> None:
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
    await state.set_state(BinanceInput.waiting_value)
    await call.message.edit_text(
        t(lang, "binance_enter"),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:binance"),
    )
    await call.answer()


@router.message(BinanceInput.waiting_value)
async def fsm_binance_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, message.from_user.id)
    val  = (message.text or "").strip()
    if not val:
        await message.answer(t(lang, "binance_enter"), parse_mode="HTML")
        return
    await state.clear()
    await repository.upsert_payment_data(session, message.from_user.id, binance_id=val)
    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    pd   = await repository.get_payment_data(session, message.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    display = f"<code>{pd.binance_id}</code>" if pd and pd.binance_id else t(lang, "stake_no_data")
    await message.answer(
        t(lang, "binance_saved", val=val) + "\n\n" + t(lang, "binance_header", num=num, val=display),
        parse_mode="HTML",
        reply_markup=binance_keyboard(lang, BINANCE_URL, True),
    )


@router.callback_query(F.data == "binance:delete")
async def cb_binance_delete(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "binance_delete_confirm"),
        reply_markup=binance_delete_confirm_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "binance:delete_confirm")
async def cb_binance_delete_confirm(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await repository.clear_payment_field(session, call.from_user.id, "binance_id")
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    await call.message.edit_text(
        t(lang, "binance_deleted") + "\n\n" + t(lang, "binance_header", num=num, val=t(lang, "stake_no_data")),
        parse_mode="HTML",
        reply_markup=binance_keyboard(lang, BINANCE_URL, False),
    )
    await call.answer()


# ─── 💬 Reviews ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "reviews")
async def cb_reviews(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        t(lang, "reviews_menu"),
        parse_mode="HTML",
        reply_markup=reviews_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "review:start")
async def cb_review_start(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)

    can, remaining = await repository.check_review_cooldown(
        session, call.from_user.id, REVIEW_COOLDOWN_HOURS
    )
    if not can:
        total_secs = int(remaining.total_seconds())
        h = total_secs // 3600
        m = (total_secs % 3600) // 60
        await call.answer(t(lang, "review_cooldown", h=h, m=m), show_alert=True)
        return

    await state.set_state(ReviewInput.waiting_content)
    await call.message.edit_text(
        t(lang, "review_prompt"),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="reviews"),
    )
    await call.answer()


@router.message(ReviewInput.waiting_content, F.text | F.photo | F.video)
async def fsm_review_content(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, message.from_user.id)
    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)

    # Re-check cooldown (race-condition guard)
    can, _ = await repository.check_review_cooldown(session, message.from_user.id, REVIEW_COOLDOWN_HOURS)
    if not can:
        await state.clear()
        await message.answer(t(lang, "review_sent"), parse_mode="HTML",
                             reply_markup=back_to_menu_keyboard(lang))
        return

    await state.clear()
    await repository.set_last_review(session, message.from_user.id)

    # Forward to moderator group
    if MODER_GROUP_ID:
        username    = message.from_user.username or t(lang, "review_moder_no_username")
        num         = user.user_number or "—"
        header_text = t(lang, "review_moder_header",
                        username=username, uid=message.from_user.id, num=num)
        try:
            await bot.send_message(MODER_GROUP_ID, header_text, parse_mode="HTML")

            if message.photo:
                # Largest photo size
                photo = message.photo[-1]
                await bot.send_photo(
                    MODER_GROUP_ID,
                    photo=photo.file_id,
                    caption=message.caption or "",
                )
            elif message.video:
                await bot.send_video(
                    MODER_GROUP_ID,
                    video=message.video.file_id,
                    caption=message.caption or "",
                )
            elif message.text:
                await bot.send_message(MODER_GROUP_ID, message.text)
        except Exception as e:
            logger.warning("Review forward failed | %s", e)

    await message.answer(
        t(lang, "review_sent"),
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(lang),
    )


# ─── FSM cancel ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_fsm")
async def cb_cancel_fsm_user(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(t(lang, "menu_text"), reply_markup=main_menu_keyboard(lang))
    await call.answer()
