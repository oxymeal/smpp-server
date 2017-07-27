from . import DeliveryStatus, ShortMessage

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
