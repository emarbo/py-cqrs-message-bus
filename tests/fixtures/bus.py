
import pytest

from lib.bus import MessageBus
from lib.bus import TransactionManager


@pytest.fixture()
def bus():
    yield MessageBus()


@pytest.fixture()
def transaction_manager(bus: MessageBus):
    yield TransactionManager(bus)


