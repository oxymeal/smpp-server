#!/usr/bin/env python3
import logging
import random
from enum import Enum

from smpp.server import Server
from smpp.external import ShortMessage, DeliveryStatus


logging.basicConfig(level=logging.DEBUG)


class Provider:
    """
    Этот класс используется как интерфейс к внешнему доставщику сообщений.
    """

    def authenticate(self, system_id: str, password: str) -> bool:
        return True

    def deliver(self, sm: ShortMessage) -> DeliveryStatus:
        """
        Метод выполняет попытку доставки короткого сообщения и возвращает
        один и перечисленных в DeliveryStatus результатов отправки.
        """

        f = open('container/sms.txt', 'a')
        f.write(str(sm.__dict__))
        f.write("\n")

        return random.choice(list(DeliveryStatus))

s = Server(provider=Provider())
s.run()
