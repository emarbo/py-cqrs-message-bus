from mb.contrib.django.unit_of_work import DjangoUnitOfWork
from mb.unit_of_work import UnitOfWork
from app.common.bus.bus import bus


class UnitOfWorkInjectionMiddleware:
    """
    Bootstaps and injects a new UnitOfWork in the request.META
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Tests may inject its own UnitOfWork
        uow = request.META.get("uow")
        if not isinstance(uow, UnitOfWork):
            request.META["uow"] = DjangoUnitOfWork(bus)

        return self.get_response(request)
