from datetime import datetime


# ─── Winner display ───────────────────────────────────────────────────────────

def format_winner(telegram_id: int, username: str | None, index: int) -> str:
    if username:
        return f"{index}. @{username}"
    s = str(telegram_id)
    return f"{index}. {s[:4]}****"


def format_winner_full(
    telegram_id: int,
    username: str | None,
    user_number: int | None,
    binance_id: str | None,
    stake_id: str | None,
    index: int,
) -> str:
    """Full winner card for bonus draw moderator report."""
    num = f"▫️{user_number}" if user_number else "▫️—"
    name = f"@{username}" if username else f"`{telegram_id}`"
    lines = [
        f"{index}. {name}  {num}",
        f"   🆔 TG ID: `{telegram_id}`",
        f"   💛 Binance: `{binance_id or '—'}`",
        f"   🎰 Stake: `{stake_id or '—'}`",
    ]
    return "\n".join(lines)


# ─── Stats bar ────────────────────────────────────────────────────────────────

def stats_bar(
    time_str: str,
    participants: int,
    winners_count: int,
    prize_text: str,
    chance_pct: float,
) -> str:
    """⏳ 0м   👥 0   🏆 3   💰 10   📊 2.3%"""
    prize = prize_text[:20] if len(prize_text) > 20 else prize_text
    chance = f"{chance_pct:.1f}%"
    return f"⏳ {time_str}   👥 {participants}   🏆 {winners_count}   💰 {prize}   📊 {chance}"


def calc_chance(winners_count: int, participants: int, is_participant: bool) -> float:
    """Return win chance % for the current user."""
    if not is_participant or participants == 0:
        return 0.0
    return min((winners_count / participants) * 100, 100.0)


# ─── Personal stats ───────────────────────────────────────────────────────────

def format_personal_stats(stats: dict, user_number: int | None) -> str:
    participations = stats["participations"]
    wins = stats["wins"]
    prize_sum = stats["prize_sum"]
    last_win: datetime | None = stats["last_win"]

    num_str = f"▫️{user_number}" if user_number else ""
    last_win_str = last_win.strftime("%d.%m.%Y") if last_win else "—"
    prize_str = f"${prize_sum:.0f}" if prize_sum > 0 else "—"

    lines = [
        "👀 <b>МОЯ СТАТИСТИКА</b>",
        f"<b>{num_str}</b>",
        "",
        f"🎲 Участий: <b>{participations}</b>",
        f"🔥 Побед: <b>{wins}</b>",
        f"💵 Сумма выигрышей: <b>{prize_str}</b>",
        f"🍷 Последняя победа: <b>{last_win_str}</b>",
    ]
    if wins == 0 and participations > 0:
        lines.append("\nУдачи в следующий раз! 🍀")
    elif wins == 1:
        lines.append("\nВы побеждали 1× — отличный результат! 🌟")
    elif wins > 1:
        lines.append(f"\nВы побеждали {wins}× — вы везунчик! 🌟")
    return "\n".join(lines)


# ─── Public stats ─────────────────────────────────────────────────────────────

def format_public_stats(stats: dict) -> str:
    prize_str = f"${stats['total_prize_sum']:.0f}" if stats["total_prize_sum"] > 0 else "—"
    return (
        "👥 <b>ОБЩАЯ СТАТИСТИКА</b>\n\n"
        f"🤹🏻 Завершено конкурсов: <b>{stats['finished_count']}</b>\n"
        f"👥 Всего участий: <b>{stats['total_participants']}</b>\n"
        f"🏆 Победителей выбрано: <b>{stats['total_winners']}</b>\n"
        f"💰 Сумма призов: <b>{prize_str}</b>"
    )


# ─── Top lists ────────────────────────────────────────────────────────────────

def _fmt_name(row: dict) -> str:
    num = f" ▫️{row['user_number']}" if row.get("user_number") else ""
    if row.get("username"):
        return f"@{row['username']}{num}"
    s = str(row["telegram_id"])
    return f"{s[:4]}****{num}"


def format_top_winners(rows: list[dict]) -> str:
    if not rows:
        return "🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>\n\nПока нет данных."
    lines = ["🏆 <b>ТОП ПОБЕДИТЕЛЕЙ</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{medal} {_fmt_name(row)} — <b>{row['wins']}</b> побед")
    return "\n".join(lines)


def format_top_participants(rows: list[dict]) -> str:
    if not rows:
        return "👥 <b>ТОП УЧАСТНИКОВ</b>\n\nПока нет данных."
    lines = ["👥 <b>ТОП УЧАСТНИКОВ</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{medal} {_fmt_name(row)} — <b>{row['count']}</b> участий")
    return "\n".join(lines)
