import struct
from enum import Enum
from typing import Tuple, Any


class Command(Enum):
    """
    Перечисление всех поддерживаемых команд и их CommandID.
    """
    UNDEFINED = -1
    GENERIC_NACK = 0x80000000
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


COMMAND_STATUS_ESME_ROK = 0x00000000  # No Error
COMMAND_STATUS_ESME_RINVMSGLEN = 0x00000001  # Message Length is invalid
COMMAND_STATUS_ESME_RINVCMDLEN = 0x00000002  # Command Length is invalid
COMMAND_STATUS_ESME_RINVCMDID = 0x00000003  # Invalid Command ID
COMMAND_STATUS_ESME_RINVBNDSTS = 0x00000004  # Incorrect BIND Status for given command)
COMMAND_STATUS_ESME_RALYBND = 0x00000005  # ESME Already in Bound State
COMMAND_STATUS_ESME_RINVPRTFLG = 0x00000006  # Invalid Priority Flag
COMMAND_STATUS_ESME_RINVREGDLVFLG = 0x00000007  # Invalid Registered Delivery Flag
COMMAND_STATUS_ESME_RSYSERR = 0x00000008  # System Error
COMMAND_STATUS_ESME_RINVSRCADR = 0x0000000A  # Invalid Source Address
COMMAND_STATUS_ESME_RINVDSTADR = 0x0000000B  # Invalid Dest Addr
COMMAND_STATUS_ESME_RINVMSGID = 0x0000000C  # Message ID is invalid
COMMAND_STATUS_ESME_RBINDFAIL = 0x0000000D  # Bind Failed
COMMAND_STATUS_ESME_RINVPASWD = 0x0000000E  # Invalid Password
COMMAND_STATUS_ESME_RINVSYSID = 0x0000000F  # Invalid System ID
COMMAND_STATUS_ESME_RCANCELFAIL = 0x00000011  # Cancel SM Failed
COMMAND_STATUS_ESME_RREPLACEFAIL = 0x00000013  # Replace SM Failed
COMMAND_STATUS_ESME_RMSGQFUL = 0x00000014  # Message Queue Full
COMMAND_STATUS_ESME_RINVSERTYP = 0x00000015  # Invalid Service Type
COMMAND_STATUS_ESME_RINVNUMDESTS = 0x00000033  # Invalid Number of Recipients
COMMAND_STATUS_ESME_RINVDLNAME = 0x00000034  # Invalid Distribution List name
COMMAND_STATUS_ESME_RINVDESTFLAG = 0x00000040  # Destination flag is invalid
COMMAND_STATUS_ESME_RINVSUBREP = 0x00000042  # Submit with Replace
COMMAND_STATUS_ESME_RINVESMCLASS = 0x00000043  # Invalid field data esm_class
COMMAND_STATUS_ESME_RCNTSUBDL = 0x00000044  # Cannot Submit to Distribution List
COMMAND_STATUS_ESME_RSUBMITFAIL = 0x00000045  # Failure to submit_sm or submit_multi
COMMAND_STATUS_ESME_RINVSRCTON = 0x00000048  # Invalid Source address TON
COMMAND_STATUS_ESME_RINVSRCNPI = 0x00000049  # Invalid Source address NPI
COMMAND_STATUS_ESME_RINVDSTTON = 0x00000050  # Invalid Destination address TON
COMMAND_STATUS_ESME_RINVDSTNPI = 0x00000051  # Invalid Destination address NPI
COMMAND_STATUS_ESME_RINVSYSTYP = 0x00000053  # Invalid system_type field
COMMAND_STATUS_ESME_RINVREPFLAG = 0x00000054  # Invalid flag replace_if_present
COMMAND_STATUS_ESME_RINVNUMMSGS = 0x00000055  # Invalid number of messages
COMMAND_STATUS_ESME_RTHROTTLED = 0x00000058  # ESME exceeded allowed message limits
COMMAND_STATUS_ESME_RINVSCHED = 0x00000061  # Invalid Scheduled DeliveryTime
COMMAND_STATUS_ESME_RINVEXPIRY = 0x00000062  # Expiry time
COMMAND_STATUS_ESME_RINVDFTMSGID = 0x00000063  # Predefined Message Invalid or Not Found
COMMAND_STATUS_ESME_RX_T_APPN = 0x00000064  # ESME Receiver Temporary App Error Code
COMMAND_STATUS_ESME_RX_P_APPN = 0x00000065  # ESME Receiver Permanent App Error Code
COMMAND_STATUS_ESME_RX_R_APPN = 0x00000066  # ESME Receiver Reject Message Error Code
COMMAND_STATUS_ESME_RQUERYFAIL = 0x00000067  # Query failure query_sm
COMMAND_STATUS_ESME_RINVOPTPARSTREAM = 0x000000C0  # Error in the optional part of the Body PDU
COMMAND_STATUS_ESME_ROPTPARNOTALLWD = 0x000000C1  # Optional Parameter not allowed
COMMAND_STATUS_ESME_RINVPARLEN = 0x000000C2  # Invalid Parameter Length
COMMAND_STATUS_ESME_RMISSINGOPTPARAM = 0x000000C3  # Expected Optional Parameter missing
COMMAND_STATUS_ESME_RINVOPTPARAMVAL = 0x000000C4  # Invalid Optional Parameter Value
COMMAND_STATUS_ESME_RDELIVERYFAILURE = 0x000000FE  # Delivery Failure
COMMAND_STATUS_ESME_RUNKNOWNERR = 0x000000FF  # Unknown Error


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

    # Этот атрибут класса перезаписывается дочерними классами.
    command = Command.UNDEFINED

    def __init__(self):
        self.command_status = 0
        self.sequence_number = 0

    @property
    def command_id(self) -> int:
        return self.command.value

    @property
    def command_length(self) -> int:
        return NotImplementedError("command_length")

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

        ps, cid, cs, sn = struct.unpack("!IIII", bs[:size])
        if len(bs) != ps:
            raise UnpackingError(
                "The size of the package does not coincide with the received")
        if self.command_id != cid:
            raise UnpackingError(
                "The command identifier does not match the received")
        self.command_status = cs
        self.sequence_number = sn

        return bs[size:]

    def _pack_header(self) -> bytearray:
        """
        Запаковывает заголовок пакета в массив байтов.
        """
        return struct.pack("!IIII", self.command_length, self.command_id,
                           self.command_status, self.sequence_number)


class EnquireLink(PDU):

    command = Command.ENQUIRE_LINK

    @property
    def command_length(self) -> int:
        return 16

    def pack(self) -> bytearray:
        return self._pack_header()

    @classmethod
    def unpack(cls, bs: bytearray) -> 'EnquireLink':
        p = EnquireLink()
        p._unpack_header(bs)
        return p


class EnquireLinkResp(PDU):

    command = Command.ENQUIRE_LINK_RESP

    @property
    def command_length(self) -> int:
        return 16

    def pack(self) -> bytearray:
        return self._pack_header()

    @classmethod
    def unpack(cls, bs: bytearray) -> 'EnquireLinkResp':
        p = EnquireLinkResp()
        p._unpack_header(bs)
        return p


def _unpack_fmt(fmt: str, bs: bytearray) -> Tuple[Tuple[Any], bytearray]:
    size = struct.calcsize(fmt)

    if len(bs) <= size:
        raise UnpackingError("The package size does not match the expected")

    params = struct.unpack(fmt, bs[:size])

    return params, bs[size:]


def unpack_coctet_string(bs: bytearray) -> Tuple[str, bytearray]:
    string = bytearray()
    for byte in bs:
        if byte == 0:
            return string.decode('ascii'), bs[len(string) + 1:]
        string.append(byte)
    raise UnpackingError("Null byte has not been reached")


def _pack_str(input_str: str, max_size: int) -> bytearray:
    input_str = st.encode('ascii')
    input_str += b'\x00'
    if len(input_str) > max_size:
        raise PackingError("Field size too long")
    return input_str


def _pack_fmt(fmt: str, *params) -> bytearray:
    try:
        b = struct.pack(fmt, *params)
    except struct.error:
        raise PackingError("Format {}, cannot pack with this params {}", fmt,
                           params)
    return b


class BindTransmitter(PDU):

    command = Command.BIND_TRANSMITTER

    def __init__(self):
        super().__init__()
        self.system_id = ""
        self.password = ""
        self.system_type = ""
        self.interface_version = 0
        self.addr_ton = 0
        self.addr_npi = 0
        self.address_range = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        sid_size = len(self.system_id) + 1
        pwd_size = len(self.password) + 1
        syt_size = len(self.system_type) + 1
        iv_at_an_size = 3
        adr_size = len(self.address_range) + 1
        return header_size + sid_size + pwd_size + syt_size + iv_at_an_size + adr_size

    @classmethod
    def unpack(cls, bs: bytearray) -> 'BindTransmitter':
        pdu = BindTransmitter()
        bs = pdu._unpack_header(bs)
        pdu.system_id, bs = unpack_coctet_string(bs)
        pdu.password, bs = unpack_coctet_string(bs)
        pdu.system_type, bs = unpack_coctet_string(bs)
        (iv, at, an), bs = _unpack_fmt('!BBB', bs)
        pdu.interface_version = iv
        pdu.addr_ton = at
        pdu.addr_npi = an
        pdu.address_range, _ = unpack_coctet_string(bs)
        return pdu


class BindReceiver(PDU):

    command = Command.BIND_RECEIVER

    def __init__(self):
        super().__init__()
        self.system_id = ""
        self.password = ""
        self.system_type = ""
        self.interface_version = 0
        self.addr_ton = 0
        self.addr_npi = 0
        self.address_range = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        sid_size = len(self.system_id) + 1
        pwd_size = len(self.password) + 1
        syt_size = len(self.system_type) + 1
        iv_at_an_size = 3
        adr_size = len(self.address_range) + 1
        return header_size + sid_size + pwd_size + syt_size + iv_at_an_size + adr_size

    @classmethod
    def unpack(cls, bs: bytearray) -> 'BindReceiver':
        pdu = BindReceiver()
        bs = pdu._unpack_header(bs)
        pdu.system_id, bs = unpack_coctet_string(bs)
        pdu.password, bs = unpack_coctet_string(bs)
        pdu.system_type, bs = unpack_coctet_string(bs)
        (iv, at, an), bs = _unpack_fmt('!BBB', bs)
        pdu.interface_version = iv
        pdu.addr_ton = at
        pdu.addr_npi = an
        pdu.address_range, _ = unpack_coctet_string(bs)
        return pdu


class BindTransceiver(PDU):

    command = Command.BIND_TRANSCEIVER

    def __init__(self):
        super().__init__()
        self.system_id = ""
        self.password = ""
        self.system_type = ""
        self.interface_version = 0
        self.addr_ton = 0
        self.addr_npi = 0
        self.address_range = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        sid_size = len(self.system_id) + 1
        pwd_size = len(self.password) + 1
        syt_size = len(self.system_type) + 1
        iv_at_an_size = 3
        adr_size = len(self.address_range) + 1
        return header_size + sid_size + pwd_size + syt_size + iv_at_an_size + adr_size

    @classmethod
    def unpack(cls, bs: bytearray) -> 'BindTransceiver':
        pdu = BindTransceiver()
        bs = pdu._unpack_header(bs)
        pdu.system_id, bs = unpack_coctet_string(bs)
        pdu.password, bs = unpack_coctet_string(bs)
        pdu.system_type, bs = unpack_coctet_string(bs)
        (iv, at, an), bs = _unpack_fmt('!BBB', bs)
        pdu.interface_version = iv
        pdu.addr_ton = at
        pdu.addr_npi = an
        pdu.address_range, _ = unpack_coctet_string(bs)
        return pdu


# TODO: Сделать TLV.
class BindTransmitterResp(PDU):

    command = Command.BIND_TRANSMITTER_RESP

    def __init__(self):
        super().__init__()
        self.system_id = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        sid_size = len(self.system_id) + 1
        return header_size + sid_size

    def pack(self) -> bytearray:
        response = bytearray()
        bs = self._pack_header()
        response += bs

        response += _pack_str(self.system_id, 16)

        return response


class BindReceiverResp(PDU):

    command = Command.BIND_RECEIVER_RESP

    def __init__(self):
        super().__init__()
        self.system_id = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        sid_size = len(self.system_id) + 1
        return header_size + sid_size

    def pack(self) -> bytearray:
        response = bytearray()
        bs = self._pack_header()
        response += bs

        response += _pack_str(self.system_id, 16)

        return response


class BindTransceiverResp(PDU):

    command = Command.BIND_TRANSCEIVER_RESP

    def __init__(self):
        super().__init__()
        self.system_id = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        sid_size = len(self.system_id) + 1
        return header_size + sid_size

    def pack(self) -> bytearray:
        response = bytearray()
        bs = self._pack_header()
        response += bs

        response += _pack_str(self.system_id, 16)

        return response


class Unbind(PDU):

    command = Command.UNBIND

    @property
    def command_length(self) -> int:
        return 16

    def pack(self) -> bytearray:
        return self._pack_header()

    @classmethod
    def unpack(cls, bs: bytearray) -> 'Unbind':
        p = Unbind()
        p._unpack_header(bs)
        return p


class UnbindResp(PDU):

    command = Command.UNBIND_RESP

    @property
    def command_length(self) -> int:
        return 16

    def pack(self) -> bytearray:
        return self._pack_header()

    @classmethod
    def unpack(cls, bs: bytearray) -> 'UnbindResp':
        p = UnbindResp()
        p._unpack_header(bs)
        return p


class GenericNack(PDU):

    command = Command.GENERIC_NACK

    @property
    def command_length(self) -> int:
        return 16

    def pack(self) -> bytearray:
        return self._pack_header()

    @classmethod
    def unpack(cls, bs: bytearray) -> 'GenericNack':
        p = GenericNack()
        p._unpack_header(bs)
        return p


def _unpack_octet_string(bs: bytearray,
                         sm_length: int) -> Tuple[str, bytearray]:
    return bs[:sm_length].decode('ascii'), bs[sm_length:]


class SubmitSm(PDU):

    command = Command.SUBMIT_SM

    def __init__(self):
        self.service_type = ""
        self.source_addr_ton = 0
        self.source_addr_npi = 0
        self.source_addr = ""
        self.dest_addr_ton = 0
        self.dest_addr_npi = 0
        self.destination_addr = ""
        self.esm_class = 0
        self.protocol_id = 0
        self.priority_flag = 0
        self.schedule_delivery_time = ""
        self.validity_period = ""
        self.registered_delivery = 0
        self.replace_if_present_flag = 0
        self.data_coding = 0
        self.sm_default_msg_id = 0
        self.sm_length = 0
        self.short_message = ""

    @property
    def command_length(self) -> int:
        header_size = 16
        st_size = len(self.service_type) + 1
        sat_size = 1  # self.source_addr_ton
        san_size = 1  # self.source_addr_npi
        sa_size = len(self.source_addr) + 1
        dat_size = 1  # self.dest_addr_ton
        dan_size = 1  # self.dest_addr_npi
        da_size = len(self.destination_addr) + 1
        ec_size = 1  # self.esm_class
        pid_size = 1  # self.protocol_id
        pf_size = 1  # self.priority_flag
        sdt_size = len(self.schedule_delivery_time) + 1
        dp_size = len(self.validity_period) + 1
        rd_size = 1  # self.registered_delivery
        ripf_size = 1  # self.replace_if_present_flag
        dc_size = 1  # self.data_coding
        sdmi_size = 1  # self.sm_default_msg_id
        sl_size = 1  # self.sm_length
        sm_size = len(self.short_message) + 1
        return header_size +  st_size + sat_size + san_size + sa_size\
                + dat_size + dan_size + da_size + ec_size\
                + pid_size + pf_size + sdt_size + dp_size\
                + rd_size + ripf_size + dc_size + sdmi_size\
                + sl_size + sm_size

    def pack(self) -> bytearray:
        response = bytearray()
        response += self._pack_header()
        response += _pack_str(self.service_type, 6)
        response += _pack_fmt("!BB", self.source_addr_ton,
                              self.source_addr_npi)
        response += _pack_str(self.source_addr, 21)
        response += _pack_fmt("!BB", self.dest_addr_ton, self.dest_addr_npi)
        response += _pack_str(self.destination_addr, 21)
        response += _pack_fmt("!BBB", self.esm_class, self.protocol_id,
                              self.priority_flag)
        response += _pack_str(self.schedule_delivery_time, 17)
        response += _pack_str(self.validity_period, 17)
        response += _pack_fmt("!BBBB", self.registered_delivery,
                              self.replace_if_present_flag, self.data_coding,
                              self.sm_default_msg_id, self.sm_length)
        response += _pack_str(self.short_message, 254)
        return response

    @classmethod
    def unpack(cls, bs: bytearray) -> 'SubmitSm':
        pdu = SubmitSm()

        bs = pdu._unpack_header(bs)
        pdu.service_type, bs = unpack_coctet_string(bs)
        (sdt, anp), bs = _unpack_fmt('!BB', bs)
        pdu.source_addr_ton = sdt
        pdu.source_addr_npi = anp
        pdu.source_addr, bs = unpack_coctet_string(bs)
        (dat, dan), bs = _unpack_fmt('!BB', bs)
        pdu.dest_addr_ton = dat
        pdu.dest_addr_npi = dan
        pdu.destination_addr, bs = unpack_coctet_string(bs)
        (ec, pid, pf), bs = _unpack_fmt('!BBB', bs)
        pdu.esm_class = ec
        pdu.protocol_id = pid
        pdu.priority_flag = pf
        pdu.schedule_delivery_time, bs = unpack_coctet_string(bs)
        pdu.validity_period, bs = unpack_coctet_string(bs)
        (rd, ripf, dc, smdi, sl), bs = _unpack_fmt('!BBBBB', bs)
        pdu.registered_delivery = rd
        pdu.replace_if_present_flag = ripf
        pdu.data_coding = dc
        pdu.sm_default_msg_id = smdi
        pdu.sm_length = sl
        pdu.short_message, _ = _unpack_octet_string(bs, pdu.sm_length)

        return pdu


class SubmitSmResp(PDU):

    command = Command.SUBMIT_SM_RESP

    def __init__(self):
        self.message_id = ""

    @property
    def command_length(self) -> int:
        head_size = 16
        mid_size = len(self.message_id) + 1
        return head_size + mid_size

    def pack(self) -> bytearray:
        response = bytearray()
        response += self._pack_header()
        response += _pack_str(self.message_id, 65)
        return response


_COMMAND_CLASSES = {
    Command.BIND_RECEIVER: BindReceiver,
    Command.BIND_RECEIVER_RESP: BindReceiverResp,
    Command.BIND_TRANSMITTER: BindTransmitter,
    Command.BIND_TRANSMITTER_RESP: BindTransmitterResp,
    Command.BIND_TRANSCEIVER: BindTransceiver,
    Command.BIND_TRANSCEIVER_RESP: BindTransceiverResp,
    Command.ENQUIRE_LINK: EnquireLink,
    Command.ENQUIRE_LINK_RESP: EnquireLinkResp,
    Command.UNBIND: Unbind,
    Command.UNBIND_RESP: UnbindResp,
    Command.GENERIC_NACK: GenericNack,
    Command.SUBMIT_SM: SubmitSm,
    Command.SUBMIT_SM_RESP: SubmitSmResp,
    # QUERY_SM = 0x00000003
    # QUERY_SM_RESP = 0x80000003
    # DELIVER_SM = 0x00000005
    # DELIVER_SM_RESP = 0x80000005
    # REPLACE_SM = 0x00000007
    # REPLACE_SM_RESP = 0x80000007
    # CANCEL_SM = 0x00000008
    # CANCEL_SM_RESP = 0x80000008
    # BIND_TRANSCEIVER = 0x00000009
    # BIND_TRANSCEIVER_RESP = 0x80000009
    # ENQUIRE_LINK = 0x00000015
    # ENQUIRE_LINK_RESP = 0x80000015
    # SUBMIT_MULTI = 0x00000021
    # SUBMIT_MULTI_RESP = 0x80000021
    # DATA_SM = 0x00000103
    # DATA_SM_RESP = 0x80000103
}


def unpack_pdu(bs: bytearray) -> PDU:

    size = struct.calcsize('!II')
    _, cid = struct.unpack("!II", bs[:size])

    return _COMMAND_CLASSES[Command(cid)].unpack(bs)
