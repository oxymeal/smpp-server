import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from . import external, parse


logger = logging.getLogger(__name__)

DEFAULT_VALIDITY_PERIOD = 60 # In seconds


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

    def __init__(self, system_id: str, password: str, eprovider: external.Provider):
        # system_id - идентификатор пользователя.
        self.system_id = system_id
        self.password = password
        self.eprovider = eprovider

    @staticmethod
    def new_message_id() -> str:
        """
        Возвращает строку из 8 случайных 16-чных цифр.
        """
        return "".join([
            random.choice("0123456789abcdef")
            for _ in range(8)
        ])

    @staticmethod
    def parse_validity_period(vp: str) -> datetime:
        time_offset = vp[13:15]
        time_offset_sign = vp[-1]

        time_offset_in_minutes = int(time_offset) * 15
        time_offset_hours = time_offset_in_minutes // 60
        time_offset_minutes = time_offset_in_minutes - time_offset_hours * 60

        time_offset_hours_formatted = str(time_offset_hours).rjust(2, "0")
        time_offset_minutes_formatted = str(time_offset_minutes).rjust(2, "0")
        time_offset_formatted = "".join([time_offset_sign, time_offset_hours_formatted, time_offset_minutes_formatted])

        validity_period_formatted = pdu.validity_period[:12] + time_offset_formatted

        sm_validity_period = datetime.strptime(validity_period_formatted, "%y%m%d%H%M%S%z")

        return sm_validity_period

    async def _store_and_forward(
        self, message_id: str, sm: external.ShortMessage, pdu: parse.SubmitSm) -> parse.DeliverSm:

        logger.info('Dispatching SaF message, esm_class = {}'.format(pdu.esm_class))

        if not pdu.validity_period:
            sm_validity_period = datetime.now() + timedelta(0, DEFAULT_VALIDITY_PERIOD)
        else:
            sm_validity_period = self.parse_validity_period(pdu.validity_period)

        final_status = None
        expired = False
        while True:
            status = await self.eprovider.deliver(sm)

            if not status.should_retry():
                final_status = status
                break

            if datetime.now() < sm_validity_period:
                expired = True
                break

        # Return the delivery receipt pdu

        deliver_sm = parse.DeliverSm()
        deliver_sm.esm_class = parse.ESM_CLASS_RECEIPT_STORE_AND_FORWARD
        deliver_sm.service_type = pdu.service_type
        deliver_sm.source_addr_ton = pdu.dest_addr_ton
        deliver_sm.source_addr_npi = pdu.dest_addr_npi
        deliver_sm.source_addr = pdu.destination_addr
        deliver_sm.dest_addr_ton = pdu.source_addr_ton
        deliver_sm.dest_addr_npi = pdu.source_addr_npi
        deliver_sm.destination_addr = pdu.source_addr

        dr = parse.DeliveryReceipt()
        dr.id = message_id
        dr.text = sm.body

        if final_status == external.DeliveryStatus.OK:
            dr.dlvrd = 1
            dr.err = 0
        else:
            dr.dlvrd = 0
            dr.err = 1

        if final_status == external.DeliveryStatus.OK:
            dr.stat = parse.RECEIPT_DELIVERED
        elif final_status == external.DeliveryStatus.UNDELIVERABLE:
            dr.stat = parse.RECEIPT_UNDELIVERABLE
        elif final_status == external.DeliveryStatus.NO_BALANCE:
            dr.stat = parse.RECEIPT_REJECTED
        elif final_status == external.DeliveryStatus.AUTH_FAILED:
            dr.stat = parse.RECEIPT_REJECTED
        elif expired:
            dr.stat = parse.RECEIPT_EXPIRED
        else:
            dr.stat = parse.RECEIPT_UNKNOWN

        deliver_sm.short_message = dr.to_str()

        return deliver_sm

    async def _dispatch_submit_sm(self, pdu: parse.PDU, rs: ResponseSender):
        sm = external.ShortMessage(
            system_id=self.system_id, password=self.password,
            source_addr_ton=pdu.source_addr_ton, source_addr_npi=pdu.source_addr_npi, source_addr=pdu.source_addr,
            dest_addr_ton=pdu.dest_addr_ton, dest_addr_npi=pdu.dest_addr_npi, destination_addr=pdu.destination_addr,
            body=pdu.short_message
        )

        msg_mode = pdu.esm_class & parse.ESM_CLASS_MODE_MASK

        if msg_mode in [parse.ESM_CLASS_MODE_DEFAULT, parse.ESM_CLASS_MODE_STORE_AND_FORWARD]:
            message_id = self.new_message_id()

            submit_sm_resp = parse.SubmitSmResp()
            submit_sm_resp.message_id = message_id
            submit_sm_resp.sequence_number = pdu.sequence_number
            await rs.send(submit_sm_resp)

            dsm = await self._store_and_forward(message_id, sm, pdu)

            smsc_receipt = pdu.registered_delivery & parse.REGDEL_SMSC_RECEIPT_MASK
            if smsc_receipt == parse.REGDEL_SMSC_RECEIPT_REQUIRED:
                await rs.send_to_rcv(dsm)
        else:
            logger.error("Unexpected message mode: {}".format(msg_mode))
            nack = parse.GenericNack()
            nack.sequence_number = pdu.sequence_number
            nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
            await rs.send(nack)


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

        if pdu.command == parse.Command.SUBMIT_SM:
            await self._dispatch_submit_sm(pdu, rs)
        else:
            nack = parse.GenericNack()
            nack.sequence_number = pdu.sequence_number
            nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
            await rs.send_to_rcv(nack)
