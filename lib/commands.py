import typing as t
from pprint import pprint  # noqa


class ExecutionWrapper:

    __command_stack: list
    __execute_method: t.Callable

    def __init__(self, command_stack, execute_method):
        self.__command_stack = command_stack
        self.__execute_method = execute_method

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:

            def wrapper():
                self.__command_stack.append(None)
                try:
                    print("Before")
                    self.__execute_method(instance)
                finally:
                    self.__command_stack.pop()
                    if not self.__command_stack:
                        print("Command End")

            return wrapper


class CommandType(type):

    #
    # TODO: Allow a way to configure the Command Bus. This Bus should be a singleton
    # instance for all the Commands.
    #
    # TODO: Prepare Event Bus handling multi-threading. That is, the same thread must
    # execute its own events. Probably this needs to threadlocal the __queue or use
    # closures.
    #
    # TODO: Prepare the ExecutionWrapper / CommandType to handle multi-threaded stacks.
    #

    __stack: t.List[t.Any] = []

    def __new__(cls, clsname, bases, attrs):
        #
        # TODO: Improve this hack for an inherited `execute`. We shouldn't wrap twice
        # and each Command should have its own `execute`.
        #
        if "execute" in attrs:
            attrs["execute"] = ExecutionWrapper(cls.__stack, attrs["execute"])
        return super().__new__(cls, clsname, bases, attrs)


class Command(metaclass=CommandType):
    def execute(self):
        print("Command")
        self._parent_method()

    def _parent_method(self):
        print("Parent method")


if __name__ == "__main__":
    c = Command()
    c.execute()
