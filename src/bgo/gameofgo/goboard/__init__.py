import math
import numpy as np
from bgo.gameofgo.gostone import StoneColor, color_char
import bgo.gameofgo.coordinate as Coord
from bgo.gameofgo import GameOfGo, GameOfGoException


class GoBoard(object):
    """
        GoBoard wraps a GameOfGo and can print it to the screen using text drawing
        marks_dict = {coord: count}
    """
    def __init__(self, title=None):
        self.game = GameOfGo()
        self.board_title = '' if title is None else title
        self.marks_dict = {}

    # -----------------------------------------------------------------------------

    def add_mark(self, coord, count):
        """
        Add count to coord.
        If coord is invalid, silently ignore.
        :param coord: Valid coordinate
        :param count: Integer count
        :return:
        """
        cart_coord = Coord.to_cart(coord)
        if not Coord.is_valid(cart_coord):
            return
        try:
            self.marks_dict[cart_coord] += count
        except KeyError:
            self.marks_dict[cart_coord] = count

    # -----------------------------------------------------------------------------

    def reset_marks(self):
        """
        Resets marks_dict to a blank dictionary.
        :return:
        """
        self.marks_dict = {}

    # -----------------------------------------------------------------------------

    def reset_board(self):
        """
        Removes moves and stones from board.
        :return:
        """
        self.reset_marks()
        self.game.reset_position()

    # -----------------------------------------------------------------------------

    def undo_last_move(self):
        """
        Removes the last move and replays the game with one fewer moves.

        :return: True if the new moves are accepted, false if rejected
        """
        return self.load_moves(self.game.move_list[:-1])

    # -----------------------------------------------------------------------------

    def load_moves(self, cart_coord_list):
        """
        Resets the board and plays a list of moves onto it. If the moves are not accepted will return false and
        then self.game.why_invalid will contain a string explanation of why the last move was rejected.

        :param cart_coord_list: List of Cart coordinate moves to play
        :return: True if moves accepted, False if a move was rejected and then self.game.why_invalid will be set
        """
        self.reset_board()
        try:
            for cart_coord in cart_coord_list:
                if not self.play_move(cart_coord):
                    return False
        except GameOfGoException:
            return False

    # -----------------------------------------------------------------------------

    def play_move(self, cart_coord):
        """
        Plays a move on the board .

        :param cart_coord: Cart coordinate of move to play
        :return: True if move was accepted, False if rejected and self.game.why_invalid set to string explanation
        """
        self.reset_marks()
        try:
            return self.game.play_move(cart_coord)
        except GameOfGoException:
            return False

    # -----------------------------------------------------------------------------

    def transform_board(self, to_transform, invert=False):
        """
        Changes the current board to a new transformed board.
            If invert is False, transforms the board to transform to the value in parameter to_transform.
            If invert is True, perform the inverse transform.

        The inverse transform asks "If we transformed from identity to n, what transform number then returns to identity?"

        Calling board.transform(n, False) changes the board using transform n.
        Then    board.transform(n, True) changes the board back to the original board.

        :param to_transform: int transform number 0 to 7
        :param invert: bool Should the inverse transform be performed?
        :return:
        """
        self.game.transform_position(to_transform, invert)

    # -----------------------------------------------------------------------------

    def get_marks(self, transform_number=0):
        """
        Returns a dictionary containing all board marks, with coordinates transformed by transform_number.
        :param transform_number: int transform number 0 to 7
        :return: {coord: count} Dictionary of all marks on board
        """
        td = {Coord.transform(k, transform_number): v for k, v in self.marks_dict.items()}
        return sorted(td.items(), key=lambda x: x[1], reverse=True)

    # -----------------------------------------------------------------------------


    """
        Format guide for printing the board

        42 wide
        21 per half
        s . . . . . . . . . . . . . . . . . . . s
          A B C D E F G H I J K L M N O P Q R S  
                             x
                  1         2         3         4
        0123456789012345678901234567890123456789012
                  x          x        x
          A B C D E F G H I J K L M N O P Q R S  
              A - 123456          B - 123456                                  

    """

    def print_board(self, transform_number=0, show_marks=True, show_hash=True, limit_marks=25, join_output=True):
        """
        Returns a string or list of strings that are a text representation of the current board.

        The board is transformed by transform number before printing.
        If show_hash is True a board hash is printed at the bottom of the board.
        If join_output is False returns a list of strings that represent the board.
        If join_output is True the list of strings is joined with newlines and the resulting string is returned.

        :param transform_number: int Transform number to transform the board by before printing
        :param show_marks: bool Should the marks letters be printed on the board?
        :param show_hash: bool Should board hash be printed at bottom of board?
        :param limit_marks: int Maximum number of marks, must be <= 25
        :param join_output: bool Should list of lines be joined with newlines?
        :return: str if join_output True, list of str if join_output False
        """
        star_point_values = [3, 9, 15]
        output_lines = []
        output_board = np.array([[color_char(StoneColor.NONE) for x in range(19)] for y in range(19)])

        # Get the marks data, and convert it to [(coord, count, letter), ...] sorted descending by count
        marks_data = self.get_marks(transform_number) if show_marks else []
        marks_data = [(coord, count, chr(97 + index))
                      for index, (coord, count) in enumerate(marks_data[:max(25, limit_marks)])]

        # Draw the 9 star points on the board
        for y in star_point_values:
            for x in star_point_values:
                output_board[y][x] = '+'

        if len(marks_data) > 0:
            # Draw the marks on the board using letters starting at 'a'
            for marks_coord, count, marks_letter in marks_data[:limit_marks]:
                output_board[marks_coord.y][marks_coord.x] = marks_letter

        # Transform each stones coordinates by transform_number and draw it on the output board
        for orig_coord in self.game.stone_coord_set:
            new_coord = Coord.transform(orig_coord, transform_number)
            output_board[new_coord.y][new_coord.x] = color_char(StoneColor(self.game.board[orig_coord.y][orig_coord.x]))

        # Using the output_board, create the output lines
        output_lines.append(f'{"  " + self.board_title:^42}')
        output_lines.append('   A B C D E F G H I J K L M N O P Q R S   ')
        for index, row in enumerate(output_board):
            letter = chr(ord('A') + index)
            output_lines.append(f' {letter} {" ".join(row)} {letter} ')
        output_lines.append('   A B C D E F G H I J K L M N O P Q R S   ')
        if show_hash:
            output_lines.append(f'{self.game.build_hash(use_transform=transform_number):^42}')

        if len(marks_data) > 0:
            # Print information about the marks under the board
            half_size = int(math.ceil(min(len(marks_data), limit_marks) / 2))
            list_left = marks_data[:half_size]
            list_right = marks_data[half_size:]

            for i in range(len(list_left)):
                text_left = f'{list_left[i][2]:>8} - {list_left[i][1]:<6}'
                try:
                    text_right = f'{list_right[i][2]:>6} - {list_right[i][1]:<6}'
                except IndexError:
                    text_right = ''
                output_lines.append(f'{text_left:<20}  {text_right:<20}')

        if join_output:
            return '\n'.join(output_lines)
        else:
            return output_lines

    # -----------------------------------------------------------------------------

    def print_all_rotations_4x(self, show_hash=True, show_marks=False, limit_marks=25):
        """
        Prints all rotations of the current board in a grid of 4 boards by 2 boards.

        :param show_hash: bool Should a board hash be printed at the bottom of each board?
        :return: list of str, output lines that can be printed to the screen
        """
        def _get_board_line_4x(board_lines, line_num):
            try:
                return board_lines[line_num]
            except IndexError:
                return ' ' * 42

        def _print_4(board_list):
            max_line = max([len(board_list[x]) for x in range(4)])
            output = []
            for line_num in range(max_line):
                output.append(f'{_get_board_line_4x(board_list[0], line_num)} '
                              f'{_get_board_line_4x(board_list[1], line_num)} '
                              f'{_get_board_line_4x(board_list[2], line_num)} '
                              f'{_get_board_line_4x(board_list[3], line_num)} ')
            return output

        boards = []
        ret = []
        old_title = self.board_title
        for tn in range(8):
            self.board_title = f'{tn}: {Coord.TRANSFORMATION_NAMES[tn]}'
            boards.append(self.print_board(transform_number=tn, show_hash=show_hash, show_marks=show_marks, limit_marks=limit_marks, join_output=False))
        sel.board_title = old_title
        ret.extend(_print_4(boards[0:4]))
        ret.append('')
        ret.extend(_print_4(boards[4:8]))
        return ret


    def print_all_rotations_2x(self, show_hash=True, show_marks=False, limit_marks=25):
        """
        Prints all rotations of the current board in a grid of 2 boards by 4 boards.

        :param show_hash: bool Should a board hash be printed at the bottom of each board?
        :return: list of str, output lines that can be printed to the screen
        """
        def _get_board_line(board_lines, line_num):
            try:
                return board_lines[line_num]
            except IndexError:
                return ' ' * 42

        def _print_2(board_list):
            max_line = max([len(board_list[x]) for x in range(2)])
            output = []
            for line_num in range(max_line):
                output.append(f'{_get_board_line(board_list[0], line_num)} '
                              f'{_get_board_line(board_list[1], line_num)} ')
            return output

        boards = []
        ret = []
        old_title = self.board_title
        for tn in range(8):
            self.board_title = f'{tn}: {Coord.TRANSFORMATION_NAMES[tn]}'
            boards.append(self.print_board(transform_number=tn, show_hash=show_hash, show_marks=show_marks, limit_marks=limit_marks, join_output=False))
        self.board_title = old_title

        ret.extend(_print_2(boards[0:2]))
        ret.append('')
        ret.extend(_print_2(boards[2:4]))
        ret.append('')
        ret.extend(_print_2(boards[4:6]))
        ret.append('')
        ret.extend(_print_2(boards[6:8]))
        return ret

