"""
homework.py.

Бот для отправки сообщений в телеграм изменения статуса домашних работ
Яндекс практикум
"""
import logging
import os
import time

from http import HTTPStatus
from sys import stdout

import requests
import telegram

from dotenv import load_dotenv

import constants as const
import exceptions as exp

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщений в телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            f'{const.LOG_MESSAGES["succesfully_send_message"]}: {message}'
        )
    except Exception as error:
        raise exp.Telegram_Exception(
            f'{const.LOG_MESSAGES["error_send_message"]}: {error}'
        )


def get_api_answer(current_timestamp=int(time.time())) -> dict:
    """
    Выполняет запрос к API на получение новых статусом ДР.

    Полученный json-массив преобразуется в словарь
    На входе временная метка
    """
    params = {'from_date': current_timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    answer_code = homework_statuses.status_code
    if answer_code != HTTPStatus.OK:
        message = f'{const.LOG_MESSAGES["wrong_status_code"]}: {answer_code}'
        raise exp.API_Ya_Practicum_Exception(message)

    try:
        return dict(homework_statuses.json())
    except Exception:
        raise ValueError(
            const.LOG_MESSAGES['error_tranform_response_to_diсt']
        )


def check_response(response: dict) -> list:
    """
    Выполняет проверку ответа API на соотвествие.

    Возвращает список домашних работ с корректными и
    изменёнными статусами
    """
    if (not(type(response) is dict)
       or not(type(response['homeworks']) is list)):
        message = f'{const.LOG_MESSAGES["wrong_type"]}: {response}'
        raise TypeError(message)

    if 'homeworks' not in response:
        message = f'{const.LOG_MESSAGES["missed_key"]} homeworks: {response}'
        raise TypeError()

    if len(response['homeworks']) < 1:
        message = f'{const.LOG_MESSAGES["empty_list"]}: {response}'
        logging.debug(message)

    return response['homeworks']


def parse_status(homework: list) -> str:
    """
    Получение информации о статусе домашней работы.

    Извлекает информацию по ключам homework_name и status из списка
    Возвращает строку с информацией о новом статусе
    """
    for key in const.HOMEWORK_KEYS:
        if key not in homework:
            message = (
                f'{const.LOG_MESSAGES["missed_key"]} {key}: {homework}'
            )
            raise KeyError(message)

    if homework['status'] not in const.HOMEWORK_STATUSES.keys():
        message = (
            f'{const.LOG_MESSAGES["wrong_status"]}: {homework["status"]}'
        )
        raise ValueError(message)

    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = const.HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка наличия переменных окружения. return true or false."""
    check_env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    result = True
    for var, val in check_env_vars.items():
        if val is None:
            result = False
            logging.critical(f'{const.LOG_MESSAGES["missed_env"]}: {var}')

    return result


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = const.LOG_MESSAGES['missed_env']
        raise EnvironmentError(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    message = const.LOG_MESSAGES['app_start']
    logging.info(message)
    send_message(bot, message)

    last_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            for homework in check_response(response):
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except EnvironmentError as error:
            logging.info(error)
            return

        except KeyboardInterrupt:
            message = const.LOG_MESSAGES['app_stop']
            logging.info(message)
            send_message(bot, message)
            return

        except exp.Telegram_Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)

        except (exp.API_Ya_Practicum_Exception_Endpoint,
                ValueError,
                TypeError,
                Exception) as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if last_message != message:
                send_message(bot, message)
                last_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=stdout,
        level=logging.DEBUG,
    )

    main()
