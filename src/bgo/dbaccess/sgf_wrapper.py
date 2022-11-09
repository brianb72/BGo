"""
    Wraps an SGF file in a class named SGFWrapper, decodes fields, provides accessor functions.
        * Imports from a string containing a complete SGF record
        * Parsing done using the PyGO SGF package
        * Important fields are extracted to a dictionary

    DBAccess can directly import an SGFWrapper

    Format of rank integers returned by get_player_rank():
        -30 = 30 kyu
         -1 = 1 kyu
          0 = Invalid Rank / Unranked Player / Unknown Title
          1 = 1 dan
          9 = 9 dan

    TODO Many games on gokifu have syntax errors, but usually only one problem per file. Examples:
    ...;B[dn];W[el];B[bn]);B[io];W[hp];B[kc])       Missing white move near end of game, extra ) in move nodes
    ...RE[W+R]PB[Wu Guangya]BR[8p]PW[Fan Yin]WR[9p]GK[1]TC[]];B[pd];W[dp];...    Extra ] after TC[] tag
    TODO Try to write a preprocessor that removes syntax errors so the file is parsable.

"""

import sgf
import re

import bgo.gameofgo.gostone as GoStone

# -----------------------------------------------------------------------------


class SGFWrapperException(Exception):
    """Raise whenever SGFWrapper has an error or exception"""


class SGFWrapper(object):
    def __init__(self, sgf_file_text, sgf_file_name=None):
        """
        Wraps an SGF records file, decodes and provides access to important fields.
        :param sgf_file_text: string contents of sgf records file
        :param sgf_file_name: string file name of sgf record
        :raises SGFWrapperException: Error processing sgf_file_text, game is not valid, why_invalid contains reason.
        """
        # Setup and param checking
        self.tag_dict = {
            'SZ': '',   # size of the board     '19'
            'HA': '',   # Handicap stones       '2'
            'PW': '',   # name of white         'Kimu Sujun'
            'WR': '',   # white rank            '8d'
            'PB': '',   # name of black         'Yamashita Keigo'
            'BR': '',   # black rank            '9d'
            'EV': '',   # event                 '33rd Tengen'
            'RO': '',   # round                 'Semi-final'
            'DT': '',   # date                  '2007-07-19'
            'PC': '',   # place                 'Nihon Ki-In, Tokyo'
            'KM': '',   # komi                  '6.5'
            'RE': '',   # result                'B+R'
        }
        self.tag_key_list = self.tag_dict.keys()
        self.sgf_file_name = sgf_file_name
        self.move_pair_list = []
        self.why_invalid = None
        self._extracted_date = None
        self._who_won = None

        if not isinstance(sgf_file_text, str) or len(sgf_file_text) == 0:
            raise SGFWrapperException(f'SGFWrapper.__init__(): sgf_file_text must be a non-zero length string')

        # Parse the text using the PyGo SGF package
        # TODO Find out what causes UnboundLocalError when parsing some files
        try:
            game_collection = sgf.parse(sgf_file_text)
        except sgf.ParseException as e:
            raise SGFWrapperException(f'SGFWrapper.__init__(): parse error of SGF record [{e}]')
        except UnboundLocalError as e:
            raise SGFWrapperException(f'SGFWrapper.__init__(): parse error of SGF record (UnboundLocalError) [{e}]')

        move_number = 1
        last_move_color = GoStone.StoneColor.WHITE
        try:
            # Walk the nodes
            node = game_collection[0].root
            while node is not None:
                # Extract any tags that are in the tag_dict
                for k, v in node.properties.items():
                    k = k.upper()
                    if k in self.tag_key_list:
                        self.tag_dict[k] = v[0]
                # Look for a black or white move in this node, if none skip to the next node
                if 'B' not in node.properties and 'W' not in node.properties:
                    node = node.next
                    continue
                # Process the move and add it to the move list
                color_letter = 'B' if last_move_color == GoStone.StoneColor.WHITE else 'W'
                if color_letter not in node.properties:
                    raise SGFWrapperException(f'SGFWrapper.__init__(): parse error of SGF record [Move order error, expecting {color_letter} stone move #{move_number}]')
                node_len = len(node.properties[color_letter][0])
                if node_len == 2:
                    self.move_pair_list.append(node.properties[color_letter][0].lower())
                elif node_len == 0:  # A small number of games have a blank move to indicate a pass
                    self.move_pair_list.append('tt')
                else:
                    raise SGFWrapperException(f'SGFWrapper.__init__(): parse error of SGF record [Invalid move #{move_number}]')
                # Advance the node
                last_move_color = GoStone.invert_color(last_move_color)
                node = node.next
                move_number += 1
        except IndexError:
            raise SGFWrapperException(f'SGFWrapper.__init__(): parse error of SGF record [Index error while processing move #{move_number}]')

    # -------------------------------------------------------------------------

    def is_valid_for_database_import(self):
        self.why_invalid = None

        # Both players must have valid names
        if len(self.tag_dict['PB']) == 0 or len(self.tag_dict['PW']) == 0:
            self.why_invalid = f'One or both players has blank name'
            return False

        # Must have a valid date
        try:
            self.get_date()
        except SGFWrapperException:
            self.why_invalid = f'Invalid "date" field'
            return False

        # Must not be a handicap game, if 'HA' tag is a non-number assume invalid
        try:
            if len(self.tag_dict['HA']) > 0:
                ha = int(self.tag_dict['HA'])
                if ha != 0:
                    self.why_invalid = 'Handicap game'
                    return False
        except ValueError:
            self.why_invalid = 'Invalid Handicap'
            return False

        # Must have at least 30 moves
        if len(self.move_pair_list) < 30:
            self.why_invalid = 'Less than 30 moves'
            return False

        # Game board size must be 19x19
        try:
            sz = int(self.tag_dict['SZ'])
            if sz != 19:
                self.why_invalid = 'Not 19x19 (sz)'
                return False
        except (TypeError, ValueError):
            '''
                Many games from BadukMovies do not have an SZ tag, or the SZ is a nonstandard value.
                A 13x13 has a maximum move of 'm', if the move list contains a move 'n' or greater the game is a 19x19.
                Remember to ignore move 'tt' for a pass. 
            '''
            found_19x19 = False
            for move in self.move_pair_list:
                x, y = move.lower()
                if (x != 't' and x > 'm') or (y != 't' and y > 'm'):
                    found_19x19 = True
                    break
            if not found_19x19:
                self.why_invalid = "Not 19x19 (discovered)"
                return False

        # Check the ranks
        '''
                Some ranks are non-standard like WR[Kisung] for a title holder.
                Only reject games that have a kyu player
                Accept games with dan players or undecodable ranks
                TODO Many gokifu games have blank rank fields, should these games be included or rejected?
        '''
        if self.get_player_rank(GoStone.StoneColor.BLACK) < 0 or self.get_player_rank(GoStone.StoneColor.WHITE) < 0:
            self.why_invalid = 'Kyu rank'
            return False

        # Check for invalid coordinates on the move list
        for index, move in enumerate(self.move_pair_list):
            x, y = move.lower()
            if not 'a' <= x <= 't' or not 'a' <= y <= 't':
                self.why_invalid = 'Invalid coordinates in moves'
                return False
            if index < 30 and (x == 't' or y == 't'):
                self.why_invalid = 'Pass within first 30 moves'
                return False

        # Success, game can be inserted
        return True

    # -------------------------------------------------------------------------

    def get_date(self):
        """
        Decodes the tag_dict['DT'] field into a string of format 'YYYY-MM-DD'
            If the month or day are missing, the value 1 is used
                '2005' becomes '2005-01-01' and '2005-07' becomes '2005-07-01'
        :return: string 'YYYY-MM-DD', and field self.extracted_date is set
        :raises SGFWrapperException: undecodable date field
        """
        if self._extracted_date is None:
            # TODO regex to do this in one expression, handle unexpected data
            match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', self.tag_dict['DT'])
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
            else:
                match = re.search(r'(\d{4})-(\d{1,2})', self.tag_dict['DT'])
                if match:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = 1
                else:
                    match = re.search(r'(\d{4})', self.tag_dict['DT'])
                    if match:
                        year = int(match.group(1))
                        month = 1
                        day = 1
                    else:
                        raise SGFWrapperException(f'SGFWrapper.__init__(): parse error on SGF record "date" field')
            self._extracted_date = f'{year:04}-{month:02}-{day:02}'
        return self._extracted_date

    # -------------------------------------------------------------------------

    def get_who_won(self):
        """
        Determine which player won by decoding the 'RE' tag
        :return: StoneColor of player who won, or NONE if winner could not be determined
        """
        if self._who_won is None:
            if 'b' in self.tag_dict['RE'].lower():
                self._who_won = GoStone.StoneColor.BLACK
            elif 'w' in self.tag_dict['RE'].lower():
                self._who_won = GoStone.StoneColor.WHITE
            else:
                self._who_won = GoStone.StoneColor.NONE
        return self._who_won

    # -------------------------------------------------------------------------

    @staticmethod
    def _convert_rank_string_to_integer(rank_string):
        """
        Convert a rank_string containing '4k' or '5D' to an integer value. Returns 0 if rank cannot be decoded.
        TODO should blank rank strings be accepted or rejected?
        :param rank_string: '9d'
        :return: int 9
        :raises SGFWrapperException: invalid params
        """
        if not isinstance(rank_string, str) or len(rank_string) == 0:
            raise SGFWrapperException(f'SGFWrapper._convert_rank_string_to_integer(): rank_string must be non-zero length string')

        '''
            Strategy: Walk the string until finding the first letter and call that rank_letter. Split the string
                and call the block before rank_letter the numeric part. Try to convert the numeric part to an int.
                Throw away strings that have letters other than 'p', 'd', or 'k', or undecodable numerics.
            TODO: Convert to a regex 
        '''
        for rank_char in rank_string.lower():
            if rank_char.isalpha():
                try:
                    numeric_as_text = rank_string.split(rank_char, 1)[0].strip()
                except IndexError:
                    return 0
                try:
                    numeric_rank = int(numeric_as_text)
                except ValueError:
                    return 0
                if rank_char == 'd' or rank_char == 'p':
                    # Allow dan rank 10 just in case any records have it for a title holder, consider it valid
                    if numeric_rank < 1 or numeric_rank > 10:
                        return 0
                    return numeric_rank
                if rank_char == 'k':
                    if numeric_rank < 1 or numeric_rank > 30:
                        return 0
                    return -numeric_rank
                else:
                    return 0
        return 0

    # -------------------------------------------------------------------------

    def get_player_rank(self, stone_color):
        """
        Decodes the rank field for the stone_color player
        :param stone_color: StoneColor of player to get rank
        :return: int Rank of player from -30 to 9, with 0 being an undecodable rank.
        :raises SGFWrapperException: invalid stone_color, or StoneColor.NONE
        """
        if not isinstance(stone_color, GoStone.StoneColor):
            raise SGFWrapperException(f'SGFWrapper.get_player_rank(): stone_color must be type StoneColor')

        if stone_color == GoStone.StoneColor.BLACK:
            return self._convert_rank_string_to_integer(self.tag_dict['BR'])
        elif stone_color == GoStone.StoneColor.WHITE:
            return self._convert_rank_string_to_integer(self.tag_dict['WR'])
        else:
            raise SGFWrapperException(f'SGFWrapper.get_player_rank(): stone_color must be StoneColor.BLACK or StoneColor.WHITE')

    # -------------------------------------------------------------------------

    def get_player_name(self, stone_color):
        """
        Gets the name field for the stone_color player
        :param stone_color: StoneColor of player to get name
        :return: string name of the stone_color player
        """
        if not isinstance(stone_color, GoStone.StoneColor):
            raise SGFWrapperException(f'SGFWrapper.get_player_name(): stone_color must be type StoneColor')

        if stone_color == GoStone.StoneColor.BLACK:
            return self.tag_dict['PB']
        elif stone_color == GoStone.StoneColor.WHITE:
            return self.tag_dict['PW']
        else:
            raise SGFWrapperException(f'SGFWrapper.get_player_name(): stone_color must be StoneColor.BLACK or StoneColor.WHITE')

