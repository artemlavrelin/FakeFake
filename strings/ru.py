class RU:
    choose_language      = "Выберите язык / Choose language:"
    menu_text            = "Выбери раздел:"
    btn_raffle           = "🤹🏻 Розыгрыш"
    btn_report           = "⭐️ Выплаты / Отзывы"
    btn_stake            = "🤞🏻 Stake"
    btn_binance          = "🟡 Binance"
    btn_my_stats         = "👀 Моя статистика"
    btn_public_stats     = "👥 Общая статистика"
    btn_loot             = "📫 Получить приз"
    btn_back             = "⬅️ Назад"
    btn_cancel           = "⬅️ Отмена"
    btn_to_menu          = "⬅️ В меню"
    btn_go               = "➡️ Перейти"

    # Raffle
    raffle_no_contest        = "🤹🏻 <b>РОЗЫГРЫШ</b>\n\nСейчас нет активного конкурса.\nСледите за обновлениями!"
    raffle_header            = "🤹🏻 <b>#{id} ТЕКУЩИЙ КОНКУРС</b>\n\n📌 {title}\n\n{bar}\n\n{status}"
    raffle_participating     = "👉 Вы участвуете в конкурсе, удачи 🤞🏻"
    raffle_not_participating = "❌ Вы не участвуете"
    raffle_banned            = "❌ Вы заблокированы"
    btn_participate          = "🔥 Участвовать"
    raffle_confirm_text      = "📌 {title}\n\n{bar}\n\nПринять участие?"
    btn_confirm              = "✅ Подтвердить"
    raffle_joined            = "✅ <b>Вы зарегистрированы!</b>\n\n📌 {title}\n\n{bar}\n\n👉 Ожидайте результатов. Удачи! 🤞🏻"
    raffle_already           = "👉 Вы уже участвуете!"
    raffle_banned_alert      = "🚫 Вы заблокированы."
    raffle_finished          = "Конкурс завершён."
    group_joined             = "✅ Вы зарегистрированы!\n👥 Участников: {n}"
    group_finished           = "❌ Конкурс уже завершён."

    # Report / Reviews (merged section)
    report_text = (
        "⭐️ <b>ВЫПЛАТЫ / ОТЗЫВЫ</b>\n\n"
        "<b>{title}</b> — прозрачная отчётность системы:\n\n"
        "• ✅ Подтверждения выплат\n"
        "• 🏆 Результаты розыгрышей\n"
        "• 💬 Отзывы участников\n"
        "• 📊 Статистика победителей\n"
        "• 🔍 Данные, подтверждающие прозрачность работы\n\n"
        "Перейди в канал или оставь свой отзыв:"
    )
    btn_leave_review    = "✍️ Оставить отзыв"
    review_prompt       = (
        "✍️ <b>Напишите ваш отзыв</b>\n\n"
        "Вы можете отправить:\n• текст\n• фото\n• видео\n\n"
        "Один отзыв каждые 12 часов."
    )
    review_sent         = "✅ Спасибо! Ваш отзыв отправлен."
    review_cooldown     = "⏳ Следующий отзыв через <b>{h}ч {m}м</b>."
    review_moder_header = "💬 <b>Новый отзыв</b>\n\n👤 @{username} | <code>{uid}</code> | ▫️{num}"
    review_moder_no_username = "(без username)"

    # My stats
    stats_header        = "👀 <b>МОЯ СТАТИСТИКА</b>"
    stats_participations = "🎲 Участий: <b>{n}</b>"
    stats_wins          = "🔥 Побед: <b>{n}</b>"
    stats_prize_sum     = "💵 Сумма выигрышей: <b>{s}</b>"
    stats_last_win      = "🍷 Последняя победа: <b>{d}</b>"
    stats_no_wins       = "\nУдачи в следующий раз! 🍀"
    stats_won_once      = "\nВы побеждали 1× — отличный результат! 🌟"
    stats_won_many      = "\nВы побеждали {n}× — вы везунчик! 🌟"

    # Public stats
    public_stats_header  = "👥 <b>ОБЩАЯ СТАТИСТИКА</b>"
    public_finished      = "🤹🏻 Завершено конкурсов: <b>{n}</b>"
    public_participants  = "👥 Всего участий: <b>{n}</b>"
    public_winners       = "🏆 Победителей выбрано: <b>{n}</b>"
    public_prize_sum     = "💰 Сумма призов: <b>{s}</b>"
    btn_top_winners      = "🏆 Топ победителей"
    btn_top_participants = "👥 Топ участников"
    top_winners_header   = "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>"
    top_winners_empty    = "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>\n\nПока нет данных."
    top_parts_header     = "👥 <b>ТОП УЧАСТНИКОВ</b>"
    top_parts_empty      = "👥 <b>ТОП УЧАСТНИКОВ</b>\n\nПока нет данных."
    top_wins_row         = "{medal} {name} — <b>{n}</b> побед"
    top_parts_row        = "{medal} {name} — <b>{n}</b> участий"

    # Stake
    stake_header         = "🤞🏻 <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: {val}"
    stake_no_data        = "—"
    btn_edit             = "✏️ Изменить"
    btn_delete           = "🗑 Удалить"
    btn_reg_stake        = "🔗 Reg Stake"
    stake_enter          = "🤞🏻 Введите ваш <b>Stake username</b>:"
    stake_saved          = "✅ Stake username сохранён: <code>{val}</code>"
    stake_deleted        = "🗑 Stake username удалён."
    stake_delete_confirm = "Удалить Stake username?"
    btn_yes_delete       = "✅ Да, удалить"

    # Binance
    binance_header         = "🟡 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: {val}"
    btn_reg_binance        = "🔗 Reg Binance"
    binance_enter          = "🟡 Введите ваш <b>Binance ID</b>:"
    binance_saved          = "✅ Binance ID сохранён: <code>{val}</code>"
    binance_deleted        = "🗑 Binance ID удалён."
    binance_delete_confirm = "Удалить Binance ID?"

    # Loot
    loot_no_data = (
        "📫 <b>ПОЛУЧИТЬ ПРИЗ</b>\n\n"
        "Для получения приза необходимо зарегистрировать <b>Binance</b> и <b>Stake</b> и пройти верификацию.\n\n"
        "После этого вы получите случайную награду от $0.10 до $10 💰"
    )
    loot_go_register    = "🔗 Зарегистрироваться"
    loot_banned_msg     = "👉 Вы уже получили свой приз"
    loot_cooldown       = "⏳ Следующий приз через <b>{h}ч {m}м</b>."
    loot_start_text     = (
        "📫 <b>ПОЛУЧИТЬ ПРИЗ</b>\n\n"
        "💛 Binance ID: <code>{binance}</code>\n"
        "🤞🏻 Stake: <code>{stake}</code>\n\n"
        "Нажмите кнопку, чтобы начать:"
    )
    btn_loot_start      = "🎁 Loot / Получить"
    loot_send_binance   = "📸 Отправьте <b>скриншот вашего Binance ID</b>:"
    loot_send_stake     = "📸 Отправьте <b>скриншот вашего Stake username</b>:"
    loot_ready          = "✅ Скриншоты получены. Нажмите кнопку для розыгрыша:"
    btn_loot_roll       = "🎁 Loot"
    loot_result         = "🎉 <b>Поздравляем!</b>\n\nВы выиграли: <b>${prize}</b>\n\nПосле проверки сумма будет отправлена на ваш баланс Stake или Binance."
    loot_moder_header   = (
        "📫 <b>LOOT ЗАЯВКА</b>\n\n"
        "👤 @{username} | <code>{uid}</code> | ▫️{num}\n"
        "💰 Выигрыш: <b>${prize}</b>\n"
        "💛 Binance: <code>{binance}</code>\n"
        "🤞🏻 Stake: <code>{stake}</code>"
    )
    loot_photo_binance  = "📸 Скриншот Binance:"
    loot_photo_stake    = "📸 Скриншот Stake:"
    loot_no_photo       = "(скриншот не предоставлен)"

    # Notifications
    notify_winner = (
        "🎉 <b>Поздравляем — вы победили!</b>\n\n"
        "📌 {title}\n💰 Приз: {prize}\n\n"
        "Свяжитесь с администратором для получения приза."
    )
    notify_other  = (
        "🤹🏻 <b>Конкурс завершён</b>\n\n📌 {title}\n\n"
        "🏆 <b>Победители:</b>\n{winners}\n\nСпасибо за участие! 🍀"
    )

    # Payment change cooldown
    payment_cooldown_stake   = "⏳ Stake username можно менять раз в 7 дней. Осталось: <b>{d}д {h}ч</b>."
    payment_cooldown_binance = "⏳ Binance ID можно менять раз в 7 дней. Осталось: <b>{d}д {h}ч</b>."

    # Mod notification on payment change
    payment_changed_moder = (
        "✏️ <b>Изменение платёжных данных</b>\n\n"
        "👤 @{username} | <code>{uid}</code> | ▫️{num}\n"
        "🔧 Поле: <b>{field}</b>\n"
        "📝 Новое значение: <code>{value}</code>"
    )
