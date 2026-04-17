class RU:
    # ── Language picker ──────────────────────────────────────────
    choose_language     = "Выберите язык / Choose language:"

    # ── Main menu ────────────────────────────────────────────────
    menu_text           = "Выбери раздел:"
    btn_raffle          = "🤹🏻 Розыгрыш"
    btn_report          = "⭐️ Выплаты / Отзывы"
    btn_my_stats        = "👀 Моя статистика"
    btn_public_stats    = "👥 Общая статистика"
    btn_atm             = "🧲 АТМ"
    btn_reviews         = "💬 Отзывы"
    btn_back            = "⬅️ Назад"
    btn_cancel          = "⬅️ Отмена"
    btn_to_menu         = "⬅️ В меню"

    # ── Raffle ───────────────────────────────────────────────────
    raffle_no_contest   = "🤹🏻 <b>РОЗЫГРЫШ</b>\n\nСейчас нет активного конкурса.\nСледите за обновлениями!"
    raffle_header       = "🤹🏻 <b>#{id} ТЕКУЩИЙ КОНКУРС</b>\n\n📌 {title}\n\n{bar}\n\n{status}"
    raffle_participating = "👉 Вы участвуете в конкурсе, удачи 🤞🏻"
    raffle_not_participating = "❌ Вы не участвуете"
    raffle_banned       = "❌ Вы заблокированы"
    btn_participate     = "🔥 Участвовать"
    raffle_confirm_text = "📌 {title}\n\n{bar}\n\nПринять участие?"
    btn_confirm         = "✅ Подтвердить"
    raffle_joined       = "✅ <b>Вы зарегистрированы!</b>\n\n📌 {title}\n\n{bar}\n\n👉 Ожидайте результатов. Удачи! 🤞🏻"
    raffle_already      = "👉 Вы уже участвуете!"
    raffle_banned_alert = "🚫 Вы заблокированы."
    raffle_finished     = "Конкурс завершён."

    # ── Report ───────────────────────────────────────────────────
    report_text         = (
        "⭐️ <b>ВЫПЛАТЫ / ОТЗЫВЫ</b>\n\n"
        "<b>{title}</b> — прозрачная отчётность системы:\n\n"
        "• ✅ Подтверждения выплат\n"
        "• 🏆 Результаты розыгрышей\n"
        "• 💬 Отзывы участников\n"
        "• 📊 Статистика победителей\n"
        "• 🔍 Данные, подтверждающие прозрачность работы\n\n"
        "Перейди в канал, чтобы убедиться в честности системы:"
    )
    btn_go              = "➡️ Перейти"

    # ── My stats ─────────────────────────────────────────────────
    stats_header        = "👀 <b>МОЯ СТАТИСТИКА</b>"
    stats_participations = "🎲 Участий: <b>{n}</b>"
    stats_wins          = "🔥 Побед: <b>{n}</b>"
    stats_prize_sum     = "💵 Сумма выигрышей: <b>{s}</b>"
    stats_last_win      = "🍷 Последняя победа: <b>{d}</b>"
    stats_no_wins       = "\nУдачи в следующий раз! 🍀"
    stats_won_once      = "\nВы побеждали 1× — отличный результат! 🌟"
    stats_won_many      = "\nВы побеждали {n}× — вы везунчик! 🌟"

    # ── Public stats ─────────────────────────────────────────────
    public_stats_header = "👥 <b>ОБЩАЯ СТАТИСТИКА</b>"
    public_finished     = "🤹🏻 Завершено конкурсов: <b>{n}</b>"
    public_participants = "👥 Всего участий: <b>{n}</b>"
    public_winners      = "🏆 Победителей выбрано: <b>{n}</b>"
    public_prize_sum    = "💰 Сумма призов: <b>{s}</b>"
    btn_top_winners     = "🏆 Топ победителей"
    btn_top_participants = "👥 Топ участников"
    top_winners_header  = "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>"
    top_winners_empty   = "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>\n\nПока нет данных."
    top_parts_header    = "👥 <b>ТОП УЧАСТНИКОВ</b>"
    top_parts_empty     = "👥 <b>ТОП УЧАСТНИКОВ</b>\n\nПока нет данных."
    top_wins_row        = "{medal} {name} — <b>{n}</b> побед"
    top_parts_row       = "{medal} {name} — <b>{n}</b> участий"

    # ── ATM ──────────────────────────────────────────────────────
    atm_header          = "🧲 <b>АТМ «МАГНИТ»</b>"
    btn_stake           = "🎰 Stake"
    btn_binance         = "🟡 Binance"

    # ── Stake section ────────────────────────────────────────────
    stake_header        = "🎰 <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: {val}"
    stake_no_data       = "—"
    btn_edit            = "✏️ Изменить данные"
    btn_delete          = "🗑 Удалить данные"
    btn_reg_stake       = "🔗 Reg Stake"
    stake_enter         = "🎰 Введите ваш <b>Stake username</b>:"
    stake_saved         = "✅ Stake username сохранён: <code>{val}</code>"
    stake_deleted       = "🗑 Stake username удалён."
    stake_delete_confirm = "Удалить Stake username?"
    btn_yes_delete      = "✅ Да, удалить"

    # ── Binance section ──────────────────────────────────────────
    binance_header      = "🟡 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: {val}"
    btn_reg_binance     = "🔗 Reg Binance"
    binance_enter       = "🟡 Введите ваш <b>Binance ID</b>:"
    binance_saved       = "✅ Binance ID сохранён: <code>{val}</code>"
    binance_deleted     = "🗑 Binance ID удалён."
    binance_delete_confirm = "Удалить Binance ID?"

    # ── Reviews ──────────────────────────────────────────────────
    reviews_menu        = "💬 <b>ОТЗЫВЫ</b>\n\nПоделитесь своим опытом — это помогает сообществу."
    btn_leave_review    = "✍️ Оставить отзыв"
    review_prompt       = (
        "✍️ <b>Напишите ваш отзыв</b>\n\n"
        "Вы можете отправить:\n"
        "• текст\n• фото\n• видео\n\n"
        "Один отзыв каждые 12 часов."
    )
    review_sent         = "✅ Спасибо! Ваш отзыв отправлен на модерацию."
    review_cooldown     = "⏳ Вы уже оставляли отзыв. Следующий можно отправить через <b>{h}ч {m}м</b>."
    review_moder_header = (
        "💬 <b>Новый отзыв</b>\n\n"
        "👤 @{username} | <code>{uid}</code> | ▫️{num}"
    )
    review_moder_no_username = "(без username)"

    # ── Group join ───────────────────────────────────────────────
    group_joined        = "✅ Вы зарегистрированы!\n👥 Участников: {n}"
    group_finished      = "❌ Конкурс уже завершён."

    # ── Notifications ────────────────────────────────────────────
    notify_winner       = (
        "🎉 <b>Поздравляем — вы победили!</b>\n\n"
        "📌 {title}\n💰 Приз: {prize}\n\n"
        "Свяжитесь с администратором для получения приза."
    )
    notify_other        = (
        "🤹🏻 <b>Конкурс завершён</b>\n\n📌 {title}\n\n"
        "🏆 <b>Победители:</b>\n{winners}\n\nСпасибо за участие! 🍀"
    )
