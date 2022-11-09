import sqlite3
from bgo.dbaccess import DBAccessException, DBAccessLookupNotFound
from bgo.gameofgo import GameOfGo, GameOfGoException
import bgo.gameofgo.coordinate as Coord

# -----------------------------------------------------------------------------


def lookup_player_by_id(self, player_id, db=None):
    """
    Searches for a player_id and returns a string name
    :param self:
    :param player_id: int id of player to lookup
    :param db: optional dbaccess connection to use, open new connection if None
    :return: string full name of player
    :raises DBAccessException: General error during lookup
    :raises DBAccessLookupNotFound: player_id not found in dbaccess
    """
    # Param checking and setup
    if not isinstance(player_id, int):
        raise DBAccessException(f'DBAccess.lookup_player_by_id(): player_id must be int')
    if db is None:
        db = self.connect_to_sql()
    query_string = f'SELECT player_name FROM player_list WHERE player_id = {player_id}'

    # Lookup
    try:
        cursor = db.execute(query_string)
        result = cursor.fetchone()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.lookup_player_by_id(): error occurred during lookup [{e}]')

    if result is None:
        raise DBAccessLookupNotFound()
    if not isinstance(result, tuple) or len(result) != 1:
        raise DBAccessException(f'DBAccess.lookup_player_by_id(): error unexpected result [{result}]')

    return result[0]


# -----------------------------------------------------------------------------


def lookup_player_by_name(self, player_name, db=None):
    """
    Searches for a player_name and returns an integer id
    :param self:
    :param player_name: string full name of player to lookup
    :param db: optional dbaccess connection to use, open new connection if None
    :return: string full name of player
    :raises DBAccessException: General error during lookup
    :raises DBAccessLookupNotFound: player_name not found in dbaccess
    """
    if not isinstance(player_name, str) or len(player_name) == 0:
        raise DBAccessException(f'DBAccess._add_new_player(): expecting nonzero length string')
    if db is None:
        db = self.connect_to_sql()

    query_string = f'SELECT player_id FROM player_list WHERE player_name = \"{player_name}\"'
    try:
        cursor = db.execute(query_string)
        result = cursor.fetchone()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.lookup_player_by_name(): error during lookup - [{e}]')

    if result is None:
        raise DBAccessLookupNotFound()

    return result[0]


# -----------------------------------------------------------------------------


def lookup_next_move_from_moves(self, move_pair_list, db=None):
    if db is None:
        db = self.connect_to_sql()
    game = GameOfGo()
    for index, move in enumerate(move_pair_list):
        try:
            if not game.play_move(Coord.Alpha(move)):
                raise DBAccessException(f'DBAccess.lookup_next_move_from_moves(): Invalid move #{index} [{move}]')
        except GameOfGoException as e:
            raise DBAccessException(f'DBAccess.lookup_next_move_from_moves(): GameOfGoException [{e}]')
    transformed_hashes = [game.build_hash(transform_number) for transform_number in range(8)]
    return self.lookup_next_move(transformed_hashes, db=db)


# -----------------------------------------------------------------------------


def lookup_next_move(self, transformed_hashes, transform_results=True, merge_results=True, year_min=None, year_max=None, db=None):
    """

    :param self:
    :param transformed_hashes: All 8 transformed board_hashes from the position to search for
    :param transform_results: TODO for testing, remove later
    :param merge_results: TODO for testing, remove later
    :param year_min: limit search results to a minimum year inclusive
    :param year_max: limit search results to a maximum year inclusive
    :param db: optional database handle
    :raises DBAccessException: general error
    :return: [(next_move, game_count, from_transform), ...]
    """
    if db is None:
        db = self.connect_to_sql()

    '''
        Some board_hashes in transformed_hashes may be identical. Only search once when identical hashes are present.
        Create an SQL SELECT statement that searches for all unique hashes and preserve their original transform number.
    '''
    seen_hashes = set()
    queries = []
    year_filter = ''
    if year_min is not None:
        year_filter += f' AND game_year >= {year_min:d}'
    if year_max is not None:
        year_filter += f' AND game_year <= {year_max:d}'
    for transform_number, board_hash in enumerate(transformed_hashes):
        if not isinstance(board_hash, int):
            raise DBAccessException(f'DBAccess.lookup_next_move(): transformed_hashes contains non-int')
        if board_hash in seen_hashes:
            continue
        seen_hashes.add(board_hash)
        queries.append(f'SELECT next_move, count(next_move) as game_count, {transform_number:d} as from_transform FROM hash_list WHERE board_hash = {board_hash:d} {year_filter} GROUP BY next_move')

    query_string = ' UNION '.join(queries)
    try:
        cursor = db.execute(query_string)
        sql_results = cursor.fetchall()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.lookup_next_move(): error occurred during lookup [{e}]')

    if sql_results is None:
        return None

    '''
        Transform the results to the identity transform, results will contain:
            results = [(next_move, game_count, from_transform), ...]
    '''
    if transform_results:
        td = {}
        for next_move, game_count, from_transform in sql_results:
            try:
                next_move_cart = Coord.Alpha(next_move).to_cart()
            except ValueError:
                raise DBAccessException(f'DBAccess._lookup_next_move(): invalid coordinate in results [{next_move}]')
            transformed_coord = Coord.transform(next_move_cart, from_transform, invert=True)
            if transformed_coord in td:
                td[transformed_coord][1] += game_count
            else:
                td[transformed_coord] = [transformed_coord, game_count, from_transform]
        results = list(td.values())
    else:
        results = sql_results

    '''
        Board symmetries may cause some moves in results to be the same move. Merge these identical moves together
        and combine their game counts.
    '''
    if transform_results and merge_results:
        results = self._merge_next_move_data(transformed_hashes, results)

    '''
        If transform_results is True, the results list contains Cart coordinates that must be converted to
        a 2 character string. 
        If False, the results list already contains 2 character strings.
    '''
    if transform_results:
        results = [(transformed_coord.to_alpha().xy, *_) for transformed_coord, *_ in results]

    '''
        Returned the results sorted by game count from high to low.
    '''
    return sorted(results, key=lambda x: x[1], reverse=True)


# -----------------------------------------------------------------------------


def get_game_by_id(self, game_id, db=None):
    '''

    :param game_id: id of game
    :param db: optional db handle to use
    :return: { 'white_id', 'white_name', 'white_rank', 'black_id', 'black_name', 'black_rank', 'event', 'round', 'date', 'place', 'komi', 'result', 'move_list' }
    '''
    if db is None:
        db = self.connect_to_sql()

    query_string = (f"SELECT game_list.white_player_id, wplayer_list.player_name AS white_player_name, game_list.white_player_rank, "
                    f" game_list.black_player_id, bplayer_list.player_name AS black_player_name, game_list.black_player_rank, "
                    f" game_list.event, game_list.round, game_list.game_date, game_list.place, game_list.komi, game_list.result, "
                    f" game_list.move_list FROM game_list"
                    f" INNER JOIN player_list AS wplayer_list ON wplayer_list.player_id = game_list.white_player_id"
                    f" INNER JOIN player_list AS bplayer_list ON bplayer_list.player_id = game_list.black_player_id"
                    f" WHERE game_id = {game_id}")
    try:
        cursor = db.execute(query_string)
        data = cursor.fetchone()
    except sqlite3.Error as e:
        raise DBAccessException(f'DBAccess.get_game_by_id(): error looking up moves for game - [{e}]')

    if (data is not None):
        game_data = {
            'white_id': data[0],
            'white_name': data[1],
            'white_rank': data[2],
            'black_id': data[3],
            'black_name': data[4],
            'black_rank': data[5],
            'event': data[6],
            'round': data[7],
            'date': data[8],
            'place': data[9],
            'komi': data[10],
            'result': data[11],
            'move_list': data[12],
        }
    else:
        raise DBAccessException(f'DBAccess.get_game_by_id() - no results from query')

    return game_data


# -----------------------------------------------------------------------------


def get_games_for_hashes(self, list_board_hashes, limit=100, db=None):
    '''

    :param list_board_hashes: board hashes to search for
    :param limit: limit to n games returned
    :param db: optional db handle to use
    :return: [{ 'board_hash', 'game_id', 'move_number', 'next_move', 'white_id', 'white_name', 'white_rank', 'black_id', 'black_name', 'black_rank' }, ... ]
    :raises: DBAccessException
    '''
    if not isinstance(list_board_hashes, list) or len(list_board_hashes) == 0:
        raise DBAccessException(f'DBAccess.get_games_for_hashes() - Expecting list of ints')

    list_to_str = [str(hash) for hash in list_board_hashes if type(hash) == int]

    if db is None:
        db = self.connect_to_sql()

    query_string = (f"SELECT hash_list.board_hash, hash_list.game_id, hash_list.move_number, hash_list.next_move,"
                    f" game_list.white_player_id, wplayer_list.player_name AS white_player_name, game_list.white_player_rank, game_list.black_player_id, bplayer_list.player_name AS black_player_name, game_list.black_player_rank, game_list.game_date AS game_date"
                    f" FROM hash_list"
                    f" INNER JOIN game_list ON game_list.game_id = hash_list.game_id"
                    f" INNER JOIN player_list AS wplayer_list ON wplayer_list.player_id = game_list.white_player_id"
                    f" INNER JOIN player_list AS bplayer_list ON bplayer_list.player_id = game_list.black_player_id"
                    f" WHERE board_hash in ({', '.join(list_to_str)}) ORDER BY game_date DESC LIMIT {limit}")

    try:
        cursor = db.execute(query_string)
    except sqlite3.Error as e:
        raise DBAccessException(f'error building next_move_list for board_hash - [{e}]')

    result_list = []
    name_dict = {}
    for row in cursor:
        board_hash = row[0]
        game_id = row[1]
        move_number = row[2]
        next_move = row[3]
        white_id = row[4]
        white_name = row[5]
        white_rank = row[6]
        black_id = row[7]
        black_name = row[8]
        black_rank = row[9]
        game_date = row[10]

        # Find the index of board_hash in list_board_hash, which will also tell us which rotation was used for this hash
        try:
            rotation = list_board_hashes.index(board_hash)
        except ValueError:
            raise DBAccessException(f'error building next_move_list could not find hash index')

        result_list.append([game_id, move_number, next_move, rotation, white_id, white_rank, black_id, black_rank])
        name_dict[white_id] = white_name
        name_dict[black_id] = black_name

    return { 'names': name_dict, 'games': result_list }