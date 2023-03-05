from mb.exceptions import CQError


class DjangoUnitOfWorkBindError(CQError, RuntimeError):
    pass
