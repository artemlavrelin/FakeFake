class EN:
    choose_language      = "Выберите язык / Choose language:"
    menu_text            = "Choose a section:"
    btn_raffle           = "🤹🏻 Raffle"
    btn_report           = "⭐️ Payouts / Reviews"
    btn_stake            = "🤞🏻 Stake"
    btn_binance          = "🟡 Binance"
    btn_my_stats         = "👀 My statistics"
    btn_public_stats     = "👥 General statistics"
    btn_loot             = "📫 Claim prize"
    btn_back             = "⬅️ Back"
    btn_cancel           = "⬅️ Cancel"
    btn_to_menu          = "⬅️ Menu"
    btn_go               = "➡️ Go"

    raffle_no_contest        = "🤹🏻 <b>RAFFLE</b>\n\nNo active contest right now.\nStay tuned!"
    raffle_header            = "🤹🏻 <b>#{id} CURRENT RAFFLE</b>\n\n📌 {title}\n\n{bar}\n\n{status}"
    raffle_participating     = "👉 You are participating, good luck! 🤞🏻"
    raffle_not_participating = "❌ You are not participating"
    raffle_banned            = "❌ You are banned"
    btn_participate          = "🔥 Join"
    raffle_confirm_text      = "📌 {title}\n\n{bar}\n\nJoin the raffle?"
    btn_confirm              = "✅ Confirm"
    raffle_joined            = "✅ <b>You are registered!</b>\n\n📌 {title}\n\n{bar}\n\n👉 Wait for results. Good luck! 🤞🏻"
    raffle_already           = "👉 You are already participating!"
    raffle_banned_alert      = "🚫 You are banned."
    raffle_finished          = "Contest is over."
    group_joined             = "✅ Registered!\n👥 Participants: {n}"
    group_finished           = "❌ Contest is already over."

    report_text = (
        "⭐️ <b>PAYOUTS / REVIEWS</b>\n\n"
        "<b>{title}</b> — transparent system reporting:\n\n"
        "• ✅ Payment confirmations\n"
        "• 🏆 Raffle results\n"
        "• 💬 User reviews\n"
        "• 📊 Winner statistics\n"
        "• 🔍 Transparency proof\n\n"
        "Open the channel or leave a review:"
    )
    btn_leave_review    = "✍️ Leave a review"
    review_prompt       = (
        "✍️ <b>Write your review</b>\n\n"
        "You can send:\n• text\n• photo\n• video\n\n"
        "One review every 12 hours."
    )
    review_sent         = "✅ Thank you! Your review has been sent."
    review_cooldown     = "⏳ Next review available in <b>{h}h {m}m</b>."
    review_moder_header = "💬 <b>New review</b>\n\n👤 @{username} | <code>{uid}</code> | ▫️{num}"
    review_moder_no_username = "(no username)"

    stats_header         = "👀 <b>MY STATISTICS</b>"
    stats_participations = "🎲 Participations: <b>{n}</b>"
    stats_wins           = "🔥 Wins: <b>{n}</b>"
    stats_prize_sum      = "💵 Total prizes: <b>{s}</b>"
    stats_last_win       = "🍷 Last win: <b>{d}</b>"
    stats_no_wins        = "\nGood luck next time! 🍀"
    stats_won_once       = "\nYou've won once — great result! 🌟"
    stats_won_many       = "\nYou've won {n}× — you're lucky! 🌟"

    public_stats_header  = "👥 <b>GENERAL STATISTICS</b>"
    public_finished      = "🤹🏻 Raffles completed: <b>{n}</b>"
    public_participants  = "👥 Total entries: <b>{n}</b>"
    public_winners       = "🏆 Winners selected: <b>{n}</b>"
    public_prize_sum     = "💰 Total prizes: <b>{s}</b>"
    btn_top_winners      = "🏆 Top winners"
    btn_top_participants = "👥 Top participants"
    top_winners_header   = "🏆 <b>TOP WINNERS</b>"
    top_winners_empty    = "🏆 <b>TOP WINNERS</b>\n\nNo data yet."
    top_parts_header     = "👥 <b>TOP PARTICIPANTS</b>"
    top_parts_empty      = "👥 <b>TOP PARTICIPANTS</b>\n\nNo data yet."
    top_wins_row         = "{medal} {name} — <b>{n}</b> wins"
    top_parts_row        = "{medal} {name} — <b>{n}</b> entries"

    stake_header         = "🤞🏻 <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: {val}"
    stake_no_data        = "—"
    btn_edit             = "✏️ Edit"
    btn_delete           = "🗑 Delete"
    btn_reg_stake        = "🔗 Reg Stake"
    stake_enter          = "🤞🏻 Enter your <b>Stake username</b>:"
    stake_saved          = "✅ Stake username saved: <code>{val}</code>"
    stake_deleted        = "🗑 Stake username deleted."
    stake_delete_confirm = "Delete Stake username?"
    btn_yes_delete       = "✅ Yes, delete"

    binance_header         = "🟡 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: {val}"
    btn_reg_binance        = "🔗 Reg Binance"
    binance_enter          = "🟡 Enter your <b>Binance ID</b>:"
    binance_saved          = "✅ Binance ID saved: <code>{val}</code>"
    binance_deleted        = "🗑 Binance ID deleted."
    binance_delete_confirm = "Delete Binance ID?"

    loot_no_data = (
        "📫 <b>CLAIM PRIZE</b>\n\n"
        "To claim a prize you need to register <b>Binance</b> and <b>Stake</b> and get verified.\n\n"
        "You will then receive a random reward from $0.10 to $10 💰"
    )
    loot_go_register    = "🔗 Register"
    loot_banned_msg     = "👉 You have already claimed your prize"
    loot_cooldown       = "⏳ Next prize available in <b>{h}h {m}m</b>."
    loot_start_text     = (
        "📫 <b>CLAIM PRIZE</b>\n\n"
        "💛 Binance ID: <code>{binance}</code>\n"
        "🤞🏻 Stake: <code>{stake}</code>\n\n"
        "Press the button to start:"
    )
    btn_loot_start      = "🎁 Loot / Claim"
    loot_send_binance   = "📸 Send a <b>screenshot of your Binance ID</b>:"
    loot_send_stake     = "📸 Send a <b>screenshot of your Stake username</b>:"
    loot_ready          = "✅ Screenshots received. Press the button to roll:"
    btn_loot_roll       = "🎁 Loot"
    loot_result         = "🎉 <b>Congratulations!</b>\n\nYou won: <b>${prize}</b>\n\nAfter verification the amount will be sent to your Stake or Binance balance."
    loot_moder_header   = (
        "📫 <b>LOOT REQUEST</b>\n\n"
        "👤 @{username} | <code>{uid}</code> | ▫️{num}\n"
        "💰 Prize: <b>${prize}</b>\n"
        "💛 Binance: <code>{binance}</code>\n"
        "🤞🏻 Stake: <code>{stake}</code>"
    )
    loot_photo_binance  = "📸 Binance screenshot:"
    loot_photo_stake    = "📸 Stake screenshot:"
    loot_no_photo       = "(screenshot not provided)"

    notify_winner = (
        "🎉 <b>Congratulations — you won!</b>\n\n"
        "📌 {title}\n💰 Prize: {prize}\n\n"
        "Contact the admin to claim your prize."
    )
    notify_other = (
        "🤹🏻 <b>Raffle finished</b>\n\n📌 {title}\n\n"
        "🏆 <b>Winners:</b>\n{winners}\n\nThanks for participating! 🍀"
    )

    # Payment change cooldown
    payment_cooldown_stake   = "⏳ Stake username can only be changed once every 7 days. Time left: <b>{d}d {h}h</b>."
    payment_cooldown_binance = "⏳ Binance ID can only be changed once every 7 days. Time left: <b>{d}d {h}h</b>."

    # Mod notification on payment change
    payment_changed_moder = (
        "✏️ <b>Payment data changed</b>\n\n"
        "👤 @{username} | <code>{uid}</code> | ▫️{num}\n"
        "🔧 Field: <b>{field}</b>\n"
        "📝 New value: <code>{value}</code>"
    )
