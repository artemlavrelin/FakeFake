from datetime import datetime


def time_ago(created_at: datetime) -> str:
    """Return compact elapsed time string: '5м', '17ч', '3д'."""
    delta = datetime.utcnow() - created_at
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "0м"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}м"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}ч"
    return f"{hours // 24}д"
