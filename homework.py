"""Main body of the Bot."""
import time
import logging
import requests

import os
from dotenv import load_dotenv
import telegram
from http import HTTPStatus

from exceptions import APIError

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    encoding='utf-8',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

SECOND_IN_ONE_MONTH = 60 * 60 * 24 * 30
timestamp = int(time.time()) - SECOND_IN_ONE_MONTH


PRACTICUM_TOKEN = os.getenv('TOKEN_PRAK')
TELEGRAM_TOKEN = os.getenv('TOKEN_BOT')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Check tokens and chat id."""
    if not PRACTICUM_TOKEN:
        logging.critical('Practicum token is incorrect!')
        return False
    if TELEGRAM_TOKEN is None:
        logging.critical('Telegram bot token absent or is invalid!')
        return False
    if TELEGRAM_CHAT_ID is None:
        logging.critical('User ID is incorrect!')
        return False
    return True


def send_message(bot, message):
    """Check message and sent it if message is appropriate."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Message was sent!')
    except Exception:
        logging.error("Message wasn't sent")


def get_api_answer(timestamp):
    """Sent request to endpoint."""
    payload = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if homeworks.status_code != HTTPStatus.OK:
            raise APIError(f'Some troubles with endpoint, status code:'
                           f'{homeworks.status_code}')
    except requests.RequestException as error:
        logging.error(f'Troubles with endpoint, RequestException occurred:'
                      f'{error}')
        raise APIError(f'Troubles with endpoint, RequestException occurred:'
                       f'{error}')
    try:
        return homeworks.json()
    except requests.exceptions.JSONDecodeError as error:
        logging.error(f'Troubles with converting homework to json standard'
                      f'{error}')


def check_response(response):
    """Check response and write problems in log."""
    if not isinstance(response, dict):
        raise TypeError('Response in not a dict')
    if 'homeworks' not in response:
        raise TypeError('There is no homeworks in the response')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Homeworks are not a list')
    if not response['homeworks'][0]:
        raise IndexError('homeworks list is empty')
    if 'status' not in response['homeworks'][0]:
        raise KeyError('status is not a valid key for homework')


def parse_status(homework):
    """Check homework content."""
    if 'homework_name' not in homework:
        raise AttributeError('Unexpected homework status!')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise AttributeError('Unexpected homework status!')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_status = ''
    if not check_tokens():
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks'][0]
            current_status = homework['status']
            if current_status != last_status:
                message = parse_status(homework)
                last_status = current_status
                send_message(bot, message)
            else:
                logging.debug('No new updates')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(f'{message}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
