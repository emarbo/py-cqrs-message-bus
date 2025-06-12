from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from mb.bus import MessageBus
from mb.contrib.django.unit_of_work import DjangoUnitOfWork
from mb.unit_of_work.uow import UnitOfWork


class MessageBusMiddleware:
    """
    Bootstaps a new unit of work and makes it globally available.

    The Django setting `MB_BUS` must be either a :class:`MessageBus` instance or a
    callable that returns one.

    Tests may configure their own unit of work or message bus by setting the
    'mb.uow' or 'mb.bus' keys at the `request.META`. This is very useful insert
    specific command or event handlers that may differ form production config.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        uow = request.META.get("mb.uow")
        if not isinstance(uow, UnitOfWork):
            bus = request.META.get("mb.bus")
            if not isinstance(bus, MessageBus):
                bus = self.get_bus()
            uow = DjangoUnitOfWork(bus)

        with uow.register_globally():
            return self.get_response(request)

    def get_bus(self):
        """
        Get the bus from the Django settings
        """
        bus = settings.get("MB_BUS")
        if not bus:
            raise ImproperlyConfigured("Missing MB_BUS Django setting")

        if callable(bus):
            bus = bus()

        if not isinstance(bus, MessageBus):
            raise ImproperlyConfigured(
                "Django setting MB_BUS is not a message bus or a callable "
                "returning one"
            )

        return bus
