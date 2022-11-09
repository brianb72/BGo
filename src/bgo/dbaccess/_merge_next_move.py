"""
Search Process
    User creates a GoBoard() object and adds moves to build a position to search for.
    A list of 8 board_hashes is created from the search GoBoard(), one for each of the 8 transformations possible.
    The board_hash table is searched for all 8 of these hashes.
    Results are generated in a list of tuples:
        results = [(next_move, game_count, from_transform), ...]

    (if transform _results) All next_move in results are transformed to the identity transform.
    (if merge_results) All next_move in result that are equivalent due to symmetries are combined.
"""

from bgo.dbaccess import DBAccessException
import bgo.gameofgo.coordinate as Coord


def _merge_next_move_data(self, transformed_hashes, results):
    """
    Symmetries may exist in the moves in results, causing two or more moves to be equivalent. Find these equivalent
    moves, combine them according to bias rules in the coordinate class, and return the merged move data.
    :param self:
    :param transformed_hashes: List of 8 integer board_hashes from original search GoBoard()
    :param results: [(next_move, game_count, from_transform), ...]
    :raises DBAccessException: general error
    :return: [(merged_next_move, merged_game_count, merged_from_transform), ...]
    """
    if not isinstance(results, list):
        raise DBAccessException(f'DBAccess._merge_next_move_data(): expecting list of tuples for next move data')
    if not isinstance(transformed_hashes, list) or len(transformed_hashes) != 8:
        raise DBAccessException(f'DBAccess._merge_next_move_data(): expecting list of 8 ints for transformed_hashes')
    if len(results) == 0:
        return []

    '''
        If there are coordinates to merge, one or more hashes in transformed_hashes will match the identity transform.
        Determine if there are matching_transforms, and if not return the original results list.
    '''
    matching_transforms = [transform_number for transform_number, board_hash in enumerate(transformed_hashes)
                           if transform_number > 0 and board_hash == transformed_hashes[0]]
    if len(matching_transforms) == 0:
        return results

    '''
        Convert results to a dictionary where the key is next_move and the value is the entire row.
        As an error check, the dictionary len must match the list len or there are duplicate coordinates in the results. 
    '''
    results_dict = {row[0]: row for row in results}
    if len(results_dict) != len(results):
        raise DBAccessException(f'DBAccess._merge_next_move_data(): internal error, results data has duplicate coordinates')

    '''
        Special Case Check:
        If all board_hashes on transformed_hashes are the same, the original search board was from an empty board or
        a board with a single black stone in the center intersection. (tengen point) This is a special case and will 
        have next_move results scattered over the board.
        
        For this special case: 
            Transform all moves to the upper right quad of the board
            Set matching_transforms = [7] which is the transform number to combine symmetries that exist in the upper 
            right quad, then fall through to the merge loop..
    '''

    if len(matching_transforms) == 7:
        merge_dict = {}
        for next_move, game_count, *_ in results_dict.values():
            to_upper_right = Coord.which_transform_to_move_to_upper_right(next_move)
            upper_right_coord = Coord.transform(next_move, to_upper_right)
            if upper_right_coord in merge_dict:
                merge_dict[upper_right_coord] = (upper_right_coord,  merge_dict[upper_right_coord][1] + game_count, 0)
            else:
                merge_dict[upper_right_coord] = (upper_right_coord,  game_count, 0)
        results_dict = merge_dict
        matching_transforms = [7]

    '''
        Combine symmetrical moves for each transform, overwriting results_dict with each merge, until all merges
        are finished and result_dict contains the fully merged next_move data.
    '''
    for transform_number in matching_transforms:
        merge_dict = {}
        coord_pair_set = set()
        for next_move, game_count, *_ in results_dict.values():
            # Find the symmetrical move for this transform, if it's the same move just copy the data
            sym_next_move = Coord.transform(next_move, transform_number, invert=True)
            if next_move == sym_next_move:
                merge_dict[next_move] = (next_move, game_count)
                continue

            # Check if this move combination has been processed in either order, if so continue
            if (next_move, sym_next_move) in coord_pair_set or (sym_next_move, next_move) in coord_pair_set:
                continue

            # Get the game count, if any, for sym_next_move
            try:
                sym_count = results_dict[sym_next_move][1]
            except KeyError:
                sym_count = 0   # If the symmetrical move has no results_dict data, use count of 0
            except (TypeError, IndexError):  # Will only happen if results_dict has invalid data
                raise DBAccessException(f'DBAccess._merge_next_move_data(): internal error, invalid data in results_dict')

            # Find the preferred move, and then the non-preferred other_move
            pref_move = Coord.bias_coord_for_merge(next_move, sym_next_move, transform_number)
            other_move = sym_next_move if pref_move == next_move else next_move

            # The preferred move gets all the game_count
            merge_dict[pref_move] = (pref_move, game_count + sym_count)

            # Add the moves to the pair set in both orders
            coord_pair_set.add((pref_move, other_move))
            coord_pair_set.add((other_move, pref_move))

        # Merge_dict becomes next_dict, repeat for the next transform_number
        results_dict = merge_dict

    # The resulting results_dict is the merged dict
    return list(results_dict.values())
