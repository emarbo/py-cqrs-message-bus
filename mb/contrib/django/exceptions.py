from mb.exceptions import MbError


class DjangoUnitOfWorkBindError(MbError, RuntimeError):
    pass
