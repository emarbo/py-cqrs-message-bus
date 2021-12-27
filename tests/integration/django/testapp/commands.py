import typing as t
from dataclasses import dataclass

from cq.commands import Command
from tests.utils.tracked_handler import tracked_handler
from tests.integration.django.testapp.models import User


@dataclass
class CreateUserCommand(Command):
    username: str


@tracked_handler
def create_user_handler(cmd: CreateUserCommand) -> "User":

    return User.new_user(cmd.username)
