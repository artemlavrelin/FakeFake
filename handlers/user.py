"""Main user handler — /start, menu, raffle, stats, payment sections."""
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
    back_to_menu_keyboard,
    binance_delete_confirm_keyboard, binance_has_data_keyboard, binance_no_data_keyboard,
    binance_replace_confirm_keyboard,
    cancel_keyboard,
    contest_not_participating_keyboard, contest_participating_keyboard,
    hub_keyboard,
    lang_keyboard,
    main_menu_keyboard_v11 as main_menu_keyboard,
    my_stats_keyboard,
    participate_confirm_keyboard,
    profile_keyboard,
    public_stats_keyboard,
    raffle_no_contest_keyboard,
    report_keyboard,
    stake_delete_confirm_keyboard, stake_has_data_keyboard, stake_no_data_keyboard,
    stake_replace_confirm_keyboard,
    tasks_menu_keyboard,
    top_list_keyboard,
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

MIN_WITHDRAWAL = 3.0   # minimum $3 withdrawal


async def _lang(session: AsyncSession, tid: int) -> str:
    user = await repository.get_user(session, tid)
    return (user.lang or "ru") if user else "ru"


async def _notify_payment_change(bot: Bot, lang: str, user, field_label: str, new_value: str) -> None:
    if not MODER_GROUP_ID:
        return
    uname = user.username or "(нет username)"
    num   = user.user_number or "—"
    try:
        text = (
            f"Изменение платёжных данных\n\n"
            f"@{uname} | {user.telegram_id} | {num}\n"
            f"Поле: {field_label}\n"
            f"Новое значение: {new_value}"
        )
        await bot.send_message(MODER_GROUP_ID, text)
    except Exception as e:
        logger.warning("Payment change notify | moder=%s | %s", MODER_GROUP_ID, e)


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    if not user.lang:
        await message.answer(f"{BOT_GREETING}\n\n{t('ru', 'choose_language')}",
                              reply_markup=lang_keyboard()); return
    args    = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else ""
    if payload.startswith("contest_"):
        await _show_raffle(message, session, user.lang, edit=False); return
    await message.answer(f"{BOT_GREETING}\n\n{t(user.lang, 'menu_text')}",
                          reply_markup=main_menu_keyboard(user.lang))


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(call: CallbackQuery, session: AsyncSession) -> None:
    lang = call.data.split(":")[1]
    await repository.set_lang(session, call.from_user.id, lang)
    await call.message.edit_text(f"{BOT_GREETING}\n\n{t(lang, 'menu_text')}",
                                  reply_markup=main_menu_keyboard(lang))
    await call.answer()


@router.callback_query(F.data == "switch_lang")
async def cb_switch_lang(call: CallbackQuery, session: AsyncSession) -> None:
    current  = await _lang(session, call.from_user.id)
    new_lang = "en" if current == "ru" else "ru"
    await repository.set_lang(session, call.from_user.id, new_lang)
    await call.message.edit_text(f"{BOT_GREETING}\n\n{t(new_lang, 'menu_text')}",
                                  reply_markup=main_menu_keyboard(new_lang))
    await call.answer()


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(f"{BOT_GREETING}\n\n{t(lang, 'menu_text')}",
                                  reply_markup=main_menu_keyboard(lang))
    await call.answer()


# ─── 🤹🏼 РОЗЫГРЫШ ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "raffle")
async def cb_raffle(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await _show_raffle(call, session, lang, edit=True)


async def _show_raffle(event, session: AsyncSession, lang: str, edit: bool) -> None:
    is_call = isinstance(event, CallbackQuery)
    uid     = event.from_user.id
    msg     = event.message if is_call else event

    user    = await repository.get_or_create_user(session, uid, event.from_user.username)
    stats   = await repository.get_public_stats(session)

    # Always show public stats on raffle screen
    prize_str = f"${stats['total_prize_sum']:.0f}" if stats["total_prize_sum"] > 0 else "—"
    stats_block = (
        f"\n🎢 Проведено конкурсов: {stats['finished_count']}\n"
        f"🤞🏻 Участвовали: {stats['total_participants']}\n"
        f"🏅 Победители: {stats['total_winners']}\n"
        f"💵 Выплачено: {prize_str}"
    )

    contest = await repository.get_active_contest(session)

    if not contest:
        text = f"🤹🏼 <b>РОЗЫГРЫШ</b>\n\nСейчас нет активного конкурса.\n{stats_block}"
        kb   = raffle_no_contest_keyboard(lang)
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        if is_call:
            await event.answer()
        return

    count   = await repository.get_participant_count(session, contest.id)
    already = await repository.is_participant(session, contest.id, uid)
    chance  = calc_chance(contest.winners_count, count, already)
    bar     = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)

    if already:
        status, kb = "👉 Вы участвуете в конкурсе, удачи 🤞🏻", contest_participating_keyboard(lang)
    elif user.is_banned:
        status, kb = "❌ Вы заблокированы", back_to_menu_keyboard(lang)
    else:
        status, kb = "❌", contest_not_participating_keyboard(lang)

    text = (
        f"🤹🏾‍♀️ <b>#{contest.id} ТЕКУЩИЙ КОНКУРС</b>\n\n"
        f"📌 {contest.title}\n\n"
        f"{bar}\n\n"
        f"{status}"
        f"{stats_block}"
    )
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
        await call.answer("🚫 Вы заблокированы.", show_alert=True); return
    contest = await repository.get_active_contest(session)
    if not contest:
        await call.answer("Конкурс завершён.", show_alert=True); return
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True); return
    count  = await repository.get_participant_count(session, contest.id)
    chance = calc_chance(contest.winners_count, count + 1, True)
    bar    = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)
    await call.message.edit_text(
        f"📌 {contest.title}\n\n{bar}\n\nПринять участие?",
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
        await call.answer("🚫 Вы заблокированы.", show_alert=True); return
    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.message.edit_text("Конкурс завершён.", reply_markup=back_to_menu_keyboard(lang))
        await call.answer(); return
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True); return
    await repository.add_participant(session, contest.id, call.from_user.id)
    count  = await repository.get_participant_count(session, contest.id)
    chance = calc_chance(contest.winners_count, count, True)
    bar    = stats_bar(time_ago(contest.created_at), count, contest.winners_count, contest.prize_text, chance)
    await call.message.edit_text(
        f"✅ <b>Вы зарегистрированы!</b>\n\n{bar}\n\n👉 Ожидайте результатов. Удачи! 🤞🏻",
        parse_mode="HTML", reply_markup=back_to_menu_keyboard(lang),
    )
    await call.answer("✅ Принято!")


@router.callback_query(F.data.startswith("group_join:"))
async def cb_group_join(call: CallbackQuery, session: AsyncSession) -> None:
    contest_id = int(call.data.split(":")[1])
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    lang = user.lang or "ru"
    if user.is_banned:
        await call.answer("🚫 Вы заблокированы.", show_alert=True); return
    contest = await repository.get_active_contest(session)
    if not contest or contest.id != contest_id:
        await call.answer("Конкурс завершён.", show_alert=True); return
    if await repository.is_participant(session, contest.id, call.from_user.id):
        await call.answer("👉 Вы уже участвуете!", show_alert=True); return
    await repository.add_participant(session, contest.id, call.from_user.id)
    count = await repository.get_participant_count(session, contest.id)
    await call.answer(f"✅ Зарегистрированы! Участников: {count}", show_alert=True)


# ─── ⭐️ Hub ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "hub")
async def cb_hub(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        "⭐️ <b>Выплаты / Отзывы / Статистика</b>",
        parse_mode="HTML",
        reply_markup=hub_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "report")
async def cb_report(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text(
        f"⭐️ <b>ВЫПЛАТЫ / ОТЗЫВЫ</b>\n\n"
        f"<b>{REPORT_CHANNEL_TITLE}</b> — прозрачная отчётность:\n\n"
        "• ✅ Подтверждения выплат\n"
        "• 🏆 Результаты розыгрышей\n"
        "• 💬 Отзывы участников\n"
        "• 📊 Статистика победителей\n\n"
        "Перейди в канал или оставь отзыв:",
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
        await call.answer(f"⏳ Следующий отзыв через {h}ч {m}м.", show_alert=True); return
    await state.set_state(ReviewInput.waiting_content)
    await call.message.edit_text(
        "✍️ Отправьте текст, фото или видео. Один отзыв каждые 12 часов.",
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
        await message.answer("✅ Спасибо!", reply_markup=back_to_menu_keyboard(lang)); return
    await state.clear()
    await repository.set_timestamp(session, message.from_user.id, "last_review_at")
    if MODER_GROUP_ID:
        uname = message.from_user.username or "(нет username)"
        num   = user.user_number or "—"
        header = f"Новый отзыв\n\n@{uname} | {message.from_user.id} | {num}"
        try:
            await bot.send_message(MODER_GROUP_ID, header)
            if message.photo:
                await bot.send_photo(MODER_GROUP_ID, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(MODER_GROUP_ID, message.video.file_id, caption=message.caption or "")
            elif message.text:
                await bot.send_message(MODER_GROUP_ID, message.text)
        except Exception as e:
            logger.warning("Review forward | %s", e)
    await message.answer("✅ Спасибо! Отзыв отправлен.", reply_markup=back_to_menu_keyboard(lang))


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_stats_full")
async def cb_my_stats_full(call: CallbackQuery, session: AsyncSession) -> None:
    user    = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    balance = await repository.get_or_create_balance(session, call.from_user.id)
    stats   = await repository.get_user_stats(session, call.from_user.id)
    profile = user.profile
    from database.models import STATUS_ICONS
    num    = f"▫️{user.user_number}" if user.user_number else "▫️—"
    status = STATUS_ICONS.get(profile.status if profile else "new", "…..")
    total  = balance.balance + balance.paid_out
    lang   = await _lang(session, call.from_user.id)

    await call.message.edit_text(
        f"{status} {num}\n\n"
        f"<b>РОЗЫГРЫШ:</b>\n"
        f"🤽 {stats['participations']}   🏅 {stats['wins']}   💵 ${stats['prize_sum']:.2f}\n\n"
        f"⭐️ Баланс: <b>${balance.balance:.2f}</b>\n"
        f"💫 Выплачено: <b>${balance.paid_out:.2f}</b>\n"
        f"✨ Всего: <b>${total:.2f}</b>",
        parse_mode="HTML",
        reply_markup=my_stats_keyboard(lang),
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
        format_top_winners(rows, lang), parse_mode="HTML", reply_markup=top_list_keyboard(lang),
    )
    await call.answer()


@router.callback_query(F.data == "top_participants")
async def cb_top_participants(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    rows = await repository.get_top_participants(session)
    await call.message.edit_text(
        format_top_participants(rows, lang), parse_mode="HTML", reply_markup=top_list_keyboard(lang),
    )
    await call.answer()


# ─── 🥼 ПРОФИЛЬ ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery, session: AsyncSession) -> None:
    user    = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    profile = user.profile or await repository.get_or_create_profile(session, call.from_user.id)
    pd      = user.payment

    from database.models import STATUS_ICONS
    num    = f"▫️{user.user_number}" if user.user_number else "▫️—"
    status = STATUS_ICONS.get(profile.status, "…..")
    stake  = pd.stake_user  if pd and pd.stake_user  else "—"
    binance= pd.binance_id  if pd and pd.binance_id  else "—"
    insta  = f"@{profile.instagram}" if profile.instagram else "—"
    threads= f"@{profile.threads}"   if profile.threads   else "—"
    fb     = profile.facebook or "—"
    tw     = f"@{profile.twitter}"   if profile.twitter   else "—"
    tiktok = f"@{profile.tiktok}"    if hasattr(profile, 'tiktok') and profile.tiktok else "—"

    has_social = any([profile.instagram, profile.threads, profile.facebook, profile.twitter])

    await call.message.edit_text(
        f"🥼 <b>ПРОФИЛЬ</b> {status} {num}\n\n"
        f"♠️ Stake: {stake}\n"
        f"🟨 Binance: {binance}\n\n"
        f"🐦 X: {tw}\n"
        f"🔵 Facebook: {fb}\n"
        f"🔸 Instagram: {insta}\n"
        f"🧵 Threads: {threads}\n"
        f"🎶 TikTok: {tiktok}",
        parse_mode="HTML",
        reply_markup=profile_keyboard(has_social),
    )
    await call.answer()


# ─── 🃏 ЗАДАНИЯ ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "tasks")
async def cb_tasks_entry(call: CallbackQuery, session: AsyncSession) -> None:
    if await repository.get_user(session, call.from_user.id) and \
       (await repository.get_user(session, call.from_user.id)).is_afk:
        await call.answer("👅 Вам доступна только команда /report", show_alert=True); return
    await call.message.edit_text(
        "🃏 <b>ЗАДАНИЯ</b>\n\nНажмите кнопку чтобы получить задание:",
        parse_mode="HTML",
        reply_markup=tasks_menu_keyboard(),
    )
    await call.answer()


# ─── ♠️ Stake — Add (no notify) / Edit (cooldown + notify) ────────────────────

@router.callback_query(F.data == "atm:stake")
async def cb_stake(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    pd   = await repository.get_payment_data(session, call.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    val  = pd.stake_user if pd and pd.stake_user else None
    if val:
        text = f"♠️ <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: <code>{val}</code>"
        kb   = stake_has_data_keyboard(lang, STAKE_URL)
    else:
        text = f"♠️ <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: —"
        kb   = stake_no_data_keyboard(lang, STAKE_URL)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "stake:add")
async def cb_stake_add(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await state.set_state(StakeInput.waiting_value)
    await state.update_data(is_first_add=True)
    await call.message.edit_text(
        "♠️ Введите ваш <b>Stake username</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:stake"),
    )
    await call.answer()


@router.callback_query(F.data == "stake:edit")
async def cb_stake_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    can, remaining = await repository.check_payment_change_cooldown(
        session, call.from_user.id, "last_stake_change_at", PAYMENT_CHANGE_COOLDOWN_DAYS
    )
    if not can:
        secs = int(remaining.total_seconds())
        d, h = secs // 86400, (secs % 86400) // 3600
        await call.answer(f"⏳ Изменить можно через {d}д {h}ч.", show_alert=True); return
    await state.set_state(StakeInput.waiting_value)
    await state.update_data(is_first_add=False)
    await call.message.edit_text(
        "♠️ Введите новый <b>Stake username</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:stake"),
    )
    await call.answer()


@router.message(StakeInput.waiting_value)
async def fsm_stake(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, message.from_user.id)
    val  = (message.text or "").strip()
    if not val:
        await message.answer("♠️ Введите Stake username:"); return

    data         = await state.get_data()
    is_first_add = data.get("is_first_add", True)
    new_val      = data.get("pending_value")

    # If we have a pending value (after replace confirmation), use it
    if new_val:
        val = new_val

    # Check uniqueness
    pd_check, err = await repository.upsert_payment_field(session, message.from_user.id, "stake_user", val)
    if err:
        await state.clear()
        await message.answer(err); return

    await state.clear()
    await repository.update_user_slot  # placeholder

    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    pd   = await repository.get_payment_data(session, message.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""

    if not is_first_add:
        await repository.set_payment_change_timestamp(session, message.from_user.id, "last_stake_change_at")
        await _notify_payment_change(bot, lang, user, "Stake username", val)
        msg_key = "Stake username обновлён"
    else:
        msg_key = "Stake username сохранён"

    await message.answer(
        f"✅ {msg_key}: <code>{val}</code>\n\n"
        f"♠️ <b>STAKE</b>\n\n{num}\n\n"
        f"🎰 Stake username: <code>{pd.stake_user}</code>",
        parse_mode="HTML",
        reply_markup=stake_has_data_keyboard(lang, STAKE_URL),
    )


@router.callback_query(F.data == "stake:delete")
async def cb_stake_delete(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text("Удалить Stake username?",
                                  reply_markup=stake_delete_confirm_keyboard(lang))
    await call.answer()


@router.callback_query(F.data == "stake:delete_confirm")
async def cb_stake_delete_confirm(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, call.from_user.id)
    await repository.clear_payment_field(session, call.from_user.id, "stake_user")
    await repository.set_payment_change_timestamp(session, call.from_user.id, "last_stake_change_at")
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    await call.message.edit_text(
        f"🗑 Stake username удалён.\n\n♠️ <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: —",
        parse_mode="HTML",
        reply_markup=stake_no_data_keyboard(lang, STAKE_URL),
    )
    await call.answer()
    await _notify_payment_change(bot, lang, user, "Stake username", "УДАЛЕНО")


# ─── 🟨 Binance — Add (no notify) / Edit (cooldown + notify) ─────────────────

@router.callback_query(F.data == "atm:binance")
async def cb_binance(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    pd   = await repository.get_payment_data(session, call.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    val  = pd.binance_id if pd and pd.binance_id else None
    if val:
        text = f"🟨 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: <code>{val}</code>"
        kb   = binance_has_data_keyboard(lang, BINANCE_URL)
    else:
        text = f"🟨 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: —"
        kb   = binance_no_data_keyboard(lang, BINANCE_URL)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "binance:add")
async def cb_binance_add(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await state.set_state(BinanceInput.waiting_value)
    await state.update_data(is_first_add=True)
    await call.message.edit_text(
        "🟨 Введите ваш <b>Binance ID</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:binance"),
    )
    await call.answer()


@router.callback_query(F.data == "binance:edit")
async def cb_binance_edit(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    can, remaining = await repository.check_payment_change_cooldown(
        session, call.from_user.id, "last_binance_change_at", PAYMENT_CHANGE_COOLDOWN_DAYS
    )
    if not can:
        secs = int(remaining.total_seconds())
        d, h = secs // 86400, (secs % 86400) // 3600
        await call.answer(f"⏳ Изменить можно через {d}д {h}ч.", show_alert=True); return
    await state.set_state(BinanceInput.waiting_value)
    await state.update_data(is_first_add=False)
    await call.message.edit_text(
        "🟨 Введите новый <b>Binance ID</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(lang, back_cb="atm:binance"),
    )
    await call.answer()


@router.message(BinanceInput.waiting_value)
async def fsm_binance(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, message.from_user.id)
    val  = (message.text or "").strip()
    if not val:
        await message.answer("🟨 Введите Binance ID:"); return

    data         = await state.get_data()
    is_first_add = data.get("is_first_add", True)

    pd_result, err = await repository.upsert_payment_field(session, message.from_user.id, "binance_id", val)
    if err:
        await state.clear()
        await message.answer(err); return

    await state.clear()
    user = await repository.get_or_create_user(session, message.from_user.id, message.from_user.username)
    pd   = await repository.get_payment_data(session, message.from_user.id)
    num  = f"▫️{user.user_number}" if user.user_number else ""

    if not is_first_add:
        await repository.set_payment_change_timestamp(session, message.from_user.id, "last_binance_change_at")
        await _notify_payment_change(bot, lang, user, "Binance ID", val)
        msg_key = "Binance ID обновлён"
    else:
        msg_key = "Binance ID сохранён"

    await message.answer(
        f"✅ {msg_key}: <code>{val}</code>\n\n"
        f"🟨 <b>BINANCE</b>\n\n{num}\n\n"
        f"💛 Binance ID: <code>{pd.binance_id}</code>",
        parse_mode="HTML",
        reply_markup=binance_has_data_keyboard(lang, BINANCE_URL),
    )


@router.callback_query(F.data == "binance:delete")
async def cb_binance_delete(call: CallbackQuery, session: AsyncSession) -> None:
    lang = await _lang(session, call.from_user.id)
    await call.message.edit_text("Удалить Binance ID?",
                                  reply_markup=binance_delete_confirm_keyboard(lang))
    await call.answer()


@router.callback_query(F.data == "binance:delete_confirm")
async def cb_binance_delete_confirm(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    lang = await _lang(session, call.from_user.id)
    await repository.clear_payment_field(session, call.from_user.id, "binance_id")
    await repository.set_payment_change_timestamp(session, call.from_user.id, "last_binance_change_at")
    user = await repository.get_or_create_user(session, call.from_user.id, call.from_user.username)
    num  = f"▫️{user.user_number}" if user.user_number else ""
    await call.message.edit_text(
        f"🗑 Binance ID удалён.\n\n🟨 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: —",
        parse_mode="HTML",
        reply_markup=binance_no_data_keyboard(lang, BINANCE_URL),
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
