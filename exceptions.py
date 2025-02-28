"""Исключения."""


class MissingTokens(Exception):
    """Отсутствуют переменные окружения."""

    pass


class UnavailablePage(Exception):
    """Эндпойнт Яндекс Практикум недоступен."""

    pass
