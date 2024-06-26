import pygame
import os
import chess
import numpy as np
import threading
import chess.polyglot
import random

# ---------- GLOBAL VARIABLES ----------
running = True
selected_piece = None
selected_position = None
selected_legal_moves = set()
dragging = False
mouse_pos = None
max_depth = 4
fps = 60
clock = pygame.time.Clock()

# Directory containing the Polyglot books
polyglot_directory = 'polyglot-collection'
polyglot_filenames = [
    'varied.bin', 'Performance.bin', 'KomodoVariety.bin', 'komodo.bin',
    'gm2600.bin', 'gm2001.bin', 'final-book.bin', 'Elo2400.bin',
    'DCbook_large.bin', 'codekiddy.bin', 'book2.bin', 'Book.bin'
]
polyglot_books = [os.path.join(polyglot_directory, filename) for filename in polyglot_filenames]

piece_square_table = [
# pawn
[[0,  0,  0,  0,  0,  0,  0,  0],
[50, 50, 50, 50, 50, 50, 50, 50],
[10, 10, 20, 30, 30, 20, 10, 10],
[5,  5, 10, 25, 25, 10,  5,  5],
[0,  0,  0, 20, 20,  0,  0,  0],
[5, -5,-10,  0,  0,-10, -5,  5],
[5, 10, 10,-20,-20, 10, 10,  5],
[0,  0,  0,  0,  0,  0,  0,  0]],
 
#  knight
[[-50,-40,-30,-30,-30,-30,-40,-50],
[-40,-20,  0,  0,  0,  0,-20,-40],
[-30,  0, 10, 15, 15, 10,  0,-30],
[-30,  5, 15, 20, 20, 15,  5,-30],
[-30,  0, 15, 20, 20, 15,  0,-30],
[-30,  5, 10, 15, 15, 10,  5,-30],
[-40,-20,  0,  5,  5,  0,-20,-40],
[-50,-40,-30,-30,-30,-30,-40,-50]],
 
#  bishop
[[-20,-10,-10,-10,-10,-10,-10,-20],
[-10,  0,  0,  0,  0,  0,  0,-10],
[-10,  0,  5, 10, 10,  5,  0,-10],
[-10,  5,  5, 10, 10,  5,  5,-10],
[-10,  0, 10, 10, 10, 10,  0,-10],
[-10, 10, 10, 10, 10, 10, 10,-10],
[-10,  5,  0,  0,  0,  0,  5,-10],
[-20,-10,-10,-10,-10,-10,-10,-20]],
 
#  rook
[[0,  0,  0,  0,  0,  0,  0,  0],
[5, 10, 10, 10, 10, 10, 10,  5],
[-5,  0,  0,  0,  0,  0,  0, -5],
[-5,  0,  0,  0,  0,  0,  0, -5],
[-5,  0,  0,  0,  0,  0,  0, -5],
[-5,  0,  0,  0,  0,  0,  0, -5],
[-5,  0,  0,  0,  0,  0,  0, -5],
[0,  0,  0,  5,  5,  0,  0,  0]],

#  queen
[[-20,-10,-10, -5, -5,-10,-10,-20],
[-10,  0,  0,  0,  0,  0,  0,-10],
[-10,  0,  5,  5,  5,  5,  0,-10],
[-5,  0,  5,  5,  5,  5,  0, -5],
[0,  0,  5,  5,  5,  5,  0, -5],
[-10,  5,  5,  5,  5,  5,  0,-10],
[-10,  0,  5,  0,  0,  0,  0,-10],
[-20,-10,-10, -5, -5,-10,-10,-20]],

#  king
[[-30,-40,-40,-50,-50,-40,-40,-30],
[-30,-40,-40,-50,-50,-40,-40,-30],
[-30,-40,-40,-50,-50,-40,-40,-30],
[-30,-40,-40,-50,-50,-40,-40,-30],
[-20,-30,-30,-40,-40,-30,-30,-20],
[-10,-20,-20,-20,-20,-20,-20,-10],
[20, 20,  0,  0,  0,  0, 20, 20],
[20, 30, 10,  0,  0, 10, 30, 20]]
]

# ---------- PIECE CLASS ----------
class Piece(pygame.sprite.Sprite):
    def __init__(self, filename, cols, rows):
        super().__init__()
        self.pieces = {}
        index = 0
        for color in (chess.WHITE, chess.BLACK):
            for piece_type in (chess.KING, chess.QUEEN, chess.BISHOP, chess.KNIGHT, chess.ROOK, chess.PAWN):
                piece = chess.Piece(piece_type, color)
                self.pieces[piece] = index
                index += 1
        self.spritesheet = pygame.image.load(filename).convert_alpha()
        self.cols = cols
        self.rows = rows
        self.cell_count = cols * rows
        self.rect = self.spritesheet.get_rect()
        w = self.cell_width = self.rect.width // self.cols
        h = self.cell_height = self.rect.height // self.rows
        self.cells = [(i % cols * w, i // cols * h, w, h) for i in range(self.cell_count)]

    def draw(self, surface, piece, coords):
        if piece in self.pieces:
            piece_index = self.pieces[piece]
            surface.blit(self.spritesheet, coords, self.cells[piece_index])

# ---------- HELPER FUNCTIONS ----------
def graphical_coords_to_coords(graphical_coords):
    graphical_x, graphical_y = graphical_coords
    return (graphical_x // 100, graphical_y // 100)

def coords_to_square(x, y):
    return chess.square(x, 7 - y)

def square_to_coords(square):
    return (chess.square_file(square), 7 - chess.square_rank(square))

def update_selected_legal_moves():
    selected_square = coords_to_square(selected_position[0], selected_position[1])
    for move in board.legal_moves:
        if move.from_square == selected_square:
            selected_legal_moves.add(move.to_square)

# ---------- LOGIC FUNCTIONS ----------
def start_piece_drag():
    global selected_piece, selected_position, dragging
    mouse_pos = pygame.mouse.get_pos()
    col, row = graphical_coords_to_coords(mouse_pos)
    square = coords_to_square(col, row)
    piece = board.piece_at(square)
    if piece:
        selected_piece = piece
        selected_position = (col, row)
        dragging = True
        update_selected_legal_moves()

def finish_piece_drag():
    global selected_piece, selected_position, dragging, selected_legal_moves
    mouse_pos = pygame.mouse.get_pos()
    col, row = graphical_coords_to_coords(mouse_pos)
    square = coords_to_square(col, row)
    if square in selected_legal_moves:
        from_square = coords_to_square(selected_position[0], selected_position[1])
        to_square = square
        print(chess.SQUARE_NAMES[from_square], chess.SQUARE_NAMES[to_square])
        move = chess.Move(from_square, to_square)
        board.push(move)
    selected_piece = None
    selected_position = None
    dragging = False
    selected_legal_moves = set()

def ai_move_logic():
    polyglot_move = get_polyglot_move(board)
    if polyglot_move and polyglot_move in board.legal_moves:
        board.push(polyglot_move)
        print("Polyglot moved:", polyglot_move)
    else:
        _, ai_move = Min(board, 0, -float('inf'), float('inf'))
        if ai_move in board.legal_moves:
            board.push(ai_move)
            print("AI moved:", ai_move)
        else:
            print("Illegal move attempted by AI:", ai_move)

# ---------- DRAWING FUNCTIONS ----------
def draw_board():
    for row in range(8):
        for col in range(8):
            color = LIGHT_GREEN if (row + col) % 2 == 0 else DARK_GREEN
            pygame.draw.rect(screen, color, (col * square_size, row * square_size, square_size, square_size))
    if selected_legal_moves:
        for move in selected_legal_moves:
            col, row = square_to_coords(move)
            pygame.draw.rect(screen, (255, 255, 0), (col * square_size, row * square_size, square_size, square_size))

def draw_pieces_on_board():
    for row in range(8):
        for col in range(8):
            square = coords_to_square(col, row)
            piece = board.piece_at(square)
            if piece:
                centered_x = col * square_size + (square_size - chess_pieces.cell_width) // 2
                centered_y = row * square_size + (square_size - chess_pieces.cell_height) // 2
                if not (dragging and (col, row) == selected_position):
                    chess_pieces.draw(screen, piece, (centered_x, centered_y))

def draw_piece_dragged():
    mouse_pos = pygame.mouse.get_pos()
    if mouse_pos:
        centered_x = mouse_pos[0] - chess_pieces.cell_width // 2
        centered_y = mouse_pos[1] - chess_pieces.cell_height // 2
        chess_pieces.draw(screen, selected_piece, (centered_x, centered_y))

# ---------- AI FUNCTIONS ----------
def evaluate_board(state):
    if state.is_checkmate():
        return -9999 if state.turn else 9999
    if state.is_stalemate():
        return 0

    eval = 0
    piece_values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
    mobility = len(list(state.legal_moves))  # Basic mobility evaluation

    # Adjusting weights based on the game phase
    if state.ply() < 20:  # Early game
        eval += mobility * 0.1
    else:  # Late game
        eval += mobility * 0.2

    for square in chess.SQUARES:
        piece = state.piece_at(square)
        if piece:
            value = piece_values[piece.piece_type]
            array_index = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING].index(piece.piece_type)
            position_value = piece_square_table[array_index][7 - chess.square_rank(square)][chess.square_file(square)]
            eval += value + position_value if piece.color == chess.WHITE else - (value + position_value)

    return eval

def gen_children(state):
    res = []
    for move in state.legal_moves:
        state.push(move)
        next_board = state.copy()
        res.append((next_board, move))
        state.pop()
    return res

def Max(state, depth, alpha, beta):
    if state.is_checkmate() or depth == max_depth:
        return evaluate_board(state), None
    val = -float('inf')
    best_move = None
    children = gen_children(state)
    for child, move in children:
        evaluation, _ = Min(child, depth+1, alpha, beta)
        if evaluation > val:
            val = evaluation
            best_move = move
        alpha = max(alpha, val)
        if alpha >= beta:
            break
    return val, best_move

def Min(state, depth, alpha, beta):
    if state.is_checkmate() or depth == max_depth:
        return evaluate_board(state), None
    val = float('inf')
    best_move = None
    children = gen_children(state)
    for child, move in children:
        evaluation, _ = Max(child, depth+1, alpha, beta)
        if evaluation < val:
            val = evaluation
            best_move = move
        beta = min(beta, val)
        if beta <= alpha:
            break
    return val, best_move

# ---------- REPRESENTATION FUNCTIONS ----------
def board_to_rep(board):
    pieces = [chess.PAWN, chess.ROOK, chess.KNIGHT, chess.BISHOP, chess.QUEEN, chess.KING]
    layers = [create_rep_layer(board, piece) for piece in pieces]
    return np.stack(layers)

def create_rep_layer(board, piece_type):
    layer = np.zeros((8, 8), dtype=int)
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type == piece_type:
            sign = 1 if piece.color == chess.WHITE else -1
            layer[chess.square_rank(square), chess.square_file(square)] = sign
    return layer

def generate_opp_ps_table():
    return [np.flipud(matrix) for matrix in piece_square_table]

opponent_piece_square_table = generate_opp_ps_table()

def get_polyglot_move(board):
    shuffled_books = polyglot_books[:]
    random.shuffle(shuffled_books)
    for book_path in shuffled_books:
        if os.path.exists(book_path):
            try:
                with chess.polyglot.open_reader(book_path) as reader:
                    try:
                        main_entry = reader.find(board)
                        return main_entry.move
                    except IndexError:
                        continue
            except IOError as e:
                print(f"Skipping invalid book {book_path}: {e}")
                continue
    return None

# ---------- MAIN PROGRAM ----------
if __name__ == "__main__":
    # Initialize Pygame
    pygame.init()

    # Set up the display
    screen_size = (800, 800)
    screen = pygame.display.set_mode(screen_size)
    pygame.display.set_caption("Chess Board")

    # Load the chess pieces
    filename = os.path.join('res', 'pieces.png')
    chess_pieces = Piece(filename, 6, 2)

    # Define chess.com-like green colors
    DARK_GREEN = (118, 150, 86)  # A muted, dark green
    LIGHT_GREEN = (238, 238, 210)  # A soft, light green

    # Size of squares
    square_size = screen_size[0] // 8

    # Initialize the chess board
    board = chess.Board()

    # Game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                start_piece_drag()
            elif event.type == pygame.MOUSEBUTTONUP and dragging:
                finish_piece_drag()
                if board.turn == chess.BLACK:
                    threading.Thread(target=ai_move_logic).start()

        # Draw board and pieces
        draw_board()
        draw_pieces_on_board()
        if dragging:
            draw_piece_dragged()

        # Refresh the display
        pygame.display.flip()
        clock.tick(fps)
