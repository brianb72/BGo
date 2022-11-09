import sqlite3
from bgo.dbaccess import DBAccessException
import bgo.gameofgo.coordinate as Coord


# -----------------------------------------------------------------------------


def _add_new_game(self, sgf_dict, db=None):
    """
    Add a new game to the database and return the automatically assigned game_id.
    :param self:
    :param sgf_dict: Keys are column names, values data to be inserted
    :param db: Optional database handle to use
    :return: int game_id of the game that was just inserted
    :raises DBAccessException: general error
    """
    if db is None:
        db = self.connect_to_sql()

    dict_to_add = {**sgf_dict}
    dict_to_add['move_list'] = ''.join(dict_to_add['move_list'])

    col_list = ['sgf_file_name', 'white_player_id', 'white_player_rank', 'black_player_id', 'black_player_rank',
        'event', 'round', 'game_date', 'place', 'komi', 'result', 'result_who_won', 'move_list']
    col_listd = [f':{s}' for s in col_list]
    query_string = 'INSERT INTO `game_list` (' + ','.join(col_list) + ') VALUES (' + ','.join(col_listd) + ')'

    try:
        with db:
            db.execute(query_string, dict_to_add)
        cursor = db.execute('SELECT last_insert_rowid()')
        game_id = cursor.fetchone()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.add_game_and_hashes(): error adding new game [{e}]')

    if game_id is None:
        raise DBAccessException(f'DBAccess.add_game_and_hashes(): select last_insert_rowid is None')

    return game_id[0]


# -----------------------------------------------------------------------------


def _add_new_player(self, player_name, db=None):
    """
    Adds a new player to the player_list table and automatically assigns them a new integer id, which is returned.
    :param self:
    :param player_name: string full name of player to add
    :param db: optional dbaccess connection to use, open new connection if None
    :return: int player_id of newly created player
    :raises DBAccessException: general error
    """
    # Param checking and setup
    if not isinstance(player_name, str) or len(player_name) == 0:
        raise DBAccessException(f'DBAccess._add_new_player(): player_name must be a non-zero length string')
    if db is None:
        db = self.connect_to_sql()
    query_string = 'INSERT INTO player_list (player_name) VALUES (?)'

    # First insert the player
    try:
        with db:
            db.execute(query_string, (player_name,))
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess._add_new_player(): error occurred during insert [{e}]')

    # Then get the auto ID that was assigned to the new record
    try:
        cursor = db.execute('SELECT last_insert_rowid()')
        new_id = cursor.fetchone()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess._add_new_player(): error occurred checking last insert id [{e}]')

    if new_id is None or len(new_id) != 1:
        raise DBAccessException(f'DBAccess._add_new_player(): Unknown error new_id came back as None or empty')

    return new_id[0]
