import os
from . import DeliveryStatus, ShortMessage

class Provider:
    """
    Базовый провайдер, который аутентифицирует всех пользователей и
    логгирует отправляемые смс в файл.
    """

    def __init__(self, file_path):
        self.file_path = file_path

    async def authenticate(self, system_id: str, password: str) -> bool:
        # Аутентифицировать всех пользователей
        return True

    async def deliver(self, sm: ShortMessage) -> DeliveryStatus:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        with open(self.file_path, 'a') as f:
            f.write(str(sm.__dict__))
            f.write("\n")

        return DeliveryStatus.OK
