from dataclasses import dataclass

from cq.events import Event
from cq.utils.tracked_handler import tracked_handler


@dataclass
class UserCreatedEvent(Event):
    id: int
    username: str


@tracked_handler
def user_created_handler(event: UserCreatedEvent) -> None:
    return None
