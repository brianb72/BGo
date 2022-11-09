

// //////////////////////////
// Entry Point
(function(){

  function make_board(div, mode, prefix, games_table, left_marks_table, right_marks_table, game_info_left, game_info_right)  {
    var board = new GameOfGo(div, mode, games_table, left_marks_table, right_marks_table, game_info_left, game_info_right)

    $(`#${prefix}_fast_back`).click ( function (e) {
      board.step_displayed_move_num(-5)
    })

    $(`#${prefix}_back`).click ( function (e) {
      board.step_displayed_move_num(-1)
    })

    $(`#${prefix}_forward`).click ( function (e) {
      board.step_displayed_move_num(1)
    })

    $(`#${prefix}_fast_forward`).click ( function (e) {
      board.step_displayed_move_num(5)
    })

    $(`#${prefix}_fast_forward`).click ( function (e) {
      board.step_displayed_move_num(5)
    })

    $(`#${prefix}_games`).click ( function (e) {
      board.load_games()
    })

    return board
  }

  //   constructor(target_div, mode, games_table, left_marks_table, right_marks_table)
  var lookup_board = make_board('board_lookup', MODE_SEARCH, 'lookup', 'games_table', 'mark_table_left', 'mark_table_right', '', '')
  var replay_board = make_board('board_replay', MODE_REPLAY, 'replay', '', '', '', 'game_info_left', 'game_info_right')

  // Tell the lookup board where loaded games should be sent to
  lookup_board.set_replay_board(replay_board)


}());
