import asyncio
from typing import Any
from typing import Callable
from typing import List


class Signal:
    def __init__(self):
        self.receivers: List[Callable] = []

    def connect(self, receiver: Callable) -> Callable:
        self.receivers.append(receiver)
        return receiver

    def send(self, sender: Any, **kwargs):
        for receiver in self.receivers:
            if asyncio.iscoroutinefunction(receiver):
                asyncio.create_task(receiver(sender, **kwargs))
            else:
                receiver(sender, **kwargs)


post_save = Signal()
post_update = Signal()
post_delete = Signal()
