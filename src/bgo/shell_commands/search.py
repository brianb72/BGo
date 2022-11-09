from bgo.shell_commands import Command
from bgo.dbaccess import DBAccess, DBAccessException, DBAccessLookupNotFound
import bgo.gameofgo.coordinate as Coord

class Search(Command):

    keywords = ['search']
    help_text = """{keyword}
{divider}
Summary: Searches the database for the pattern on the current play board.

Usage: {keyword}
"""

    def do_command(self, *args):
        db = self.state.db_access
        go_board = self.state.go_board

        # Get the next move information
        board_hashes = [go_board.game.build_hash(transform_number) for transform_number in range(8)]

        try:
            results = db.lookup_next_move(board_hashes, year_min=self.state.min_year, year_max=self.state.max_year)
        except DBAccessException as e:
            print(f'Error while accessing database! {self.state.database_path} - {e}')
            return
        except DBAccessLookupNotFound:
            print(f'No results found')
            return

        # Add the next move results to the go_board
        go_board.reset_marks()
        total_count = 0
        for next_move, game_count, *_ in results[:self.state.limit_marks]:
            go_board.add_mark(Coord.Alpha(next_move[0], next_move[1]), game_count)
            total_count += game_count
        # Display the board
        command = self.state.commands.get('board') or None
        if not command:
            print('Command not found: board')
            return

        command.do_command()
        print(f'Total count: {total_count}')

