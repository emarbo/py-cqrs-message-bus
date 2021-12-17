import typing as t

from lib.commands import Command
from lib.events import Event

CommandType = type[Command]
CommandInstance = t.TypeVar("CommandInstance", bound=Command)
CommandHandler = t.Callable[["CommandInstance"], t.Any]


EventType = type[Event]
EventInstance = t.TypeVar("EventInstance", bound=Event)
EventHandler = t.Callable[["EventInstance"], t.Any]
