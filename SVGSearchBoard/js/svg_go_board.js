const gutter = 500
const bsz = 10000
const stroke = 10
const stoneradius = 510
const stonestroke = 10
const hoshiradius = 150


// Board Mode
const MODE_SEARCH = 0    // Clicking adds a stone and performs a next move lookup
const MODE_REPLAY = 1    // No stone adding possible, only replaying an existing game
const MODE_STATIC = 2    // No stone adding or replay features, static board.


// Stones on board
const NOSTONE = 0
const WHITESTONE = -1
const BLACKSTONE = 1

// API Information
const APIPATH_BASE = CONFIG.API_URL
const APIPATH_NEXTMOVE = '/nextmove/'
const APIPATH_GAMESFORHASHES = '/gamesforhashes/'
const APIPATH_GAMEBYID = '/gamebyid/'


// Misc Utility
const NEIGHBOR_TRANSFORM = [[-1, 0], [1, 0], [0, -1], [0, 1]]

const COORDINATE_TRANSFORM = [
    [[1, 0], [0, 1]],    // 0   0    Identity                (x,y)       (X, Y)
    [[-1, 0], [0, 1]],   // 1   1    Flip left-right         (18-x, y)   (-X, Y)
    [[1, 0], [0, -1]],   // 2   2    Flip top-bottom         (x, 18-y)   (X, -Y)
    [[0, 1], [-1, 0]],   // 3   5    Rotate 90 CCW           (y, 18-x)   (Y, -X)
    [[-1, 0], [0, -1]],  // 4   4    Rotate 180 CCW          (18-x,18-y) (-X, -Y)
    [[0, -1], [1, 0]],   // 5   3    Rotate 270 CCW          (18-y, x)   (-Y, X)
    [[0, 1], [1, 0]],    // 6   6    Rotate 90 CCW, FlipLR   (y, x)      (Y, X)
    [[0, -1], [-1, 0]],  // 7   7    Rotate 270 CCW, FlipTB  (18-y,18-x) (-Y, -X)
]


function check_coords(x,y,warn=false) {
    if (x < 0 || y < 0 || x > 18 || y > 18) {
      if (warn) { alert(`Coordinates out of bounds x: [${x}] y: [${y}]`) }
      return false
    }
    return true
}

function flatten(x,y) {
  return (19 * y) + x
}

function unflatten(flat) {
  return [
    flat % 19,
    Math.trunc(flat / 19),
  ]
}

// Given an intersection return a list of neighboring intersections
function neighbor_list(x,y) {
  var nl = []
  for (var i = 0; i < 4; ++i) {
    var tx = x + NEIGHBOR_TRANSFORM[i][0]
    var ty = y + NEIGHBOR_TRANSFORM[i][1]
    if (tx >= 0 && ty >= 0 && tx <= 18 && ty <= 18)  {
      nl.push([tx,ty])
    }
  }
  return nl
}

function neighbor_list_flat(flat) {
  var nl = []
  const [x,y] = unflatten(flat)
  for (var i = 0; i < 4; ++i) {
    var tx = x + NEIGHBOR_TRANSFORM[i][0]
    var ty = y + NEIGHBOR_TRANSFORM[i][1]
    if (tx >= 0 && ty >= 0 && tx <= 18 && ty <= 18)  {
      nl.push(flatten(tx,ty))
    }
  }
  return nl
}

function arraysEqual(a, b) {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (a.length !== b.length) return false;

  for (var i = 0; i < a.length; ++i) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}


// https://stackoverflow.com/questions/7033639/split-large-string-in-n-size-chunks-in-javascript
// Split str into a list of chunks that are size big  "abcdef" -> ["ab", "cd", "ef"]
function chunkSubstr(str, size) {
  const numChunks = Math.ceil(str.length / size)
  const chunks = new Array(numChunks)

  for (let i = 0, o = 0; i < numChunks; ++i, o += size) {
    chunks[i] = str.substr(o, size)
  }

  return chunks
}

// ///////////////////////////////////////////////////////////////////////////
// SVGGoBoard
//    Draws an SVG board with stones and marks

class SVGGoBoard
{
  constructor(target_div)
  {
    this.target_div = target_div
    this.setup_svg()
  }

  setup_svg() {
    this.svg_board_base = SVG().addTo(`#${this.target_div}`)
                .size(bsz + gutter * 2, bsz + gutter * 2)
                .viewbox(0, 0, bsz + gutter * 2, bsz + gutter * 2)
                .attr({
                      preserveAspectRatio: 'xMidYMid meet',
                        width: '100%', height: '100%',
                        margin: '5px',
                        padding: '5px'
                      })

    this.svg_board_base.rect(bsz + gutter * 2, bsz + gutter * 2).fill('WHITE')
            .stroke({ width: stroke, color: 'Black'})

    this.svg_board = this.svg_board_base.group()
    this.svg_board.rect(bsz, bsz).fill('White')


    for (var i = 0; i < 19; ++i) {
      const linestart = i * bsz / 18;
      this.svg_board.line(linestart, 0, linestart, bsz)
              .stroke({ width: stroke, color: 'Black' })
      this.svg_board.line(0, linestart, bsz, linestart)
        .stroke({ width: stroke, color: 'Black' })
    }

    // Draw hoshi points
    for (let x of [3, 9, 15]) {
      for (let y of [3, 9, 15]) {
        var px = x * (bsz / 18)
        var py = y * (bsz / 18)
        this.svg_board.circle(hoshiradius).fill('Black')
            .move(px - hoshiradius / 2, py - hoshiradius / 2);
      }
    }

    this.svg_board.transform({ translateX: gutter, translateY: gutter} )
    this.svg_stones = this.svg_board.group()
    this.svg_marks = this.svg_board.group()
  }

  svg_clear_marks() {
    this.svg_marks.clear()
  }

  svg_clear_stones() {
      this.svg_stones.clear()
  }

  draw_stone(x, y, isblack) {
    var px = x * bsz / 18
    var py = y * bsz / 18
    var stonecolor = isblack ? 'Black' :  'White'

    this.svg_stones.circle(stoneradius)
            .stroke({ width: stonestroke, color: 'Black'})
            .fill(stonecolor)
            .move(px - stoneradius / 2,
                  py - stoneradius / 2)
  }

  draw_mark(x, y, mark, color, backbox=false) {
    var px = x * bsz / 18
    var py = y * bsz / 18

    // Draw the mark on the board
    const font_size = 500
    const adjustx = font_size * 0.02
    const adjusty = font_size * 0.05

    if (backbox) {
      const rectsize = bsz / 18 * 0.9
      this.svg_marks.rect(rectsize, rectsize)
          .fill('White')
          .move(px - rectsize / 2, py - rectsize / 2)
    }

    this.svg_marks.text(mark)
        .font({ family: 'Courier New', size: font_size, fill: color, weight: 'bold'})
        .center(px + adjustx ,py + adjusty)

    return true
  }

  draw_highlight(x, y, on_stone_color) {
    var px = x * bsz / 18
    var py = y * bsz / 18

    const radius = stoneradius * 0.65
    var strokecolor = 'White'
    var fillcolor = 'Black'

    if (on_stone_color == WHITESTONE) {
      strokecolor = 'Black'
      fillcolor = 'White'
    }


    this.svg_stones.circle(radius)
    .stroke({ width: stonestroke * 5, color: strokecolor})
    .fill(fillcolor)
        .move(px - radius / 2, py - radius / 2)

  }



} // SVGGoBoard()


// ///////////////////////////////////////////////////////////////////////////
// GameOfGo
//    Implements the game of go, handles clicking to add new moves, next move
// lookup.

class GameOfGo
{
  constructor(target_div, mode, games_table, left_marks_table, right_marks_table, game_info_left, game_info_right)
  {
    this.target_div = target_div
    this.games_table = games_table
    this.left_marks_table = left_marks_table
    this.right_marks_table = right_marks_table
    this.game_info_left = game_info_left
    this.game_info_right = game_info_right

    this.svg = new SVGGoBoard(this.target_div, this.handler_board_clicked)

    this.game = {
      limit_marks: 10,    // Max number of marks to display, must be equal or less than 26
      total_move_num: 0,           // 0 = no moves, 1 = first move, ...
      displayed_position_num: 0,   // 0 = empty board, 1 = first move, ...
      moves: [],
      cur_position: new Array(361).fill(0),
      positions: [ new Array(361).fill(0) ],   // the first position is a blank board
      marks: {},
      locked: false,     // ignore clicks or updates if locked, used during marks api fetch
      mode: mode,        // Lookup, Replay, Static
      // format: [game_id, move_number, next_move, rotation, white_id, white_rank, black_id, black_rank]
      game_list: [],    // List of matching games returned from API next move search, shown in game_list column
      name_dict: {},    // Dictionary of player id to name
      replay_board: undefined,    // If games_table is clicked, send the game to replay to replay_board
      highlight_last_move: true,
    }



    this.svg.svg_board_base.click( function (e) {
        if (this.game.locked) {
          console.log('Ignoring click while board is locked')
          return
        }

        switch (this.game.mode) {
          case MODE_STATIC:
            // Ignore any clicks in static mode
            return
          case MODE_REPLAY:
            // Advance to the next move in replay mode
            this.step_displayed_move_num(1)
            return
          case MODE_SEARCH:
            // Perform a next move search
            var point = this.svg.svg_board_base.point(e.pageX, e.pageY)
            var cx = Math.round( (point.x - gutter) / (bsz / 18))
            var cy = Math.round( (point.y - gutter) / (bsz / 18))
            if (check_coords(cx,cy)) {
              this.clear_marks()
              this.play_move(cx,cy)  // will clear the marks board
            }
            this.perform_nextmove_lookup()
            return
        }
        console.log(`click handler has invalid game.mode! [${this.game.mode}]`)
      }.bind(this))

      this.draw_board()
      if (this.game.mode == MODE_SEARCH) {
        this.clear_marks(true)
        this.perform_nextmove_lookup()
      }


  }

  // ////////////////////////////////////////////////////////////////////////
  // Marksboard

  clear_marks(will_be_blank=false) {
    this.clear_html_marks_tables(will_be_blank)
    this.game.marks = {}
    this.svg.svg_clear_marks()
  }

  add_mark(x, y, mark, count) {
    var flat = flatten(x,y)
    const g = this.game
    const p = this.game.cur_position
    if (g.marks[flat]) {
      console.log(`Mark ${g.marks[flat].mark}already exists at ${x}, ${y}`)
      return false
    }

    // Use black for color, but if there is a blackstone on the intersection use white
    var color = 'Black'
    if (p[flat] ==  BLACKSTONE) {
      color = 'White'
    }

    g.marks[flat] = {
      x: x,
      y: y,
      mark: mark,
      flat: flat,
      color: color,
      count: count,
    }

    return true
  }


  // ////////////////////////////////////////////////////////////////////////
  // SVG Drawing

  // Draw the marks board
  draw_marks() {
    for (const [key, value] of Object.entries(this.game.marks)) {
      var color = this.game.cur_position[flatten(value.x, value.y)]
      var backbox = (color == NOSTONE)?true:false
      this.svg.draw_mark(value.x, value.y, value.mark, value.color, backbox)
    }
  }

  // Draw stones on the board, and redraw the marks board
  draw_board() {
    const g = this.game
    this.svg.svg_clear_marks()
    this.svg.svg_clear_stones()
    for (var x = 0; x < 19; ++x) {
      for (var y = 0; y < 19; ++y) {
        var flat = flatten(x,y)
        if (!g.positions[g.displayed_position_num]) {
          alert('nope')
        }
        var color = g.positions[g.displayed_position_num][flat]
        if (color != NOSTONE) { this.svg.draw_stone(x, y, color == BLACKSTONE); }
      }
    }
    this.draw_marks()

    if (g.highlight_last_move && g.displayed_position_num > 0) {
      const [x,y] = g.moves[g.displayed_position_num - 1]
      var stonecolor = BLACKSTONE
      if ( (g.displayed_position_num + 2) % 2 == 0) {
        stonecolor = WHITESTONE
      }
      this.svg.draw_highlight(x, y, stonecolor)
    }

  }


  set_replay_board(replay_board) {
    this.game.replay_board = replay_board
    replay_board.receive_game_to_replay(undefined, 0)

  }

  // ////////////////////////////////////////////////////////////////////////
  // Moves

  reset_game() {
    const g = this.game
    g.total_move_num = 0
    g.displayed_position_num = 0
    g.moves = []
    g.cur_position = new Array(361).fill(0)
    g.positions = [ new Array(361).fill(0) ]
    g.marks = {}
    g.locked = false
    g.game_list = []
    g.name_dict = {}
  }

  // Add a move to the board, color based on move number.
  play_move(at_x, at_y, redraw=true) {
    const g = this.game

    // Step #1: Test to see if this is a valid move
    // Coordinates must be valid
    if (!check_coords(at_x,at_y)) {
      console.log(`Invalid coordinates. ${at_x},${at_y}`)
      return false
    }

    const flat = flatten(at_x,at_y)

    // Make a temporary copy of the currently displayed position
    var tpos = [...g.positions[g.displayed_position_num]]

    // The intersection must be empty
    if (tpos[flat] != NOSTONE) {
      console.log(`Can't play on an existing stone. ${at_x},${at_y}`)
      return false
    }

    // Step #2: So far we have a valid move, but still need to test for ko

    // The next move will be added after displayed_position_num, and any
    // Set the color
    var isblack = false
    if ( (g.displayed_position_num + 2) % 2 == 0) {
      isblack = true
    }


    // Last color is the last stone played (this move), other_color is the inverse
    const last_color = isblack ? BLACKSTONE : WHITESTONE
    const other_color = isblack ? WHITESTONE : BLACKSTONE

    // Add our stone to the board
    tpos[flat] = last_color;

    // Scan the groups and look for captured stones
    var zero_last_color = []   // Groups with 0 liberties and the same color as the last move
    var zero_other_color = []  // Groups with 0 liberties with the other color

    var groups = this.build_groups(tpos)

    // Record any groups with 0 liberties
    for (var i = 0; i < groups.length; ++i) {
      if (groups[i].color == last_color && groups[i].liberties == 0) { zero_last_color.push(groups[i]) }
      else if (groups[i].color == other_color && groups[i].liberties == 0) { zero_other_color.push(groups[i]) }
    }

    // There should only be 0 or 1 groups of zero_last_color
    if (zero_last_color.length > 1) {
      alert("zero_last_color more than 1, this shouldn't happen?")
      console.log("zero_last_color more than 1, this shouldn't happen?")
      return false
    }

    // If there is 1 group in zero_last_color, there must be 1 or more groups in zero_other_color to avoid self capture
    if (zero_last_color.length == 1 && zero_other_color == 0) {
      console.log("cannot play self capture")
      return false
    }

    // Remove all zero_other_color groups from the board
    for (let og of zero_other_color) {
      for (let stone of og.stones) {
        tpos[stone] = NOSTONE
      }
    }

    // Check for ko
    if (g.displayed_position_num > 0 && arraysEqual(tpos, g.positions[g.displayed_position_num-1])) {
        console.log("can't play ko")
        return false
    }

    // Only update moves and move_num at this point
    // Truncate the current moves to displayed_position_num
    g.moves = g.moves.slice(0, g.displayed_position_num)
    g.moves.push([at_x,at_y])

    // Slice positions array to new displayed_position
    g.positions = g.positions.slice(0, g.displayed_position_num+1)

    // Adjust our values
    g.displayed_position_num += 1
    g.total_move_num = g.displayed_position_num

    //  Push the temporary position onto the positions array
    g.positions.push(tpos)

    // Redraw the board with the updated position
    if (redraw) {
      this.draw_board()
    }

  }

  // Step forwards are backwards in the move/position list
  step_displayed_move_num(n) {
    const g = this.game

    if (g.locked) {
      return
    }

    if (n > 0 && g.displayed_position_num == g.total_move_num) { return }
    else if (n < 0 && g.displayed_position_num == 0) { return }
    else if (n == 0) { return }

    if (g.mode == MODE_STATIC) { return }
    else if (g.mode == MODE_REPLAY) {
      g.displayed_position_num = Math.min(Math.max(0, g.displayed_position_num + n), g.total_move_num)
      g.cur_position = g.positions[Math.max(0, g.displayed_position_num)]
      this.draw_board()
    }
    else if (g.mode == MODE_SEARCH) {
      g.displayed_position_num = Math.min(Math.max(0, g.displayed_position_num + n), g.total_move_num)
      g.cur_position = g.positions[Math.max(0, g.displayed_position_num)]
      this.clear_marks()
      this.draw_board()
      this.perform_nextmove_lookup()
    }

  }

  // ////////////////////////////////////////////////////////////////////////
  // Lookup

  // Convert the 2 integer move list to a list of 2 character moves
  get_moves_for_lookup() {
    const g = this.game
    var r = []
    for (var i = 0; i < Math.min(g.displayed_position_num, g.moves.length); ++i) {
      const [x,y] = g.moves[i]
      const ax = String.fromCharCode(x + 97)
      const ay = String.fromCharCode(y + 97)
      r.push(ax+ay)
    }
    return r
  }

  // Create the Promise for the Flask API lookup
  perform_nextmove_lookup() {
    this.game.locked = true
    var moves = this.get_moves_for_lookup()

    /*
    if (moves.length > 0) {
      //moves = moves.join('+')
    } else {
      moves = []
    }
    */

    const full_url = `${APIPATH_BASE}${APIPATH_NEXTMOVE}
    `
    var params = {
      moves: moves
    }
    axios.post(full_url, params)
      .then(result => {
        this.add_nextmove_results(result)
        this.game.locked = false
      })
      .catch(error => {
        console.log(`AXIOS lookup error [${full_url}] -> [${error}]`)
        this.clear_marks(true)
        this.game.locked = false
      })

  }

  clear_html_marks_tables(will_be_blank=false) {
    const left_table = $(`#${this.left_marks_table}`)
    const right_table = $(`#${this.right_marks_table}`)
    left_table.empty()
    right_table.empty()

    if (will_be_blank) {
      const blank = '---'
      const table_html = `<tr><th scope="row" class="text-center align-middle">${blank}</th><td class="text-center align-middle">${blank}</td><td class="text-center align-middle">${blank}</td></tr>`

      for (var i = 0; i < 5; ++i) {
          left_table.append(table_html)
          right_table.append(table_html)
      }
    }
  }




  // Called when the lookup Promise completes, add next moves to the mark board
  // Then draw mark board
  add_nextmove_results(results) {
    this.clear_marks()

    const left_table = $(`#${this.left_marks_table}`)
    const right_table = $(`#${this.right_marks_table}`)

    const nextmoves = results.data.nextmove
    const totalgames = results.data.totalgames

    for (var i = 0; i < Math.min(this.game.limit_marks, nextmoves.length); ++i) {
      const x = parseInt(nextmoves[i].move.charCodeAt(0)) - 97
      const y = parseInt(nextmoves[i].move.charCodeAt(1)) - 97
      const letter = String.fromCharCode(i + 65)
      const count = nextmoves[i].count
      var per = (totalgames > 0) ? (count * 100 / totalgames) : 0
      per = per.toFixed(1)

      this.add_mark(x, y, letter, count)
      const table_html = `<tr data-href="${letter}"><th scope="row" class="text-center align-middle">${letter}</th><td class="text-center align-middle">${count}</td><td class="text-center align-middle">${per}%</td></tr>`
      if (i < 5) {
        left_table.append(table_html)
      } else if (i < 10) {
        right_table.append(table_html)
      }
    }

    // Marks table click handler
    const myobj = this
    $(`#${this.left_marks_table} > tr`).click( function(e) {
      const data = $(this).data('href')
      myobj.marks_table_clicked(data )
    })
    $(`#${this.right_marks_table} > tr`).click( function(e) {
      const data = $(this).data('href')
      myobj.marks_table_clicked(data )
    })


    this.draw_marks()
  }

  load_games() {
    const g = this.game
    if (g.displayed_position_num < 1) { return; }
    const p = this.game.positions[g.displayed_position_num]
    var hashes = []

    for (var rot = 0; rot < 8; ++rot) {
      var rotated_position = position_transform(p, rot)
      var hash = generate_position_hash(rotated_position)
      hashes.push(hash)
    }

    const full_url = `${APIPATH_BASE}${APIPATH_GAMESFORHASHES}`
    var params = {
      hashes: hashes,
    }

    this.game.locked = false

    axios.post(full_url, params)
      .then(result => {
        this.game.locked = false
        this.parse_game_results(result)
      })
      .catch(error => {
        console.log(`AXIOS lookup error [${full_url}] -> [${error}]`)
        this.game.locked = false
      })
  }

  // <0 kyu ranks >0 dan ranks =0 unknown / no rank
  decode_rank_int(rank_int) {
    if (rank_int < 0) {
      return `${rank_int*-1}k`
    } else if (rank_int > 0) {
      return `${rank_int}d`
    }
    return 'NR'  // no rank
  }

  // [game_id, move_number, next_move, rotation, white_id, white_rank, black_id, black_rank]
  // names[id] = 'player name'
  parse_game_results(results) {
    const games = results.data.games
    const names = results.data.names

    this.game.game_list = results
    this.game.name_dict = names

    const target_table = $(`#${this.games_table}`)

    target_table.empty()

    for (var i = 0; i < games.length; ++i) {
      const [game_id, move_number, next_move, rotation, white_id, white_rank, black_id, black_rank] = games[i]
      const white_name = names[white_id] || "Unknown"
      const black_name = names[black_id] || "Unknown"
      const white_rankstr = this.decode_rank_int(white_rank)
      const black_rankstr = this.decode_rank_int(black_rank)

      /*
      const x = parseInt(next_move.charCodeAt(0)) - 97
      const y = parseInt(next_move.charCodeAt(1)) - 97

      const [rx, ry] = move_transform(x,y,rotation)
      const rflat = flatten(rx,ry)
      const next_move_letter = this.game.marks[rflat].mark
      */

      // Black Player 9d - White Player 9d
      const table_html = `<tr data-href="${game_id}"><td scope="row" class="text-center align-middle">${black_name} ${black_rankstr}</th><td class="text-center align-middle">${white_name} ${white_rankstr}</td></tr>`
      target_table.append(table_html)
    }

    // Games table click handler
    const myobj = this
    $(`#${this.games_table} > tr`).click( function(e) {
      const data = $(this).data('href')
      myobj.games_table_clicked(data)
    })

  }

  // This board is a replay board and we are receiving a game record to replay


  // If record == undefined then game_info table will be filled with blank values
  receive_game_to_replay(record, start_from_move) {
    const g = this.game

    this.reset_game()

    function add_to_info(target, field_name, value) {
      const table_html = `<tr><th scope="row" class="text-center align-middle">${field_name}</th><td class="text-center align-middle">${value}</td></tr>`
      target.append(table_html)
    }

    const left_table = $(`#${this.game_info_left}`)
    const right_table = $(`#${this.game_info_right}`)
    left_table.empty()
    right_table.empty()

    if (record) {
      const { black_name: black_name, black_rank: black_rank, white_name: white_name, white_rank: white_rank,
              date: game_date, event: game_event, komi: komi, move_list: game_moves, place: place,
             result: game_result, round: game_round } = record

      var move_list_char = chunkSubstr(game_moves, 2)

      for (var i = 0; i < move_list_char.length; ++i) {
        const x = parseInt(move_list_char[i].charCodeAt(0)) - 97
        const y = parseInt(move_list_char[i].charCodeAt(1)) - 97
        this.play_move(x,y, false)
      }
      g.displayed_position_num = start_from_move + 1
      add_to_info(left_table, 'Black', `${black_name} ${this.decode_rank_int(black_rank)}`)
      add_to_info(left_table, 'Date', game_date)
      add_to_info(left_table, 'Event', game_event)
      add_to_info(left_table, 'Result', game_result)

      add_to_info(right_table, 'White', `${white_name} ${this.decode_rank_int(white_rank)}`)
      add_to_info(right_table, 'Place', place)
      add_to_info(right_table, 'Round', game_round)
      add_to_info(right_table, 'Komi', komi)
    } else {
      const blank = '---'
      add_to_info(left_table, 'Black', blank)
      add_to_info(left_table, 'Date', blank)
      add_to_info(left_table, 'Event', blank)
      add_to_info(left_table, 'Result', blank)

      add_to_info(right_table, 'White', blank)
      add_to_info(right_table, 'Place', blank)
      add_to_info(right_table, 'Round', blank)
      add_to_info(right_table, 'Komi', blank)
    }
    this.draw_board()
  }


  // When a game in the game table is clicked, load it from the API and send it to the replay_board
  games_table_clicked(game_id) {
    const g = this.game

    if (!g.replay_board) {
      alert('Could not find replay board to load game')
      return
    }

    const full_url = `${APIPATH_BASE}${APIPATH_GAMEBYID}`
    var params = {
      game_id: game_id,
    }

    g.locked = false

    axios.post(full_url, params)
      .then(result => {
        g.replay_board.receive_game_to_replay(result.data.game, g.displayed_position_num)
        g.locked = false

      })
      .catch(error => {
        console.log(`AXIOS lookup error [${full_url}] -> [${error}]`)
        g.locked = false
      })
  }

  marks_table_clicked(letter) {
    const g = this.game
    for (const [key, value] of Object.entries(this.game.marks)) {
       if (value.mark == letter) {
         if (check_coords(value.x, value.y)) {
           this.clear_marks()
           this.play_move(value.x, value.y)  // will clear the marks board
         }
         this.perform_nextmove_lookup()
       }
    }
  }




  /*
    var groups = [
      { 'color': xxx, 'liberties': xxx, 'stones': [stone1, stone2] },
      ...
    ]
  */
  build_groups(p) {
    var stones = new Set()

    // Create a set of every stone on the board
    for (var x = 0; x < 19; x++) {
      for (var y = 0; y < 19; y++) {
          var flat = flatten(x,y)
          if (p[flat] == NOSTONE) { continue; }
          stones.add( flat )
      }
    }

    var groups = []

    // Iterate the set
    for (let stone of stones) {
      const color = p[stone]
      var group = {
          color: color,
          stones: new Set([stone]),
          liberties: 0,
      }
      // Walk neighbors
      var neighbors = new Set(neighbor_list_flat(stone))
      var walked = new Set([stone])
      for (let nei of neighbors) {
        if (walked.has(nei)) { continue; }  // Skip if previously walked
        walked.add(nei)     // Add it to walked

        const ncolor = p[nei]

        if (ncolor == NOSTONE) { // An empty intersection increases the liberty count
          group.liberties += 1;
          continue;
        }
        if (color != ncolor) { continue; } // Skip if not same color

        stones.delete(nei)  // Remove it from our stones so we ignore in the future
        group.stones.add(nei)     // Add it to the group
        // Add the neighbors of this neighbor
        for (let neinei of new Set(neighbor_list_flat(nei))) {
          neighbors.add(neinei)
        }
      } // for neighbors

      groups.push(group)
    } // for stones

    return groups
  }
}


function move_transform(x, y, to_rotation) {
  x -= 9
  y -= 9

  var tx = COORDINATE_TRANSFORM[to_rotation][0][0] * x + COORDINATE_TRANSFORM[to_rotation][0][1] * y
  var ty = COORDINATE_TRANSFORM[to_rotation][1][0] * x + COORDINATE_TRANSFORM[to_rotation][1][1] * y

  tx += 9
  ty += 9

  return [tx,ty]
}

function position_transform(position, to_rotation) {
  if (to_rotation == 0) { return position; }  // identity, no transform

  var newpos = Array(361).fill(0)

  for (var flat = 0; flat < 361; ++flat) {
    if (position[flat] == 0) { continue; }
    var [x,y] = unflatten(flat)

    x -= 9
    y -= 9

    var tx = COORDINATE_TRANSFORM[to_rotation][0][0] * x + COORDINATE_TRANSFORM[to_rotation][0][1] * y
    var ty = COORDINATE_TRANSFORM[to_rotation][1][0] * x + COORDINATE_TRANSFORM[to_rotation][1][1] * y

    tx += 9
    ty += 9

    newpos[flatten(tx,ty)] = position[flat]
  }
  return newpos
}

function generate_position_hash(position) {
  var hash = 0

  for (var flat = 0; flat < 361; ++flat) {
    switch (position[flat]) {
      case 1:
        hash += hash_list[flat]
        break
      case -1:
        hash -= hash_list[flat]
        break
    }
  }
  return hash
}



const hash_list = [-972026825, -855920665, -1726883353, 1806723638, -648474315, 1619839338, -213149750,
-231944539, 887033447, 1849648372, -54043465, 949655785, -1334813165,
-1771758190, 1034872264, 1359215583, -757123712, 1694960022, 506437520,
-227169411, 1335668001, 1433809003, 1248103884, 1730660977, -2034259802,
1288510125, -716585919, 681379394, 957705316, 199602563, 260650543,
-1161343494, 438883554, 563041023, -1886395062, 1462606573, 1646141152,
36576695, -1214355107, -1410124574, 886717536, -652980963, 1991971104,
577518384, -1935914452, -1795747586, 335831797, -1462043508, -1520917193,
-396289409, 794210363, 882962285, 1622551917, 1635916551, 662610062,
-844042532, -1944829931, -710073645, 1246966854, -1981841524, 228439338,
-465315427, 1188540565, -1271969847, -1119931263, 660216454, 1554363362,
-1969092275, -919618935, -1219721921, -843148662, 148936817, -1388441096,
-823279673, 2126667073, 1468018502, -767434323, 567639680, 890068206,
256529797, -1531579188, -60283541, -1239028041, 1695889733, 464187627,
-950983790, -358075531, -2083264826, 671994939, -2118388489, 922519004,
371762758, 101406936, 286184582, -309530584, 1733252789, 1081226214,
-1516377420, 39442194, -986112117, -1310121328, 1062820820, 1839505864,
987150089, -2133306922, -1256315936, -153190432, 1933798711, 2077041310,
-1917989055, 1305817215, 1470041007, 1094788200, 1822033425, 1507030157,
763287880, 1658445793, -1482155416, 1492771741, 121684891, 598924905,
-1689224351, 1201388232, 2099256430, 17961897, 1522275325, 1493685179,
167615007, 1710536090, -771966650, 1811684229, 1004385170, 1099886385,
420020622, -1485956208, 259713666, 366531608, -108865169, 1452257253,
265352787, 396402605, -421707998, 1882267329, 1465721177, 882826991,
-963398815, -1440899873, 492789782, -2126207435, -1146034519, 580030631,
321322726, -650075877, 44775587, -1220270119, 1033833541, -925374333,
-1318800175, -308994659, 1030848008, -1894022819, -1238955432, -1851640580,
-594997545, 1069959051, 1407705011, -669883570, -382471228, -131719646,
2042198607, 1465647781, 200383342, 1103902715, 1212278557, 620484923,
-1857086104, -1095640055, 1402821869, 1744822009, -1352788169, 124446377,
476675151, -1650276483, -1416508133, -1803790882, -175369260, 1278291069,
1098340613, 2005870518, 323592929, -1226157433, -1525055588, 1530745740,
1490417397, 1512245340, -1042683609, -992939560, -1724159607, -1375327423,
1257510892, 2064668924, 1039290195, -1496318722, -2096323740, 576895175,
1682239382, -1546503029, -1249923969, -1749342611, -334636227, 1617671366,
1610862487, 375490895, 1039666140, -1321710076, 1480346947, 1263288353,
1825334082, -1002873420, 1920825508, -1075680037, 721974563, -2062743169,
23008308, 131740297, 596454172, 352798103, -401864016, 751518861,
-1560327711, -302726995, -1584798571, -15028121, -1700792087, -1669598150,
1214689452, 679380635, -978412234, 1948637947, -1779121113, 2146499041,
-1981279796, 1605621392, 1860385820, -1285489806, 845708615, 273184763,
931392929, 217160301, -971610348, -102765941, -2134909853, 1606036935,
-1786464360, 1832087705, 1416759935, -1058277974, 118666276, -40753032,
454885773, -757610856, 1443640366, 663035612, -359534822, 282485556,
542140423, 934173109, 1559607622, -1603312393, -1937332178, -629882516,
-1219546994, -2067978131, 1275127438, -1491160000, -1267879758, -1041409596,
811721822, 171008249, 590769220, 1974044419, 660437281, -440617399,
-971012481, 1293961571, -80241936, 1002706782, -1219204095, -1318953765,
-303981390, -1568378224, 1640636430, -1922410365, -1009542555, 1750259331,
1751505067, -1586733799, 1339936491, 146716565, 94377855, 1029165885,
-1629560459, 640307961, -728779588, -1527141589, -2135018408, -1191148766,
1012658703, 307307600, -258019807, -810482710, -391475368, -1696946342,
-528690604, 603393721, -670922633, -1982497401, -956713494, -644436859,
-1609030857, -1179041967, 1665013954, -1755367507, -1823206815, -799533943,
-1912942313, -1280527608, -818350471, -1626106951, -1158296155, -1299851071,
-2118741668, -1006170402, -57213069, 1675730722, 379424666, -413190079,
-538879081, 1993810651, 1208183018, -1663859350, 1261522857, 1687092594,
1774828867, 1065121946, -388339712, 1444488625, -462731110, -1911843849,
-1528463158, 933501526, 1942862173, -7455370, 1814298465, -545721152,
1029373491, -1320566722, -207142928, -522679221, 1052816698, -1172526969]
