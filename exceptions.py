"""Исключения."""


class MissingTokens(Exception):
    """Отсутствуют переменные окружения."""


class WrongStatusCode(Exception):
    """HTTP код не 200."""
