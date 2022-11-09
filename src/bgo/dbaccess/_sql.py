import sqlite3
from bgo.dbaccess import DBAccessException

# -----------------------------------------------------------------------------

"""
    SQL create statements for tables and indexes
"""

CREATE_PLAYER_LIST = ('CREATE TABLE IF NOT EXISTS `player_list` ('
                      '`player_id`	INTEGER PRIMARY KEY AUTOINCREMENT,'
                      '`player_name`	TEXT NOT NULL UNIQUE);')

CREATE_GAME_LIST = ('CREATE TABLE IF NOT EXISTS `game_list` ('
                    '`game_id`	INTEGER PRIMARY KEY,'
                    '`sgf_file_name`    TEXT NOT NULL,'
                    '`white_player_id`	INTEGER NOT NULL,'
                    '`white_player_rank`	INTEGER NOT NULL,'
                    '`black_player_id`	INTEGER NOT NULL,'
                    '`black_player_rank`	INTEGER NOT NULL,'
                    '`event`	TEXT,'
                    '`round`	TEXT,'
                    '`game_date`	DATE NOT NULL,'  # YYYY-MM-DD
                    '`place`	TEXT,'
                    '`komi`	TEXT,'
                    '`result`	TEXT NOT NULL,'
                    '`result_who_won`	INTEGER NOT NULL,'  # -1 = white   0 = unknown   1 = black
                    '`move_list` TEXT NOT NULL'
                    ');')

CREATE_DYER_LIST = ('CREATE TABLE IF NOT EXISTS `dyer_signatures` ('
                    '`game_id`	INTEGER NOT NULL,'
                    '`signature_a`	TEXT NOT NULL,'
                    '`signature_b`	TEXT NOT NULL,'
                    'PRIMARY KEY(`signature_a`,`signature_b`,`game_id`));')

CREATE_HASH_LIST = ('CREATE TABLE IF NOT EXISTS `hash_list` ('
                    '`board_hash`	INTEGER NOT NULL,'
                    '`game_id`	INTEGER NOT NULL,'
                    '`move_number` INTEGER NOT NULL,'
                    '`next_move` TEXT NOT NULL, ' 
                    '`game_year` INTEGER NOT NULL);')

CREATE_FINAL_BOARD_HASH_LIST = ('CREATE TABLE IF NOT EXISTS `final_board_hash` ('
                                '`board_hash`	INTEGER PRIMARY KEY,'
                                '`game_id`	INTEGER NOT NULL);')


"""
    Create statements for indexes:
        board_hash on hash_list
        move_number on hash_list
"""

CREATE_HASH_INDEX_1 = 'CREATE INDEX IF NOT EXISTS idx_hash_list ON hash_list (board_hash);'
CREATE_HASH_INDEX_2 = 'CREATE INDEX IF NOT EXISTS idx_hash_list_move_number ON hash_list (move_number);'
CREATE_HASH_INDEX_3 = 'CREATE INDEX IF NOT EXISTS idx_hash_list_game_year ON hash_list (game_year);'


# -----------------------------------------------------------------------------


def first_check_of_database(self):
    """
    Connects to the database and executes all creation statement, which will be silently ignored if tables exist.
    Returns nothing but if no exceptions raised the database is in a usable state.
    :param self:
    :return:
    :raises DBAccessException: Connection to dbaccess failed, or create statements failed.
    """
    db = self.connect_to_sql()

    try:
        with db:
            db.execute(CREATE_PLAYER_LIST)
            db.execute(CREATE_GAME_LIST)
            db.execute(CREATE_DYER_LIST)
            db.execute(CREATE_HASH_LIST)
            db.execute(CREATE_FINAL_BOARD_HASH_LIST)
            db.execute(CREATE_HASH_INDEX_1)
            db.execute(CREATE_HASH_INDEX_2)
            db.execute(CREATE_HASH_INDEX_3)
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.first_check_of_database(): SQLite Error [{e}]')


# -----------------------------------------------------------------------------


def get_database_path(self):
    """
    Returns the full path to the database file
    :param self:
    :return: String containing the full path to the database file
    """
    return self.database_path


# -----------------------------------------------------------------------------


def connect_to_sql(self):
    """
    Connect to SQLite database and return a connection object.
    If self.in_memory is True, ignore the database_path and open an in memory database.
    :param self:
    :return: sqlite3 connection to database
    :raises DBAccessException: Failure to connect to database
    """
    if self.in_memory:
        return self.memory_db_handle
    try:
        connection = sqlite3.connect(self.database_path)
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.connect_to_sql(): SQLite Error during connection to dbaccess [{e}]')
    return connection


# -----------------------------------------------------------------------------


def get_table_final_board_as_dict(self, db=None):
    """
    Loads the final_board table to a dictionary to be used as an in memory unique game check during an import.
    :param self:
    :param db: optional database handle
    :raises DBAccessException: general error
    :return: {board_hash: game_id}
    """
    if db is None:
        db = self.connect_to_sql()
    query_string = 'SELECT board_hash, game_id FROM final_board_hash'

    try:
        cursor = db.execute(query_string)
        results = cursor.fetchall()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.get_table_final_board_as_dict(): SQLite error occurred during SELECT [{e}]')
    return {board_hash: game_id for board_hash, game_id in results}


# -----------------------------------------------------------------------------

def store_dict_final_board_to_table(self, dict_final_board, db=None):
    """
    Stores the final_board dictionary to the database after an import has finished.
    :param self:
    :param dict_final_board: {board_hash: game_id} All final boards
    :param db: optional database handle
    :raises DBAccessException: general error
    :return:
    """
    if db is None:
        db = self.connect_to_sql()
    query_string = 'INSERT INTO final_board_hash (board_hash, game_id) VALUES (?, ?)'

    try:
        with db:
            db.execute('DELETE FROM final_board_hash')
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.store_dict_final_board_to_table(): SQLite error occurred during DELETE [{e}]')
    try:
        with db:
            db.executemany(query_string, dict_final_board.items())
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.store_dict_final_board_to_table(): SQLite error occurred during INSERT [{e}]')


# -----------------------------------------------------------------------------


def store_board_hash_list(self, board_hash_list, db=None):
    """
    Store the board_hash list to the database. During an import, new board hashes accumulate in memory and then are
    written out.
    :param self:
    :param board_hash_list: [(board_hash, game_id, move_number, next_move, game_year), ...] next move info
    :param db: optional db handle
    :raises DBAccessException: general error
    :return:
    """
    if db is None:
        db = self.connect_to_sql()
    query_string = 'INSERT INTO hash_list (board_hash, game_id, move_number, next_move, game_year) VALUES (?, ?, ?, ?, ?)'

    try:
        with db:
            db.executemany(query_string, board_hash_list)
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.store_board_hash_list(): SQLite error occurred during INSERT [{e}]')

    return True

# -----------------------------------------------------------------------------


def indexes_remove(self, db=None):
    """
    Remove all indexes from the hash_list table.
    :param self:
    :param db: optional db handle
    :raises DBAccessException: general error
    :return:
    """
    if db is None:
        db = self.connect_to_sql()

    try:
        db.execute('DROP INDEX idx_hash_list')
        db.execute('DROP INDEX idx_hash_list_move_number')
        db.execute('DROP INDEX idx_hash_list_game_year')
    except sqlite3.Error as e:
        raise DBAccessException(f'{__file__}.indexes_remove() - error dropping indexes [{e}]')


# -----------------------------------------------------------------------------


def indexes_add(self, db=None):
    """
    Add all indexes to the hash_list table.
    :param self:
    :param db: optional db handle
    :raises DBAccessException: general error
    :return:
    """
    if db is None:
        db = self.connect_to_sql()

    try:
        db.execute(CREATE_HASH_INDEX_1)
        db.execute(CREATE_HASH_INDEX_2)
        db.execute(CREATE_HASH_INDEX_3)
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.indexes_add() - error adding indexes [{e}]')


# -----------------------------------------------------------------------------


def get_game_count_in_database(self, db=None):
    """
    Returns an integer count of the number of games in the database.
    :param self:
    :param db: optional db handle
    :raises DBAccessException: general error
    :return: int count of games in database
    """
    if db is None:
        db = self.connect_to_sql()
    query_string = 'SELECT COUNT(*) from game_list'

    try:
        cursor = db.execute(query_string)
        result = cursor.fetchone()
    except DBAccessException as e:
        raise DBAccessException(f'DBAccess.get_game_count_in_database(): error getting game count - [{e}]')

    return result[0]
