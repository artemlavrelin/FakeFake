from datetime import datetime
from i18n import t


def format_winner(telegram_id: int, username: str | None, index: int) -> str:
    if username:
        return f"{index}. @{username}"
    s = str(telegram_id)
    return f"{index}. {s[:4]}****"


def stats_bar(
    time_str: str, participants: int, winners_count: int,
    prize_text: str, chance_pct: float,
) -> str:
    prize = prize_text[:20] if len(prize_text) > 20 else prize_text
    return f"⏳ {time_str}   👥 {participants}   🏆 {winners_count}   💰 {prize}   📊 {chance_pct:.1f}%"


def calc_chance(winners_count: int, participants: int, is_participant: bool) -> float:
    if not is_participant or participants == 0:
        return 0.0
    return min((winners_count / participants) * 100, 100.0)


def format_personal_stats(stats: dict, user_number: int | None, lang: str) -> str:
    participations = stats["participations"]
    wins           = stats["wins"]
    prize_sum      = stats["prize_sum"]
    last_win: datetime | None = stats["last_win"]

    num_str      = f"▫️{user_number}" if user_number else ""
    last_win_str = last_win.strftime("%d.%m.%Y") if last_win else "—"
    prize_str    = f"${prize_sum:.0f}" if prize_sum > 0 else "—"

    lines = [
        t(lang, "stats_header"),
        f"<b>{num_str}</b>",
        "",
        t(lang, "stats_participations", n=participations),
        t(lang, "stats_wins",           n=wins),
        t(lang, "stats_prize_sum",      s=prize_str),
        t(lang, "stats_last_win",       d=last_win_str),
    ]
    if wins == 0 and participations > 0:
        lines.append(t(lang, "stats_no_wins"))
    elif wins == 1:
        lines.append(t(lang, "stats_won_once"))
    elif wins > 1:
        lines.append(t(lang, "stats_won_many", n=wins))
    return "\n".join(lines)


def format_public_stats(stats: dict, lang: str) -> str:
    prize_str = f"${stats['total_prize_sum']:.0f}" if stats["total_prize_sum"] > 0 else "—"
    return "\n".join([
        t(lang, "public_stats_header"),
        "",
        t(lang, "public_finished",     n=stats["finished_count"]),
        t(lang, "public_participants", n=stats["total_participants"]),
        t(lang, "public_winners",      n=stats["total_winners"]),
        t(lang, "public_prize_sum",    s=prize_str),
    ])


def _fmt_name(row: dict) -> str:
    num = f" ▫️{row['user_number']}" if row.get("user_number") else ""
    if row.get("username"):
        return f"@{row['username']}{num}"
    s = str(row["telegram_id"])
    return f"{s[:4]}****{num}"


def format_top_winners(rows: list[dict], lang: str) -> str:
    if not rows:
        return t(lang, "top_winners_empty")
    medals = ["🥇", "🥈", "🥉"]
    lines  = [t(lang, "top_winners_header"), ""]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(t(lang, "top_wins_row", medal=medal, name=_fmt_name(row), n=row["wins"]))
    return "\n".join(lines)


def format_top_participants(rows: list[dict], lang: str) -> str:
    if not rows:
        return t(lang, "top_parts_empty")
    medals = ["🥇", "🥈", "🥉"]
    lines  = [t(lang, "top_parts_header"), ""]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(t(lang, "top_parts_row", medal=medal, name=_fmt_name(row), n=row["count"]))
    return "\n".join(lines)
