"""
    GameOfGo


    Notes:
        self.board[:] = StoneColor.NONE     # Set entire board to NONE
        new_board = np.zeros_like(self.board)   # Create a new board of same dimensions, all values 0

"""

import numpy as np
from bgo.gameofgo.gostone import StoneColor, invert_color, color_char
import bgo.gameofgo.coordinate as Coord
from bgo.gameofgo.hashdata import BOARD_HASH_VALUES


class GameOfGoException(Exception):
    """Raise whenever GameOfGo has an error or exception"""


class GameOfGo(object):
    """
        GameOfGo provides all the logic needed to play moves on a 19x19 board and run the rules of Go
    """
    def __init__(self):
        self.board = None
        self.stone_coord_set = None
        self.last_board = None
        self.move_list = None
        self.why_invalid = None
        self.reset_position()

    # -----------------------------------------------------------------------------

    def reset_position(self):
        """
        Resets the game to an empty position with no moves.

        :return:
        """
        self.board = np.array([[StoneColor.NONE for x in range(19)] for y in range(19)])
        self.stone_coord_set = set()
        self.last_board = None
        self.move_list = []
        self.why_invalid = None

    # -----------------------------------------------------------------------------

    def get_next_color_to_play(self):
        """
        Returns the StoneColor of the next color that should be played.

        :return: StoneColor of next move
        """
        if len(self.move_list) % 2 == 0:
            return StoneColor.BLACK
        else:
            return StoneColor.WHITE

    # -----------------------------------------------------------------------------

    def build_groups(self):
        """
        Builds a list of all groups on the board, the stones in the groups, and their free liberty counts

        :return: [ { 'color': StoneColor, 'liberties': int, 'stones': [ (Cart), ...] }, ... ]
        """
        walked = set()
        groups = []

        # Walk all stones on the board
        for coord in self.stone_coord_set:
            if coord in walked:
                continue
            walked.add(coord)

            # Start a new group
            group_color = self.board[coord.y][coord.x]
            group_liberty_coords = set()
            coords_to_walk = list(Coord.neighbor_list(coord))
            group = {
                'color': group_color,
                'liberties': 0,
                'stones': [coord],
            }

            # Repeatedly walk to neighboring same color stone coordinates until done, discovering unique liberties
            while len(coords_to_walk) > 0:
                walk = coords_to_walk.pop()
                if walk in walked:
                    continue
                if self.board[walk.y][walk.x] == 0:
                    group_liberty_coords.add(walk)
                    continue
                elif self.board[walk.y][walk.x] != group_color:
                    continue
                walked.add(walk)
                group['stones'].append(walk)
                coords_to_walk.extend(Coord.neighbor_list(walk))

            # Set the discovered liberty count of the group and add it to known groups
            group['liberties'] = len(group_liberty_coords)
            groups.append(group)

        # After all stones have been walked, return discovered groups
        return groups

    # -----------------------------------------------------------------------------

    def load_moves(self, move_list):
        """
        Resets the current position, and plays all moves in move_list to the board.
        If the moves are accepted, return True and the position is valid.
        If any of the moves are invalid, return False and the position should not be used.
        :param move_list:
        :return: True if moves accepted, false if any errors.
        """
        self.reset_position()
        try:
            for move in move_list:
                if not self.play_move(move):
                    return False
        except GameOfGoException:
            return False
        return True

    # -----------------------------------------------------------------------------

    def play_move(self, any_coord):
        """
        Plays a move on the board and returns if it was accepted. If the move was rejected, the board is unchanged.
           TODO The exception will only raise if there is already an invalid color stone on the board before this
              call. It should never happen, but if it does, just returning False will hide this invalid state. Is there
              a better way of dealing with this that doesn't require the raising of an exception?
        :param any_coord: valid Alpha or Cart coordinate
        :return: True if move accepted, false if any errors.
        :raises GameOfGo: Only raised if there is a pre-existing stone on the board of an unknown color.
        """
        # Convert coordinate to cart if needed
        coord = Coord.to_cart(any_coord)
        if not Coord.is_valid(coord):
            self.why_invalid = f'Coordinate to play is invalid [{coord}]'
            return False

        if self.board[coord.y][coord.x] != 0:
            self.why_invalid = f'Stone already exists at {coord}'
            return False

        # Prepare a copy of the original board that can be reverted to if the move is found to be invalid
        orig_board = np.copy(self.board)

        # Add the move to the board, create a list of groups
        cur_color = self.get_next_color_to_play()
        other_color = 0
        if cur_color == 1:
            other_color = 2
        elif cur_color == 2:
            other_color = 1

        self.board[coord.y][coord.x] = cur_color
        self.stone_coord_set.add(coord)
        groups = self.build_groups()

        # Count the number of same colored captured stones, and different colored captured stones
        captured_same_color = 0
        captured_diff_color = 0

        for group in groups:
            if group['liberties'] == 0:
                if group['color'] == cur_color:
                    captured_same_color += 1
                elif group['color'] == other_color:
                    captured_diff_color += 1
                else:
                    raise GameOfGoException(f'DBAccess:play_move(): Group has unknown color {group["color"]}')

        # Check for self capture: If any same color groups are zero liberties, then this move must capture one or
        # more diff color groups, which will create liberties for the same color group and avoid self capture.
        if captured_same_color > 0 and captured_diff_color == 0:
            # This move causes self capture, revert to the original board and report invalid move
            self.board = orig_board
            self.stone_coord_set.remove(coord)
            self.why_invalid = f'Self capture at {coord}'
            return False

        # Remove opposite colored stones from the board, and create a set of stones that were removed
        to_remove_from_set = []
        for group in groups:
            if group['color'] == other_color and group['liberties'] == 0:
                for remove_coord in group['stones']:
                    self.board[remove_coord.y][remove_coord.x] = 0
                    to_remove_from_set.append(remove_coord)

        # Check for Ko, if last board is the same as current board the position repeated with an illegal Ko
        if self.last_board is not None and np.array_equal(self.last_board, self.board):
            self.board = orig_board
            self.stone_coord_set.remove(coord)
            self.why_invalid = f'Illegal ko at {coord}'
            return False

        # Move is valid, orig_board becomes last_board, update stone_coord_set and move_list
        self.last_board = orig_board
        for remove_coord in to_remove_from_set:
            self.stone_coord_set.remove(remove_coord)
        self.stone_coord_set.add(coord)
        self.move_list.append(coord)

        # Success, move was accepted
        self.why_invalid = None
        return True

    # -----------------------------------------------------------------------------

    def build_hash(self, use_transform=0):
        """
        Returns a hash for the current position, optionally rotated by use_transform. Current position is not modified.

        :param use_transform: use the int transform number to calculate the hash
        :return: int board hash
        :raises ValueError: If use_transform is not int or outside 0-7, or if any coord is invalid (should not happen)
        """
        board_hash = 0
        for board_coord in self.stone_coord_set:
            if use_transform > 0:
                hash_coord = Coord.transform(board_coord, use_transform)
            else:
                hash_coord = board_coord
            if self.board[board_coord.y][board_coord.x] == 1:  # StoneColor.BLACK:
                board_hash += BOARD_HASH_VALUES[hash_coord.y * 19 + hash_coord.x]
            elif self.board[board_coord.y][board_coord.x] == 2:  # StoneColor.WHITE
                board_hash -= BOARD_HASH_VALUES[hash_coord.y * 19 + hash_coord.x]
        return board_hash

