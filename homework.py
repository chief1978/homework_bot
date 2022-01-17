import logging
import os
import time

from http import HTTPStatus
from sys import stdout

import requests
import telegram

from dotenv import load_dotenv

import exceptions as exp

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

LOG_MESSAGES = {
    'missed_env': 'Отсутствуют переменные окружения',
}


def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp=int(time.time())) -> dict:
    # current_timestamp = 0
    params = {'from_date': current_timestamp}
    # params = {}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    answer_code = homework_statuses.status_code
    if answer_code != HTTPStatus.OK:
        message = f'API Yandex практикума вернул код {answer_code} <> 200 OK.'
        raise exp.API_Ya_Practicum_Exception(message)

    try:
        return dict(homework_statuses.json())
    except Exception:
        raise ValueError(
            'Не удалось преобразовать ответ API к нужному типу данных'
        )


def check_response(response) -> dict:

    if not(type(response) is dict):
        message = f'API вернул ответ некорректного типа: {response}'
        logging.error(message)
        raise TypeError(message)

    if 'homeworks' not in response:
        message = f'В ответе отсуствует ключ homeworks: {response}'
        logging.error(message)
        raise TypeError()

    if not(type(response['homeworks']) is list):
        message = f'API вернул ответ некорректного типа: {response}'
        logging.error(message)
        raise TypeError(message)

    if len(response['homeworks']) < 1:
        message = f'Получен пустой список: {response}'
        logging.debug(message)
        # raise ValueError()

    return response['homeworks']


def parse_status(homework) -> str:
    if 'homework_name' not in homework:
        message = f'В ответе отсутствует ключ homework_name: {homework}'
        logging.error(message)
        raise KeyError(message)

    if 'status' not in homework:
        message = f'В ответе отсутствует ключ status: {homework}'
        logging.error(message)
        raise KeyError(message)

    if homework['status'] not in HOMEWORK_STATUSES.keys():
        message = f'Статус работы отличается от ожидаемых: {homework}'
        logging.error(message)
        raise ValueError(message)

    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка переменных окружения"""

    check_env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    result = True
    for var, val in check_env_vars.items():
        if val is None:
            result = False
            logging.critical(f'Отсутствует переменная окружения: {var}')

    return result


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    message = 'homework_bot started ...'
    logging.info(message)
    send_message(bot, message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            for homework in check_response(response):
                message = parse_status(homework)
                send_message(bot, message)
                logging.info(f'сообщение успешно отправлено {message}')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except KeyboardInterrupt:
            message = 'homework_bot stoped: ctrl+c'
            logging.info(message)
            send_message(bot, message)
            return

        except exp.API_Ya_Practicum_Exception_Endpoint as error:
            message = f'Сбой в работе Endpoint: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)

        except ValueError as error:
            message = f'Полученные данные не корректны: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)

        except TypeError as error:
            message = f'Получены данные не того типа: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=stdout,
        level=logging.DEBUG,
    )

    main()
