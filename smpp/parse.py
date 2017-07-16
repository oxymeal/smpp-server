import struct
from enum import Enum


class Command(Enum):
    """
    Перечисление всех поддерживаемых команд и их CommandID.
    """
    UNDEFINED = -1
    GENERICK_NACK = 0x80000000
    BIND_RECEIVER = 0x00000001
    BIND_RECEIVER_RESP = 0x80000001
    BIND_TRANSMITTER = 0x00000002
    BIND_TRANSMITTER_RESP = 0x80000002
    QUERY_SM = 0x00000003
    QUERY_SM_RESP = 0x80000003
    SUBMIT_SM = 0x00000004
    SUBMIT_SM_RESP = 0x80000004
    DELIVER_SM = 0x00000005
    DELIVER_SM_RESP = 0x80000005
    UNBIND = 0x00000006
    UNBIND_RESP = 0x80000006
    REPLACE_SM = 0x00000007
    REPLACE_SM_RESP = 0x80000007
    CANCEL_SM = 0x00000008
    CANCEL_SM_RESP = 0x80000008
    BIND_TRANSCEIVER = 0x00000009
    BIND_TRANSCEIVER_RESP = 0x80000009
    ENQUIRE_LINK = 0x00000015
    ENQUIRE_LINK_RESP = 0x80000015
    SUBMIT_MULTI = 0x00000021
    SUBMIT_MULTI_RESP = 0x80000021
    DATA_SM = 0x00000103
    DATA_SM_RESP = 0x80000103


class PackingError(ValueError):
    """
    Исключения этого типа выбрасываются при ошибках кодирования пакета
    в массив байтов.
    """


class UnpackingError(ValueError):
    """
    Исключения этого типа выбрасываются при ошибках декодирования массива байтов
    в экземпляр класса пакета.
    """


class PDU:
    """
    Родительский класс всех классов пакетов SMPP.
    """

    def __init__(self):
        self.command_length = 0
        self.command_status = 0
        self.sequence_number = 0

    # Этот атрибут класса перезаписывается дочерними классами.
    command = Command.UNDEFINED

    @property
    def command_id(self) -> int:
        return self.command.value

    # Этот метод экземпляра перезаписывается дочерними классами.
    def pack(self) -> bytearray:
        """
        Кодирует экземпляр класса пакета в массив байтов согласно протоколу SMPP.
        Если при кодировании произойдет какая-то ошибка,
        метод выбросит PackingError.
        """
        raise NotImplementedError('pack')

    # Этот метод класса перезаписывается дочерними классами.
    @classmethod
    def unpack(cls, bs: bytearray) -> 'PDU':
        """
        Парсит пакет данного типа из массива байтов.
        Если при парсинге произойдет какая-то ошибка (например, синтаксис пакета
        окажется недействительным), метод выбросит UnpackingError.
        """
        raise NotImplementedError('unpack')

    def _unpack_header(self, bs: bytearray) -> bytearray:
        """
        Распаковывает заголовок каждого пакета в поля.
        Возвращает байты тела пакета.
        """
        size = struct.calcsize("!IIII")

        cl, cid, cs, sn = struct.unpack("!IIII", bs[:size])
        self.command_length = cl
        self.command = Command(cid)
        self.command_status = cs
        self.sequence_number = sn

        return bs[:size]
