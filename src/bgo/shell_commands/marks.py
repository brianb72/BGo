import os
from bgo.shell_commands import Command


class Marks(Command):

    keywords = ['marks']
    help_text = """{keyword}
{divider}
Summary: Limits the number of next move marks shown on the search board, maximum of 26.

Usage: {keyword} <number of marks>

Examples:

    {keyword} 12

"""

    def do_command(self, *args):
        if not args or len(args) != 1:
            print('Expecting argument between 1 and 26.')
            return

        try:
            value = int(args[0])
        except (ValueError, TypeError):
            print('Invalid argument.')
            return

        if not 0 < value <= 25:
            print('Number of marks must be between 1 and 26.')
            return

        self.state.limit_marks = value
        print(f'Number of marks limited to {value}.')


