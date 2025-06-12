# Python CQRS Message Bus

## Overview

This package provides an in-memory message bus to emit commands and events that
will be managed by the registered handlers.

Key features:

- Dead simple
- Flexible customization of messages
- Deferred handling of events
- Django integration

## Full example

<details>

<summary>Code example that runs as is (click to open)</summary>

```python
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import os
import sqlite3
import logging

from mb import MessageBus, Command, Event, UnitOfWork, get_current_uow


logging.basicConfig(
    level=logging.INFO,
    format="[{name}] {levelname} {asctime} {funcName}: {message}",
    style="{",
)
logger = logging.getLogger()


# -------------------------------------
# Persistence layer
# -------------------------------------

DB = "demo.sqlite"

def setup_databse():
    """
    Setup an example database
    """
    db = Path()
    if db.exists():
        os.remove(db)

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            create table users(
                id       integer primary key autoincrement,
                username text unique,
                name
            )
            """
        )

@contextmanager
def atomic():
    """
    Trick to bind uow and database transactions
    """
    uow = get_current_uow()
    conn = sqlite3.connect(DB)
    with uow:
        with conn:
            yield conn


# -------------------------------------
# User Domain
# -------------------------------------

@dataclass
class CreateUser(Command):
    username: str
    name: str


@dataclass
class UserCreated(Event):
    """
    How this works is up to you: dataclasses, Pydantic, a payload dictionary, ...
    """
    id: int
    username: str
    name: str


def create_user(cmd: CreateUser, uow: UnitOfWork) -> int:
    """
    Creates the user and emits an event on success
    """
    with atomic() as conn:
        # Create
        cursor = conn.cursor()
        cursor.execute(
            "insert into users (username, name) values (?, ?) returning id",
            (cmd.username, cmd.name),
        )
        (user_id,) = cursor.fetchone()
        # Emit event (deferred handling)
        event = UserCreated(id=user_id, username=cmd.username, name=cmd.name)
        uow.emit_event(event)
        # Commands may return a value
        return user_id


def queue_welcome_email(e: UserCreated):
    """
    Queue the email only after data is persisted
    """
    logger.info(f"Queueing welcome email for '{e.id}/{e.username}'")


# -------------------------------------
# Integration-ABC Domain
# -------------------------------------

def sync_user(e: UserCreated):
    """
    Queue or send to the 3rd party system
    """
    logger.info(f"Synchronizing user '{e.id}/{e.username}'")


# -------------------------------------
# Audit domain
# -------------------------------------

def store_event(e: Event):
    """
    Store any event for auditing purposes
    """
    logger.info(f"Storing event: '{e}'")


# -------------------------------------
# Wire things up
# -------------------------------------

bus = MessageBus()
bus.subscribe_command(CreateUser, create_user)
bus.subscribe_event(UserCreated, queue_welcome_email)
bus.subscribe_event(UserCreated, sync_user)
bus.subscribe_event("**", store_event)


# -------------------------------------
# Run
# -------------------------------------

if __name__ == "__main__":
    setup_databse()

    # The UoW is usually created and registered on every request (HTTP, task, ...)
    uow = UnitOfWork(bus)
    with uow.register_globally():

        # First run -> events are handled
        user_id = uow.handle_command(CreateUser("jdoe", "John"))

        # Second run -> events are discarded because of the integrity error
        try:
            user_id = uow.handle_command(CreateUser("jdoe", "John"))
        except Exception:
            logger.error("Command failed. No events emitted")
```

</details>

## Commands

Commands are messages that produce a change on the system. They are addressed
to one and exactly one handler. If the handler does not exist, an error is
raised.

The contents of a command are the parameters for the handler. If you want to
create a user, the command must contain all the required information to create
that user.
The way these parameters are stored (and validated) is up to you. You are free
to use Pydantic, dataclasses, attrs or whatever fits you better. Here is an
example using dataclasses:

```python
from mb import MessageBus, Command, Event, UnitOfWork

@dataclass
class CreateUser(Command):
    username: str
    name: str

def create_user(cmd: CreateUser, uow: UnitOfWork) -> int:
    """
    Create the user
    """
    with uow:
        ...

# Wire up
bus = MessageBus()
bus.subscribe_command(CreateUser, create_user)


if __name__ == "__main__":
    uow = UnitOfWork(bus)
    with uow.register_globally():
        command = CreateUser("jdoe", "John")
        uow.handle_command(command)
```

Using this library for managing commands **is not recommended** unless you want
to subscribe different handlers depending on runtime. For instance, by setting
fake handlers during tests. The message pattern always breaks "go to the
definition" feature on any IDE and also takes more cycles than a direct call.
It's not worth the complexity for an in-memory implementation.

```python
from mb import MessageBus, Command, Event, UnitOfWork, get_current_uow


def create_user(username: str, name: str) -> int:
    """
    Create the user
    """
    uow = get_current_uow()
    with uow:
        ...


# Wire up
bus = MessageBus()

if __name__ == "__main__":
    uow = UnitOfWork(bus)
    with uow.register_globally():
        # Just call it
        create_user("jdoe", "John")
```

## Events

Events represent changes on the system, metrics or any event of interest. They
may have many handlers or none at all.

As in the case of commands, the way they carry the payload is up to you.

In contrast to commands, they support more subscription options:

- By name
- By pattern
- By type and subtypes
- By custom functions

```python
from dataclasses import dataclass
from mb import MessageBus, Command, Event, UnitOfWork, get_current_uow, TypeEventMatcher


@dataclass
class UserCreated(Event):
    # custom name (otherwise, autogenrated using the qualname)
    NAME = "users.UserCreated"

    username: str
    name: str


def create_user(username: str, name: str) -> int:
    """
    Create the user
    """
    uow = get_current_uow()
    with uow:
        ...
        uow.emit_event(UserCreated(username, name))


def event_handler(event: Event):
    print(event)


# Wire up
bus = MessageBus()

bus.subscribe_event(UserCreated.NAME,    event_handler) # by name (1)
bus.subscribe_event(UserCreated,         event_handler) # by name (2)
bus.subscribe_event("users.UserCreated", event_handler) # by name (3)

bus.subscribe_event("**", event_handler)                # by pattern (any event)
bus.subscribe_event("users.*", event_handler)           # by pattern
bus.subscribe_event("users.**", event_handler)          # by pattern

bus.subscribe_event(TypeEventMatcher(UserCreated), event_handler)  # by type

if __name__ == "__main__":
    uow = UnitOfWork(bus)
    with uow.register_globally():
        create_user("jdoe", "John")
```

### Persistent events

Some events may reflect metrics or failures to be reported even when the
database transaction is rolled back. For these events, override the method
`is_persistent` with your custom implementation:

```py
from mb import Event
from app.users import check_credentials


class AuthenticationSucceeded(Event):
    ...


class AuthenticationFailed(Event):
    ...

    def is_persistent(self):
        return True


def login(username, password):
    uow = get_current_uow()
    with uow:
        user = check_credentials(username, password)
        if user:
            uow.emit(AuthenticationSucceeded(...))
            return user
        else:
            uow.emit(AuthenticationFailed(...))
            raise Exception(...)
```

### Failures on event handlers

Events handlers are allowed to fail. They do not interrupt the response of the
main command.

When an error occurs, it is logged using `logging.exception` that will be
recorded by tools like Sentry.

## Naming

Command and Event inherit from Message. All of them have an `NAME` attribute
that is autogenrated based on the qualname if not defined. The Message
metaclass checks that these names are unique at loading time.

You can customize the way these names are generated by defining your own base
classes. Here is an example for events:

```python
from mb import Event, EventMeta

class AppEventMeta(EventMeta):

    @classmethod
    def _set_default_name(cls, name: str, dic: dict[str, t.Any]):
        try:
            dic["NAME"]
        except KeyError:
            # This is the default implementation
            dic["NAME"] = f"{dic['__module__']}.{name}"


class AppEvent(Event, metaclass=AppEventMeta):
    """
    Inherit all your events from this one
    """
    pass
```

## Bootstrapping

The library works around a MessageBus instance that holds the configuration of
your command and events handlers. Nothing stops you using multiple instances if
you find a use case for that. During tests, you may clone the original bus and
drop the events handlers to prevent side-effects.

The handlers registration can be done by calling the subscribe methods or using
decorators. The decorators are recommended for better readability.

```python
# File: /app/shared/mb/bus.py
from mb import MessageBus

bus = MessageBus()


# File: /app/users/event_handlers.py
from app.shared.mb.bus import bus
from app.users.events import UserCreated

@bus.event_handler(UserCreated)
def send_welcome_email(event: UserCreated):
    ...

# This is the same as using the decorator above
bus.subscribe_event(UserCreated, send_welcome_email)
```

As it happens with other libraries (e.g. Celery), the registration happens only
when the module where the decorated funciton lives. If the module is not
imported, then it won't be registered.

Everytime your application handles a request, it should create a new UnitOfWork
that receives your bus as the only parameter. You can make this instance
available at `get_current_uow()` by calling the `register_globally` method.

```python
# File: /app/shared/mb/bus.py
from mb import MessageBus

bus = MessageBus()


# File: /app/shared/mb/middleware.py
from mb import UnitOfWork
from app.shared.bus import bus

def bus_middelware(get_response):
    uow = UnitOfWork(bus)
    with uow.register_globally():
        return get_response()
```

## Dependency injection

The UnitOfWork injects the command or event to be handled and the UnitOfWork
itself following these rules:

- The parameter is typed (forward references don't work)
- The parameter is named "message", "command", "cmd", "event" , "uow" or
  "unit_of_work"
- The parameter is positional and has no default value. In this case, the first
  possition is used for the message and the second for the UoW.

Notice that handlers are not forced to receive this parameters. They may
receive none or use defaults:

```python
from mb import MessageBus
from mb import Event

bus = MessageBus()

@bus.event_handler(Event)
def handler():
    """
    No injection
    """

@bus.event_handler(Event)
def handler(extra=None):
    """
    No injection
    """

@bus.event_handler(Event)
def handler(extra: Event = None):
    """
    Injects by annotation. The event must be a subtype of the annotation.
    """

@bus.event_handler(Event)
def handler(event):
    """
    Injects by name
    """

@bus.event_handler(Event)
def handler(m):
    """
    Injects by positional argument (first is the event or comand)
    """
```

## Access the current UoW

The current Uow is the latest that called the `register_globally` or was used
as a context manager.

```python
from mb import MessageBus, UnitOfWork, get_current_uow

bus = MessageBus()
uow = UnitOfWork(bus)

# Opens a transaction and registers globally
with uow:
    uow2 = get_current_uow()
    assert uow is uow2

# Registers globally
with uow.register_globally():
    uow2 = get_current_uow()
    assert uow is uow2


uow2 = get_current_uow(raise_if_missing=False)
asert uow2 is None

# Raises an exception
uow2 = get_current_uow()
```

## Nested transactions and event handling

The UnitOfWork supports nested transactions as regular databases do.

Events are collected at every transaction during its lifespan. Once the
transaction is committed or rolled back, the events are collected by the parent
transaction or discarded (except for the persistent events). When the outermost
transaction is closed, the remaining events are finally handled.

## Django integration

This library provides a special `DjangoUnitOfWork` and `MessageBusMiddleware`
to ease the integration.

The `DjangoUnitOfWork` basically provides a handy `atomic()` that binds the
database transaction to the UoW transaction. This works well even with
different database connections (different `using=...`) provided that you're
using the `atomic()` context manager to manage transactions. In other words,
you don't manually begin and rollback checkpoints.

The `MessageBusMiddleware` globally registers a new UoW on every request that
is accessible by calling `get_current_uow()`. It bootstraps the UoW using the
bus defined at the Django setting variable `MB_BUS`. This variable can be a
`MessageBus` instance or a callable that returns one.

Tests can provide a different `UnitOfWork` (thus a different bus) by setting
the `mb.uow` at the Django `request.META`.

## F.A.Q.

Some questions I would make myself

**Why not a Query object?** As it happens with Commands, I'm not sure how
useful would this be. I prefer to avoid complexity if not needed. It'd be totally different if we were using an external brokwer (Kafka, RabbitMQ, or similar)

**Is this used in some real project?** Yes, it is implemented in at least one
project of around 70k LOC that exposes all the logic through an API. This
project does not use commands at all, but makes extensive use of events for
decoupling, auditing and tests validation. The event is extremely customized to
the needs of the application. Tests check the event is actually emitted more
than checking objects are stored in database.

**Why not Django Signals?** The real problem with signals is that handlers are
called immediately when the signal is emitted. This causes two problems when
signals are emitted inside a database transaction. First problem is the
transaction will last as long as all hanlders are finished. This might be a
long time if the handlers perform HTTP request on slow systems. Second, if you
queue a task, the task may want to read a database object that isn't yet
persisted. Deferring the event handling solve this two problems.

**But, what happens if the event handler fails?** In this case, the task won't
be queued or the external system won't be called. In any case, the error will
be reported (e.g. to Sentry) to be fixed later. I prefer this approach by
default than the other way around. Future releases may allow registering
handlers to be executed immediately to cover some use cases. For instance, if
you register all your events in your database, you want _that_ event handler to
run inside the database transaction for auditing purposes. Forcing all to fail
or succeed at once.

## Next steps

- [ ] Poetry or uv
- [ ] Testing multiple Python versions
- [ ] Allow immediate event handlers
