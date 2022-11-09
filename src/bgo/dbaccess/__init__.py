import sqlite3

# -----------------------------------------------------------------------------


class DBAccessException(Exception):
    """An unexpected and serious error while accessing the dbaccess"""


class DBAccessLookupNotFound(Exception):
    """A game record or player lookup returned nothing"""


class DBAccessDuplicate(Exception):
    """A game record or player that is being added already exists in the dbaccess"""


class DBAccessGameRecordError(Exception):
    """A game record that is being parsed had invalid format, invalid data, or illegal moves"""
    
    
# -----------------------------------------------------------------------------

class DBAccess(object):
    DISPLAY_MESSAGE_COUNT = 1000     # When importing games, display a progress update every N games processed
    NUM_OF_MOVES_FOR_HASHES = 30    # How many moves should board hashes be generated for?
    PROCESS_GAME_BATCH_SIZE = 1000    # Build n games in parallel when importing
    from bgo.dbaccess._sql import first_check_of_database, get_database_path, connect_to_sql, get_game_count_in_database
    from bgo.dbaccess._sql import get_table_final_board_as_dict, store_dict_final_board_to_table, store_board_hash_list
    from bgo.dbaccess._adding import _add_new_player, _add_new_game
    from bgo.dbaccess._lookup import lookup_player_by_name, lookup_player_by_id
    from bgo.dbaccess._lookup import lookup_next_move, lookup_next_move_from_moves, get_games_for_hashes, get_game_by_id
    from bgo.dbaccess._import_tgz import import_games_from_tgz, _process_batch_list
    from bgo.dbaccess._merge_next_move import _merge_next_move_data

    # -------------------------------------------------------------------------

    def __init__(self, database_path, in_memory=False):
        self.database_path = database_path
        self.in_memory = in_memory
        if in_memory:
            self.memory_db_handle = sqlite3.connect(':memory:')
        self.first_check_of_database()
