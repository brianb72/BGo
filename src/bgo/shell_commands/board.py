from bgo.shell_commands import Command

class Board(Command):

    keywords = ['board']
    help_text = """{keyword}
{divider}
Summary: Shows the current play board, or resets it.

Usage: {keyword} [reset]

Examples:

    {keyword}
    {keyword} reset
"""

    def do_command(self, *args):
        go_board = self.state.go_board
        if len(args) == 1 and args[0] == 'reset':
            print('Resetting board.\n')
            go_board.reset_board()

        print(go_board.print_board(show_hash=True, join_output=True))
