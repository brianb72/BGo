"""
Provide a command line interface to work with the database, display a go board, and play moves on it.
"""

from attr import attrs, attrib
from importlib import import_module
import os
import site
import pkgutil
import sys
import traceback
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from bgo.gameofgo.goboard import GoBoard
from bgo.dbaccess import DBAccess, DBAccessException, DBAccessGameRecordError, DBAccessLookupNotFound, DBAccessDuplicate

DEFAULT_DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'bgogames.sqlite')


@attrs
class ShellState:
    database_path = attrib(default=DEFAULT_DATABASE_PATH)
    working_dir = attrib(default=None)
    commands = attrib(default={})
    session = attrib(default=None)
    key_bindings = attrib(default=None)
    go_board = attrib(default=GoBoard())
    db_access = attrib(default=None)
    auto_search = attrib(default=True)
    min_year = attrib(default=None)
    max_year = attrib(default=None)
    limit_marks = attrib(default=12)


def load_commands(state, session):
    """
    Load each command script from the commands directory.

    :param state:
    :param session:
    :return:
    """
    path = os.path.join(os.path.dirname(__file__), "shell_commands")
    modules = pkgutil.iter_modules(path=[path])

    for loader, mod_name, ispkg in modules:
        if mod_name not in sys.modules:
            loaded_mod = import_module('bgo.shell_commands.'+mod_name)
            class_name = ''.join([x.title() for x in mod_name.split('_')])
            loaded_class = getattr(loaded_mod, class_name, None)
            if not loaded_class:
                continue
            # Create an instance of the class
            instance = loaded_class(state, session)


def main_loop():
    session = PromptSession()
    kb = KeyBindings()
    start_dir = os.path.dirname(os.path.realpath(__file__))
    working_dir = os.getcwd()
    db_access = DBAccess(DEFAULT_DATABASE_PATH)
    game_count = db_access.get_game_count_in_database()
    print(f'Start {start_dir}  Work {working_dir}')
    print(f'Using database [{DEFAULT_DATABASE_PATH}] with {game_count} games.')

    state = ShellState(session=session, key_bindings=kb, working_dir=working_dir, db_access=db_access)
    load_commands(state, session)

    while True:
        try:
            user_input = session.prompt("> ", key_bindings=kb)
            if not user_input:
                continue
            else:
                user_input = user_input.split()

            print()

            if user_input[0] == 'exit':
                break

            command = state.commands.get(user_input[0]) or None
            if not command:
                print("Unknown command.")
                continue

            command.do_command(*user_input[1:])

        except (EOFError, KeyboardInterrupt):
            pass
        except Exception as e:
            traceback.print_exc()


def main():
    main_loop()

if __name__ == '__main__':
    main_loop()

