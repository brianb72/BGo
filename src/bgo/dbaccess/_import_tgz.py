import os
import tarfile
from bgo.dbaccess import DBAccessException, DBAccessLookupNotFound
from bgo.dbaccess.sgf_wrapper import SGFWrapper, SGFWrapperException
from bgo.gameofgo import GameOfGo, GameOfGoException
from datetime import datetime
import bgo.gameofgo.coordinate as Coord
from multiprocessing import Pool
from enum import IntEnum
from bgo.gameofgo.gostone import StoneColor


class BuildReturn(IntEnum):
    """
    Return values for game building
    """
    SUCCESS = 1             # Game successfully added
    PARSE_ERROR = -1        # SGFGame.import_from_sgf_string() failed to parse
    IMPORT_REJECTED = -2    # SGFGame.is_valid_for_database_import() returned False
    INVALID_MOVE = -3       # GameOfGo reports invalid move: off board, top of existing, ko, self capture
    DUPLICATE = -4          # Database unique game check failed, already in database


# -----------------------------------------------------------------------------

def import_games_from_tgz(self, path_to_tgz, db=None):
    """
    Given the path to a tgz containing sgf game records, parse and import all games.
    :param self:
    :param path_to_tgz: Path and filename to tgz containing game records
    :param db: optional database handle
    :return:
    :raises DBAccessException: general error
    """
    if db is None:
        db = self.connect_to_sql()
    stats = dict(
        sgf_parse_error=0,     # Failure of SGFGame to parse game
        sgf_rejected=0,        # Rejected by SGFGame.is_valid_for_import()
        sgf_duplicate=0,       # Game already exists in database and was skipped
        sgf_invalid_move=0,    # Invalid move while building position
        sgf_added=0,           # Successfully added to database
        sgf_exception=0,       # Exception occurred processing batch list and adding game, game not added
    )
    try:
        tar = tarfile.open(path_to_tgz, 'r:gz')
    except OSError as e:
        raise DBAccessException(f'DBAccess.import_games_from_tgz(): Could not open tgz [{e}]')

    # Get the total number of files in tgz, may include non-SGF
    number_of_files_in_tgz = sum(1 for member in tar if member.isreg())
    processed_files = 0

    # Load the final board table from the database to a dictionary, to test if games being imported already exist in db
    final_board_dict = self.get_table_final_board_as_dict(db)

    # Process each file in the archive, ignoring files that do not have an SGF extension
    last_time = datetime.now()
    sgf_list = []
    board_hash_list = []
    pool = Pool()
    print(f'Importing {path_to_tgz} with {number_of_files_in_tgz} files...')
    time_start = datetime.now()
    with db:
        for tarinfo in tar:
            processed_files += 1
            if processed_files % self.DISPLAY_MESSAGE_COUNT == 0:
                now_time = datetime.now()
                elapsed_time = now_time - last_time
                last_time = now_time
                print(f'...Loaded {processed_files} / {number_of_files_in_tgz} ({processed_files / number_of_files_in_tgz * 100:.0f}%) ({elapsed_time})')
            _, extension = os.path.splitext(tarinfo.name)
            if extension.lower() != '.sgf':
                continue

            # Add the data to the list
            tar_reader = tar.extractfile(tarinfo)
            sgf_list.append(dict(
                raw_text=tar_reader.read().decode('utf-8'),
                file_name=tarinfo.name,
                num_hashes=self.NUM_OF_MOVES_FOR_HASHES,
            ))

            # Should we process?
            if len(sgf_list) > self.PROCESS_GAME_BATCH_SIZE:
                batch_list = build_games(pool, sgf_list)
                self._process_batch_list(db, stats, final_board_dict, board_hash_list, batch_list)
                sgf_list = []

        # Finished reading tar, if anything left on the sgf_list process it
        if len(sgf_list) > 0:
            batch_list = build_games(pool, sgf_list)
            self._process_batch_list(db, stats, final_board_dict, board_hash_list, batch_list)
            sgf_list = []

    self.store_dict_final_board_to_table(final_board_dict, db)
    print(f'Wrote final position dictionary...')

    self.store_board_hash_list(board_hash_list, db)
    print(f'Wrote board hashes...')

    time_stop = datetime.now()
    print(f'Finished import in {time_stop - time_start}')

    print(f'Processed {processed_files} files...')
    print(f'   {stats["sgf_parse_error"]} parse errors')
    print(f'   {stats["sgf_rejected"]} rejected for import')
    print(f'   {stats["sgf_duplicate"]} already in database')
    print(f'   {stats["sgf_invalid_move"]} have invalid moves')
    print(f'Added {stats["sgf_added"]} files.')


def _process_batch_list(self, db, stats, final_board_dict, board_hash_list, batch_list, output=True):
    """
    Processes batch_list, which is a list of prebuilt games. Add games to database that build successfully and
    pass the requirements.
    :param self:
    :param db: database handle
    :param stats: dictionary containing stats of build results
    :param final_board_dict: board_hashes of all final boards in database for unique checks
    :param board_hash_list: all board_hashes for processed games
    :param batch_list: list of results from game building
    :param output: bool should output be printed to screen?
    :raises DBAccessException: general error
    :return:
    """
    for batch in batch_list:
        build_result = batch['build_result']
        sgf_file_name = batch['sgf_file_name']
        sgf_why_invalid = batch['sgf_why_invalid']

        # Test the game for the three basic failures during building
        if build_result == BuildReturn.PARSE_ERROR:
            if output:
                print(f'   Parse error: [{sgf_why_invalid}] {sgf_file_name} ')
            stats['sgf_parse_error'] += 1
            continue
        elif build_result == BuildReturn.IMPORT_REJECTED:
            if output:
                print(f'   Rejected for import: [{sgf_why_invalid}] {sgf_file_name}')
            stats['sgf_rejected'] += 1
            continue
        elif build_result == BuildReturn.INVALID_MOVE:
            if output:
                print(f'   Rejected for invalid move: [{sgf_why_invalid}] {sgf_file_name}')
            stats['sgf_invalid_move'] += 1
            continue
        elif build_result != BuildReturn.SUCCESS:  # Never
            raise DBAccessException(f'DBAccess._process_batch_list(): Unknown BuildReturn [{build_result}]')

        # At this point the game is valid for import, duplicate check
        final_board_hash = batch['final_board_hash']
        if final_board_hash in final_board_dict:
            if output:
                print(f'   Already in database as game_id [{final_board_dict[final_board_hash]}]: {sgf_file_name}')
            stats['sgf_duplicate'] += 1
            continue

        # Game is not a duplicate and is ready to be added to database.
        # First convert the player names to ids
        black_player_name = batch['black_player_name']
        white_player_name = batch['white_player_name']
        try:
            try:
                batch['black_player_id'] = self.lookup_player_by_name(black_player_name, db)
            except DBAccessLookupNotFound:
                batch['black_player_id'] = self._add_new_player(black_player_name, db)
            try:
                batch['white_player_id'] = self.lookup_player_by_name(white_player_name, db)
            except DBAccessLookupNotFound:
                batch['white_player_id'] = self._add_new_player(white_player_name, db)
        except DBAccessException as e:
            raise DBAccessException(f'DBAccess._process_batch_list(): error trying to lookup or add names for game {sgf_file_name} [{e}]')
        # Then add the game
        try:
            new_game_id = self._add_new_game(batch, db)
        except DBAccessException as e:
            print(f'DBAccess._process_batch_list(): error while adding game [{sgf_file_name}] [{e}]')
            stats['sgf_exception'] += 1
            continue

        try:
            game_year = datetime.strptime(batch['game_date'], '%Y-%m-%d').year
        except (TypeError, ValueError):
            print(f'DBAccess._process_batch_list(): Error parsing date for {sgf_file_name} [{batch["game_date"]}]')
            stats['sgf_exception'] += 1
            continue

        # Add the empty board hash to the hash list, and then add each moves hash.
        try:
            board_hash_list.append((0, new_game_id, 0, batch['move_list'][0], game_year))
            for index, board_hash in enumerate(batch['board_hashes']):
                board_hash_list.append((
                    board_hash,
                    new_game_id,
                    index + 1,
                    batch['move_list'][index+1],
                    game_year
                ))
        except IndexError:
            # At this stage new players may have been added to the database from a game we rejected, but this shouldn't
            # be a problem.
            print(f'DBAccess._process_batch_list(): Index error while adding hashes for game {sgf_file_name}')
            stats['sgf_exception'] += 1
            continue

        # Game has been added to the database, add to duplicate_dict
        final_board_dict[final_board_hash] = new_game_id
        stats['sgf_added'] += 1


def _build_game(work):
    """
    The multiprocessing pool passes each game to _build_game() for building. The SGF is parsed and checked for errors,
    the moves are placed on a board, and the board_hashes are generated. The return is a dictionary that can be added
    to the batch_list of built games, and that batch_list will later be processed by _process_batch_list() and added
    to the database.
    :param work: {'raw_text', 'file_name', 'num_hashes'} raw sgf text and file name to be built
    :return: result dictionary
    """
    sgf_raw_text = work['raw_text']
    sgf_file_name = work['file_name']
    num_hashes = work['num_hashes']

    # Wrap the raw text in an SGFWrapper
    try:
        sgf_game = SGFWrapper(sgf_file_text=sgf_raw_text, sgf_file_name=sgf_file_name)
    except SGFWrapperException as e:
        return dict(build_result=BuildReturn.PARSE_ERROR, sgf_file_name=sgf_file_name, sgf_why_invalid=f'SGFWrapper Error [{e}]')

    # Does the game pass the tests for insertion?
    try:
        if not sgf_game.is_valid_for_database_import():
            return dict(build_result=BuildReturn.IMPORT_REJECTED, sgf_file_name=sgf_file_name, sgf_why_invalid=sgf_game.why_invalid,)
    except SGFWrapperException as e:
        return dict(build_result=BuildReturn.PARSE_ERROR, sgf_file_name=sgf_file_name, sgf_why_invalid=f'SGFWrapper Error [{e}]')

    # Make a GameOfGo and play the sgf_game moves onto it, building hashes and final hash
    game_board_hashes = []
    game = GameOfGo()
    for index, move in enumerate(sgf_game.move_pair_list):
        try:
            if not game.play_move(Coord.Alpha(move)):
                return dict(build_result=BuildReturn.INVALID_MOVE, sgf_file_name=sgf_file_name, sgf_why_invalid=sgf_game.why_invalid)
        except GameOfGoException:
            return dict(build_result=BuildReturn.INVALID_MOVE, sgf_file_name=sgf_file_name, sgf_why_invalid=sgf_game.why_invalid)
        if index < num_hashes:
            game_board_hashes.append(game.build_hash())

    return dict(
        build_result=BuildReturn.SUCCESS,
        sgf_file_name=sgf_file_name,
        sgf_why_invalid=sgf_game.why_invalid,
        white_player_name=sgf_game.get_player_name(StoneColor.WHITE),
        white_player_rank=sgf_game.get_player_rank(StoneColor.WHITE),
        black_player_name=sgf_game.get_player_name(StoneColor.BLACK),
        black_player_rank=sgf_game.get_player_rank(StoneColor.BLACK),
        event=sgf_game.tag_dict['EV'].strip(),
        round=sgf_game.tag_dict['RO'].strip(),
        game_date=sgf_game.get_date(),
        place=sgf_game.tag_dict['PC'].strip(),
        komi=sgf_game.tag_dict['KM'].strip(),
        result=sgf_game.tag_dict['RE'].strip(),
        result_who_won=sgf_game.get_who_won(),
        move_list=sgf_game.move_pair_list,
        board_hashes=game_board_hashes,
        final_board_hash=game.build_hash()
    )


def build_games(pool, sgf_list):
    """
    Build all games in sgf_list using a multiprocessing pool, return a batch_list that can be processed and inserted.
    :param pool: multiprocessing pool to use
    :param sgf_list: {raw_text, file_name, num_hashes}
    :return: List of dictionaries of built game results
    """
    batch_list = []
    for result in pool.imap_unordered(_build_game, sgf_list):
        batch_list.append(result)
    return batch_list





