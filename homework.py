"""Бот-помощник."""
from http import HTTPStatus
import json
import logging
import sys
import time

import requests
from telebot import TeleBot

from config import (
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    ENDPOINT,
    HEADERS,
    RETRY_PERIOD
)
from exceptions import (
    MissingTokens,
    # SendMessageError,
    UnavailablePage,
    # UnknownFail,
    # StatusError
)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяем наличие переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.debug('Переменные окружения успешно получены.')
        return True
    logger.critical('Критическая ошибка! Отсутствуют переменные окружения! '
                    'Программа принудиттельно остановлена')
    return False


def get_api_answer(timestamp):
    """Получаем ответ от API Яндекс Практикум."""
    params = {'from_date': timestamp}
    try:
        request_result = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except UnavailablePage:
        raise UnavailablePage
    except Exception:
        logger.error('Ошибка! Сбой при запросе к эндпойнту ЯП.')
    if request_result.status_code != HTTPStatus.OK:
        raise UnavailablePage
    try:
        return request_result.json()
    except json.decoder.JSONDecodeError as e:
        logger.error(f'Недопустимый формат ответа API. {e}')


def check_response(response):
    """Проверяем ответ от API."""
    if not isinstance(response, dict):
        logger.error('Ошибка! Получен неверный формат данных в ответе API.')
        raise TypeError
    if response.get('homeworks') is None:
        logger.error('Ошибка! Отсутствуют ожидаемые ключи в ответе API.')
        raise KeyError
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logger.error('Ошибка! Получен неверный формат данных в ответе API.')
        raise TypeError
    return homeworks[0]


def parse_status(homework):
    """Проверяем статус домашнего задания."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except Exception:
        logger.error('Ошибка! В ответе API нет нужных ключей.')
        raise KeyError
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except Exception:
        logger.error('Ошибка! Получен недопустимый статус домашнней работы.')
        raise KeyError
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправляем сообщение."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
            )
        logger.debug('Сообщение успешно отправлено')
    except Exception:
        logger.error('Ошибка! Не удалось отправить сообщение.')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise MissingTokens
    bot = TeleBot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except Exception:
            logger.error('Ошибка! Эндпойнт ЯП не доступен. '
                         'Отправляю в Телеграм сообщение об ошибке')
        try:
            response = check_response(response)
            if response:
                status_message = parse_status(response)
                send_message(bot, status_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
