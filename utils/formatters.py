"""Formatting helpers used across handlers."""


def format_winner(telegram_id: int, username: str | None, index: int) -> str:
    """
    Return a human-readable winner line.
    If the user has a username  → show @username
    Otherwise                  → show partially masked ID: 1234****
    """
    if username:
        return f"{index}. @{username}"
    masked = _mask_id(telegram_id)
    return f"{index}. {masked}"


def _mask_id(telegram_id: int) -> str:
    """Show first 4 digits, mask the rest with ****."""
    s = str(telegram_id)
    visible = s[:4] if len(s) >= 4 else s
    return f"{visible}****"


def format_stats(participations: int, wins: int) -> str:
    win_rate = (wins / participations * 100) if participations > 0 else 0
    lines = [
        "📊 <b>Ваша статистика</b>\n",
        f"🎯 Участий в конкурсах: <b>{participations}</b>",
        f"🏆 Побед: <b>{wins}</b>",
        f"📈 Процент побед: <b>{win_rate:.1f}%</b>",
    ]
    if wins == 0:
        lines.append("\nУдачи в следующий раз! 🍀")
    elif wins == 1:
        lines.append("\nВы уже выигрывали — отличный результат! 🎉")
    else:
        lines.append(f"\nВы выиграли {wins} раза — вы везунчик! 🌟")
    return "\n".join(lines)
