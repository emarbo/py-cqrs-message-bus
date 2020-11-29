import typing as t
from pprint import pprint  # noqa
from functools import partial


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

    __stack = []

    def __new__(cls, clsname, bases, attrs):

        attrs["execute"] = ExecutionWrapper(cls.__stack, attrs["execute"])

        return super().__new__(cls, clsname, bases, attrs)


class Command(metaclass=CommandType):
    def execute(self):
        print("Executed")

    print(execute)


print(Command.execute)


if __name__ == "__main__":
    c = Command()
    c.execute()
