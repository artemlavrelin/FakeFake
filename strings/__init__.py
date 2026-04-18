from strings.ru import RU
from strings.en import EN

LANGUAGES = {"ru": RU, "en": EN}


def t(lang: str, key: str, **kwargs) -> str:
    strings = LANGUAGES.get(lang, RU)
    text = getattr(strings, key, None) or getattr(RU, key, key)
    return text.format(**kwargs) if kwargs else text
