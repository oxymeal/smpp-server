import logging
import uuid
from datetime import datetime
from datetime import timedelta
from typing import Optional

from . import external, parse


logger = logging.getLogger(__name__)

DEFAULT_VALIDITY_PERIOD = 60


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
            sm = external.ShortMessage(
                system_id=self.system_id, password=self.password,
                source_addr_ton=pdu.source_addr_ton, source_addr_npi=pdu.source_addr_npi, source_addr=pdu.source_addr,
                dest_addr_ton=pdu.dest_addr_ton, dest_addr_npi=pdu.dest_addr_npi, destination_addr=pdu.destination_addr,
                body=pdu.short_message
            )

            msg_mode = pdu.esm_class & parse.ESM_CLASS_MODE_MASK

            if msg_mode in [parse.ESM_CLASS_MODE_DEFAULT, parse.ESM_CLASS_MODE_STORE_AND_FORWARD]:
                logger.info('Dispatch SaF PDU with esm_class = {}'.format(pdu.esm_class))

                message_id = str(uuid.uuid4())[:8]

                submit_sm_resp = parse.SubmitSmResp()
                submit_sm_resp.message_id = message_id
                submit_sm_resp.sequence_number = pdu.sequence_number

                await rs.send(submit_sm_resp)

                if not pdu.validity_period:
                    sm_validity_period = datetime.now() + timedelta(0, DEFAULT_VALIDITY_PERIOD)
                else:
                    time_offset = pdu.validity_period[13:15]
                    time_offset_sign = pdu.validity_period[-1]

                    time_offset_in_minutes = int(time_offset) * 15
                    time_offset_hours = time_offset_in_minutes // 60
                    time_offset_minutes = time_offset_in_minutes - time_offset_hours * 60

                    time_offset_hours_formatted = str(time_offset_hours).rjust(2, "0")
                    time_offset_minutes_formatted = str(time_offset_minutes).rjust(2, "0")
                    time_offset_formatted = "".join([time_offset_sign, time_offset_hours_formatted, time_offset_minutes_formatted])

                    validity_period_formatted = pdu.validity_period[:12] + time_offset_formatted

                    sm_validity_period = datetime.strptime(validity_period_formatted, "%y%m%d%H%M%S%z")

                status = ""
                while True:
                    sm_status = self.eprovider.deliver(sm)

                    if sm_status == external.DeliveryStatus.OK or (datetime.now() < sm_validity_period):
                        status = sm_status
                        break

                smsc_receipt = pdu.registered_delivery & parse.REGDEL_SMSC_RECEIPT_MASK

                if status == external.DeliveryStatus.OK and smsc_receipt == parse.REGDEL_SMSC_RECEIPT_REQUIRED:

                    deliver_sm = parse.DeliverSm()
                    deliver_sm.service_type = pdu.service_type
                    deliver_sm.source_addr_ton = pdu.source_addr_ton
                    deliver_sm.source_addr_npi = pdu.source_addr_npi
                    deliver_sm.source_addr = pdu.source_addr
                    deliver_sm.dest_addr_ton = pdu.dest_addr_ton
                    deliver_sm.dest_addr_npi = pdu.dest_addr_npi
                    deliver_sm.destination_addr = pdu.destination_addr
                    deliver_sm.sequence_number = pdu.sequence_number
                    deliver_sm.short_message = pdu.short_message

                    await rs.send_to_rcv(deliver_sm)

                return
            else:
                logger.error("Unexpected message mode: {}".format(msg_mode))
                nack = parse.GenericNack()
                nack.sequence_number = pdu.sequence_number
                nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
                await rs.send(nack)

        nack = parse.GenericNack()
        nack.sequence_number = pdu.sequence_number
        nack.command_status = parse.COMMAND_STATUS_ESME_RUNKNOWNERR
        await rs.send_to_rcv(nack)
