import os
from bgo.shell_commands import Command


class Rotations(Command):

    keywords = ['rotations']
    help_text = """{keyword}
{divider}
Summary: Shows all 8 rotations of the boards and their hashes.

Usage: {keyword} [marks]

Examples:

    {keyword} 

"""

    def do_command(self, *args):
        if len(args) == 1 and args[0] == 'marks':
            show_marks = True
        else:
            show_marks = False
        limit_marks = self.state.limit_marks
        go_board = self.state.go_board
        output = go_board.print_all_rotations_2x(show_hash=True, show_marks=show_marks, limit_marks=limit_marks)
        print('\n'.join(output))