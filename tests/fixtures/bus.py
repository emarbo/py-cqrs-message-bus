
import pytest

from lib.bus import MessageBus
from lib.databases import BasicTransactionManager


@pytest.fixture()
def bus():
    yield MessageBus()


@pytest.fixture()
def basic_transaction_manager(bus: MessageBus):
    yield BasicTransactionManager(bus)
