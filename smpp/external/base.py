from enum import Enum

class ShortMessage:
    def __init__(self, *,
                 system_id: str, password: str,
                 source_addr_ton: int, source_addr_npi :int, source_addr: str,
                 dest_addr_ton: int, dest_addr_npi: int, destination_addr: str,
                 body: str):
        self.system_id = system_id
        self.password = password

        self.source_addr_ton = source_addr_ton
        self.source_addr_npi = source_addr_npi
        self.source_addr = source_addr

        self.dest_addr_ton = dest_addr_ton
        self.dest_addr_npi = dest_addr_npi
        self.destination_addr = destination_addr

        self.body = body


class DeliveryStatus(Enum):
    DELIVERED = 0 # Доставлено
    EXPIRED = 1 # Время на доставку истекло
    DELETED = 2 # Сообщение удалено до доставки
    UNDELIVERABLE = 3 # Сообщение недостовляемо
    ACCEPTED = 4 # Принято, но будет доставлено позже
    UNKNOWN = 5 # Неизвестный статус
    REJECTED = 6 # Отклонено

    # Особый статус, который сообщает серверу, что ему нужно предпринять еще
    # одну попытки доставки чуть позже (еще раз вызвать метод deliver),
    # если время жизни сообщений еще не истекло. Если сообщение устарело,
    # клиенту будет отправлен статус EXPIRED.
    TRY_LATER = 100

class Provider:
    """
    Этот класс используется как интерфейс к внешнему доставщику сообщений.
    """

    async def authenticate(self, system_id: str, password: str) -> bool:
        """
        Метод возвращает True, если аутентификация пользователя с данными
        system_id и паролем успешна.
        """
        raise NotImplementedError('authenticate')

    async def deliver(self, sm: ShortMessage) -> DeliveryStatus:
        """
        Метод выполняет попытку доставки короткого сообщения и возвращает
        один и перечисленных в DeliveryStatus результатов отправки.
        """
        raise NotImplementedError('deliver')
