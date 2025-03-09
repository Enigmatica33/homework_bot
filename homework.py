"""Бот-помощник."""
import logging
import sys
import time
from http import HTTPStatus

import requests
from telebot import TeleBot, telebot

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
    WrongStatusCode
)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
PRACTICUM_TOKEN = PRACTICUM_TOKEN

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяем наличие переменных окружения."""
    logger.info('Проверяем наличие переменных окружения')
    token_list = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_tokens = [token for token in token_list if not globals()[token]]
    if missing_tokens:
        message_error = 'Отсутствуют переменные окружения: '
        logger.critical(f'{message_error}{",".join(missing_tokens)}')
        raise MissingTokens(f'{message_error}{",".join(missing_tokens)}')


def get_api_answer(timestamp):
    """Получаем ответ от API Яндекс Практикум."""
    params = {'from_date': timestamp}
    logger.info(f'Отправляем запрос к API ЯП, эндпойнт: {ENDPOINT}, '
                f'параметры: {params}')
    try:
        request_result = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException as e:
        raise ConnectionError(f'Эндпойнт ЯП недоступен. {e}')
    if request_result.status_code != HTTPStatus.OK:
        raise WrongStatusCode(f'Ошибка доступа к эндпойнту: {ENDPOINT}')
    logger.info('Ответ от эндпойнта получен.')
    return request_result.json()


def check_response(response):
    """Проверяем ответ API."""
    key = 'homeworks'
    logger.info('Проверяем валидность ответа от API.')
    if not isinstance(response, dict):
        raise TypeError('Неверный формат данных в ответе API. '
                        f'Получен: {type(response)}')
    if key not in response:
        raise KeyError('В ответе API отсутствует ключ.')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Неверный формат данных в ответе API. '
                        f'Получен: {type(homeworks)}')
    logger.info('Ответ API соответствуют ожидаемому.')
    return homeworks


def parse_status(homework):
    """Проверяем статус домашнего задания."""
    logger.info('Проверяем статус домашнего задания.')
    expected_keys = [homework.get('homework_name'), homework.get('status')]
    missing_keys = [key for key in expected_keys if not key]
    if missing_keys:
        raise KeyError('Ошибка! В ответе API нет необходимых ключей.')
    homework_name, homework_status = expected_keys
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Ошибка! Недокументированный статус домашней работы. '
                         f'{homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    logger.info('Проверка завершена.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправляем сообщение."""
    logger.info('Отправляем сообщение.')
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.debug('Сообщение успешно отправлено')


def main():
    """Основная логика работы бота."""
    last_result = None
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.debug('Ответ API пуст: нет новых домашних работ.')
                continue
            status_message = parse_status(homeworks[0])
            if last_result != status_message:
                logger.info('Получен новый статус домашнего задания!')
                send_message(bot, status_message)
                last_result = status_message
            current_timestamp = response.get('current_date', current_timestamp)
        except (
            telebot.apihelper.ApiException,
            requests.exceptions.RequestException
        ):
            logger.exception('Запрос к Telegram API был неудачным.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(f'{message} {error}')
            last_result = message
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
