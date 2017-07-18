import logging
from typing import Optional

from . import parse


logger = logging.getLogger(__name__)


class ResponseSender:
    """
    Этот класс используется как интерфейс отправки пакетов клиентов через
    соединения в режиме Receiver. MessagingDispatcher использует объект
    с данным интерфейсом, чтобы отправлять клиентам отчеты о доставке
    сообщений с режимом отправки "Store and Forward".
    """

    async def send(self, pdu: parse.PDU):
        """
        Отправляет пакет клиенту по текущему соединению.
        """
        raise NotImplementedError('send')

    async def send_to_rcv(self, pdu: parse.PDU):
        """
        Отправляет пакет клиенту по существующим соединениям в режиме RECEIVER
        с тем же system_id.
        """
        raise NotImplementedError('send')


class Deliverer:
    """
    Этот класс используется как интерфейс к внешнему доставщику сообщений.
    """

    # Аргументы метода надо будет дописать по мере наобходимости.
    # Возможно, стоит создать структуру для передачи всех необходимых данных.
    def deliver(self, *args):
        raise NotImplementedError('deliver')


class Dispatcher:
    """
    Класс обработки команд соединения в режиме Transmitter.
    Отвечает за обработку пакетов и формирование ответов, т.е. за хранение
    сообщений, откладывание доставки, повторные попытки отправки, инвалидацию
    сообщений после указанного клиентом срока, замену сообщений, отмену
    сообщений, отправка отчета о доставке.
    Он же вызывает функцию осуществления доставки.

    Данный класс _не_ обязан обрабатывать пакеты BIND_* и UNBIND - это должен
    делать вызывающий код.
    """

    def __init__(self, system_id: str, password: str, d: Deliverer):
        # system_id - идентификатор пользователя.
        self.system_id = system_id
        self.password = password
        self.d = d

    async def receive(self, pdu: parse.PDU, rs: ResponseSender):
        """
        Обрабатывает очередной входящий пакет. Если на этот пакет следует
        какой-то ответ, метод его формирует и возвращает. Если ответа не следует,
        метод возвращает None.

        Этот метод гарантировано не выбрасывает никаких исключений. В случае
        ошибки обработки он возвращает пакет GENERICK_NACK согласно протоколу.

        Объект rs используется для ответа определенным пакетом в текущее соединение,
        либо в соединения в режиме receiver.
        """
        logger.info('Dispatching PDU {}'.format(pdu.command))

        nack = parse.GenericNack()
        nack.sequence_number = pdu.sequence_number
        nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
        await rs.send_to_rcv(nack)
