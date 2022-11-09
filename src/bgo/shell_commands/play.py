from bgo.shell_commands import Command
from bgo.gameofgo import GameOfGoException
import bgo.gameofgo.coordinate as Coord

class Play(Command):

    keywords = ['play']
    help_text = """{keyword}
{divider}
Summary: Plays one or more moves on the board.

Usage: {keyword} [reset]

Examples:

    {keyword} <move> [<move> ...]
    {keyword} pd
    {keyword} pd dp dd
"""

    def do_command(self, *args):
        go_board = self.state.go_board

        if len(args) == 0:
            print('Need move(s)')
            return

        if len(args) == 1 and len(args[0]) == 1:
            play_letter = args[0].lower()
            play_position = ord(play_letter[0]) - ord('a')
            marks_data = go_board.get_marks()
            try:
                play_coord = marks_data[play_position][0]
            except IndexError:
                print(f'Mark letter {play_letter} is not a valid mark.')
                return
            try:
                if not go_board.play_move(play_coord):
                    print(f'Move {play_coord} is an illegal move.\n{go_board.game.why_invalid}')
                    return
            except GameOfGoException as e:
                print(f'Move {play_coord} is invalid.')
                return
        else:
            for move in args:
                try:
                    if len(move) != 2:
                        print(f'Move {move} is invalid.\n')
                        return
                    if not go_board.play_move(Coord.Alpha(move)):
                        print(f'Move {move} is an illegal move.\n{go_board.game.why_invalid}')
                        break
                except GameOfGoException as e:
                    print(f'Move {move} is invalid.\n')
                    break

        if self.state.auto_search:
            command = self.state.commands.get('search') or None
            if not command:
                print('Command not found: search')
                return
            command.do_command()
        else:
            command = self.state.commands.get('board') or None
            if not command:
                print('Command not found: board')
                return
            command.do_command()
