from datetime import datetime


# ─── Winner display ───────────────────────────────────────────────────────────

def format_winner(telegram_id: int, username: str | None, index: int) -> str:
    if username:
        return f"{index}. @{username}"
    s = str(telegram_id)
    return f"{index}. {s[:4]}****"


# ─── Stats bar ────────────────────────────────────────────────────────────────

def stats_bar(time_str: str, participants: int, winners_count: int, prize_text: str) -> str:
    """⏳ 17ч   👥 18   🏆 2   💰 10$"""
    prize = prize_text[:20] if len(prize_text) > 20 else prize_text
    return f"⏳ {time_str}   👥 {participants}   🏆 {winners_count}   💰 {prize}"


# ─── Personal stats ───────────────────────────────────────────────────────────

def format_personal_stats(stats: dict) -> str:
    participations = stats["participations"]
    wins = stats["wins"]
    prize_sum = stats["prize_sum"]
    last_win: datetime | None = stats["last_win"]

    last_win_str = last_win.strftime("%d.%m.%Y") if last_win else "—"
    prize_str = f"${prize_sum:.0f}" if prize_sum > 0 else "—"

    lines = [
        "📱 <b>МОЯ СТАТИСТИКА</b>\n",
        f"🎯 Участий: <b>{participations}</b>",
        f"🏆 Побед: <b>{wins}</b>",
        f"💰 Сумма выигрышей: <b>{prize_str}</b>",
        f"📅 Последняя победа: <b>{last_win_str}</b>",
    ]
    if wins == 0 and participations > 0:
        lines.append("\nУдачи в следующий раз! 🍀")
    elif wins > 0:
        lines.append(f"\nВы побеждали {wins}×  — отличный результат! 🌟")
    return "\n".join(lines)


# ─── Public stats ─────────────────────────────────────────────────────────────

def format_public_stats(stats: dict) -> str:
    prize_str = f"${stats['total_prize_sum']:.0f}" if stats["total_prize_sum"] > 0 else "—"
    return (
        "🌍 <b>ОБЩАЯ СТАТИСТИКА</b>\n\n"
        f"⚡️ Завершено конкурсов: <b>{stats['finished_count']}</b>\n"
        f"👥 Всего участий: <b>{stats['total_participants']}</b>\n"
        f"🏆 Победителей выбрано: <b>{stats['total_winners']}</b>\n"
        f"💰 Сумма призов: <b>{prize_str}</b>"
    )


# ─── Top lists ────────────────────────────────────────────────────────────────

def format_top_winners(rows: list[dict]) -> str:
    if not rows:
        return "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>\n\nПока нет данных."
    lines = ["🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = f"@{row['username']}" if row["username"] else f"{str(row['telegram_id'])[:4]}****"
        lines.append(f"{medal} {name} — <b>{row['wins']}</b> побед")
    return "\n".join(lines)


def format_top_participants(rows: list[dict]) -> str:
    if not rows:
        return "👥 <b>ТОП УЧАСТНИКОВ</b>\n\nПока нет данных."
    lines = ["👥 <b>ТОП УЧАСТНИКОВ</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = f"@{row['username']}" if row["username"] else f"{str(row['telegram_id'])[:4]}****"
        lines.append(f"{medal} {name} — <b>{row['count']}</b> участий")
    return "\n".join(lines)
