class EN:
    # ── Language picker ──────────────────────────────────────────
    choose_language     = "Выберите язык / Choose language:"

    # ── Main menu ────────────────────────────────────────────────
    menu_text           = "Choose a section:"
    btn_raffle          = "🤹🏻 Raffle"
    btn_report          = "⭐️ Payouts / Reviews"
    btn_my_stats        = "👀 My statistics"
    btn_public_stats    = "👥 General statistics"
    btn_atm             = "🧲 ATM"
    btn_reviews         = "💬 Reviews"
    btn_back            = "⬅️ Back"
    btn_cancel          = "⬅️ Cancel"
    btn_to_menu         = "⬅️ Menu"

    # ── Raffle ───────────────────────────────────────────────────
    raffle_no_contest   = "🤹🏻 <b>RAFFLE</b>\n\nNo active contest right now.\nStay tuned!"
    raffle_header       = "🤹🏻 <b>#{id} CURRENT RAFFLE</b>\n\n📌 {title}\n\n{bar}\n\n{status}"
    raffle_participating = "👉 You are participating, good luck! 🤞🏻"
    raffle_not_participating = "❌ You are not participating"
    raffle_banned       = "❌ You are banned"
    btn_participate     = "🔥 Join"
    raffle_confirm_text = "📌 {title}\n\n{bar}\n\nJoin the raffle?"
    btn_confirm         = "✅ Confirm"
    raffle_joined       = "✅ <b>You are registered!</b>\n\n📌 {title}\n\n{bar}\n\n👉 Wait for results. Good luck! 🤞🏻"
    raffle_already      = "👉 You are already participating!"
    raffle_banned_alert = "🚫 You are banned."
    raffle_finished     = "Contest is over."

    # ── Report ───────────────────────────────────────────────────
    report_text         = (
        "⭐️ <b>PAYOUTS / REVIEWS</b>\n\n"
        "<b>{title}</b> — transparent system reporting:\n\n"
        "• ✅ Payment confirmations\n"
        "• 🏆 Raffle results\n"
        "• 💬 User reviews\n"
        "• 📊 Winner statistics\n"
        "• 🔍 Transparency proof\n\n"
        "Open the channel to verify:"
    )
    btn_go              = "➡️ Go"

    # ── My stats ─────────────────────────────────────────────────
    stats_header        = "👀 <b>MY STATISTICS</b>"
    stats_participations = "🎲 Participations: <b>{n}</b>"
    stats_wins          = "🔥 Wins: <b>{n}</b>"
    stats_prize_sum     = "💵 Total prizes: <b>{s}</b>"
    stats_last_win      = "🍷 Last win: <b>{d}</b>"
    stats_no_wins       = "\nGood luck next time! 🍀"
    stats_won_once      = "\nYou've won once — great result! 🌟"
    stats_won_many      = "\nYou've won {n}× — you're lucky! 🌟"

    # ── Public stats ─────────────────────────────────────────────
    public_stats_header = "👥 <b>GENERAL STATISTICS</b>"
    public_finished     = "🤹🏻 Raffles completed: <b>{n}</b>"
    public_participants = "👥 Total entries: <b>{n}</b>"
    public_winners      = "🏆 Winners selected: <b>{n}</b>"
    public_prize_sum    = "💰 Total prizes: <b>{s}</b>"
    btn_top_winners     = "🏆 Top winners"
    btn_top_participants = "👥 Top participants"
    top_winners_header  = "🏆 <b>TOP WINNERS</b>"
    top_winners_empty   = "🏆 <b>TOP WINNERS</b>\n\nNo data yet."
    top_parts_header    = "👥 <b>TOP PARTICIPANTS</b>"
    top_parts_empty     = "👥 <b>TOP PARTICIPANTS</b>\n\nNo data yet."
    top_wins_row        = "{medal} {name} — <b>{n}</b> wins"
    top_parts_row       = "{medal} {name} — <b>{n}</b> entries"

    # ── ATM ──────────────────────────────────────────────────────
    atm_header          = "🧲 <b>ATM «MAGNET»</b>"
    btn_stake           = "🎰 Stake"
    btn_binance         = "🟡 Binance"

    # ── Stake section ────────────────────────────────────────────
    stake_header        = "🎰 <b>STAKE</b>\n\n{num}\n\n🎰 Stake username: {val}"
    stake_no_data       = "—"
    btn_edit            = "✏️ Edit data"
    btn_delete          = "🗑 Delete data"
    btn_reg_stake       = "🔗 Reg Stake"
    stake_enter         = "🎰 Enter your <b>Stake username</b>:"
    stake_saved         = "✅ Stake username saved: <code>{val}</code>"
    stake_deleted       = "🗑 Stake username deleted."
    stake_delete_confirm = "Delete Stake username?"
    btn_yes_delete      = "✅ Yes, delete"

    # ── Binance section ──────────────────────────────────────────
    binance_header      = "🟡 <b>BINANCE</b>\n\n{num}\n\n💛 Binance ID: {val}"
    btn_reg_binance     = "🔗 Reg Binance"
    binance_enter       = "🟡 Enter your <b>Binance ID</b>:"
    binance_saved       = "✅ Binance ID saved: <code>{val}</code>"
    binance_deleted     = "🗑 Binance ID deleted."
    binance_delete_confirm = "Delete Binance ID?"

    # ── Reviews ──────────────────────────────────────────────────
    reviews_menu        = "💬 <b>REVIEWS</b>\n\nShare your experience — it helps the community."
    btn_leave_review    = "✍️ Leave a review"
    review_prompt       = (
        "✍️ <b>Write your review</b>\n\n"
        "You can send:\n"
        "• text\n• photo\n• video\n\n"
        "One review every 12 hours."
    )
    review_sent         = "✅ Thank you! Your review has been sent for moderation."
    review_cooldown     = "⏳ You already submitted a review. Next one available in <b>{h}h {m}m</b>."
    review_moder_header = (
        "💬 <b>New review</b>\n\n"
        "👤 @{username} | <code>{uid}</code> | ▫️{num}"
    )
    review_moder_no_username = "(no username)"

    # ── Group join ───────────────────────────────────────────────
    group_joined        = "✅ Registered!\n👥 Participants: {n}"
    group_finished      = "❌ Contest is already over."

    # ── Notifications ────────────────────────────────────────────
    notify_winner       = (
        "🎉 <b>Congratulations — you won!</b>\n\n"
        "📌 {title}\n💰 Prize: {prize}\n\n"
        "Contact the admin to claim your prize."
    )
    notify_other        = (
        "🤹🏻 <b>Raffle finished</b>\n\n📌 {title}\n\n"
        "🏆 <b>Winners:</b>\n{winners}\n\nThanks for participating! 🍀"
    )
