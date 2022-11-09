from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_restful import Resource, Api
import site
import os
from werkzeug.routing import BaseConverter
from bgo.dbaccess import DBAccess, DBAccessException, DBAccessLookupNotFound
from bgo.gameofgo import GameOfGo, GameOfGoException

db_access = None

# From https://exploreflask.com/en/latest/views.html
class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split('+')

    def to_url(self, values):
        return '+'.join(super(ListConverter, self).to_url(value)
                        for value in values)


class NextMoveData(Resource):
    def post(self):
        # Setup
        try:
            moves = request.json['moves']
        except KeyError:
            return make_response(jsonify({'message': 'must pass a moves list'}), 400)

        if len(moves) > 1000:
            return make_response(jsonify({'message': 'max of 1000 moves'}), 400)

        # Do next move lookup
        try:
            results = db_access.lookup_next_move_from_moves(moves)
        except DBAccessException as e:
            print(f'NextMoveData() - database error [{e}] - [{moves}]')
            return make_response(jsonify({'message': f'IllegalMove in [{moves}]', 'nextmove': []}), 500)

        # Convert result to json output     result = [(next_move, game_count, rotation), ...]
        game_count = sum([row[1] for row in results])
        data = [{'move': row[0], 'count': row[1]} for row in results]
        return make_response(jsonify({
            'message': 'success',
            'nextmove': data,
            'totalgames': game_count,
        }), 200)


class GetGameByID(Resource):
    def post(self):
        try:
            game_id = request.json['game_id']
        except KeyError:
            return make_response(jsonify({'message': 'must pass a game_id'}), 400)

        if not isinstance(game_id, int):
            return make_response(jsonify({'message': 'game_id must be int'}), 400)

        try:
            result = db_access.get_game_by_id(game_id)
        except DBAccessException as e:
            print(f'GetGameByID() - internal error [{e}] - {game_id}')
            return make_response(jsonify({'message': 'internal error during request'}), 500)

        return make_response(jsonify({'message': 'success', 'game': result}), 200)


class GamesForHashes(Resource):
    def post(self):
        try:
            hashes = request.json['hashes']
        except KeyError:
            return make_response(jsonify({'message': 'must pass at least one hash'}), 400)

        if len(hashes) == 0 or len(hashes) > 100:
            return make_response(jsonify({'message': 'must pass at between 1 to 100 hashes'}), 400)

        for board_hash in hashes:
            if not isinstance(board_hash, int):
                return make_response(jsonify({'message': 'all hashes must be int'}), 400)

        try:
            results = db_access.get_games_for_hashes(hashes, 1000)
        except DBAccessException as e:
            print(f'GamesForHashes() - internal error [{e}] - {hashes}')
            return make_response(jsonify({'message': 'internal error during request'}), 500)

        return make_response(jsonify({'message': 'success', 'games': results['games'], 'names': results['names']}), 200)

def main():
    global db_access
    database_path = os.path.join(os.path.dirname(__file__), 'bgogames.sqlite')
    app = Flask(__name__)
    api = Api(app)
    cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.url_map.converters['list'] = ListConverter
    db_access = DBAccess(database_path)
    api.add_resource(NextMoveData, '/api/nextmove/')
    api.add_resource(GamesForHashes, '/api/gamesforhashes/')
    api.add_resource(GetGameByID, '/api/gamebyid/')

    app.run(debug=True, host='0.0.0.0')

if __name__ == '__main__':
    main()


