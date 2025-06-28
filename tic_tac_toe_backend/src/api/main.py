from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

# --- OpenAPI Metadata ---
app = FastAPI(
    title="Tic Tac Toe Backend API",
    description=(
        "Backend service for Tic Tac Toe game: "
        "start/restart game, make player moves, query status/state."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Game", "description": "Endpoints for playing and managing Tic Tac Toe games."}
    ]
)

# --- CORS Middleware (open for dev/local) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models for API ---
class Player(str, Enum):
    X = "X"
    O_player = "O"  # Renamed to avoid ambiguous variable name



class CellValue(str, Enum):
    empty = ""
    X = "X"
    O_player = "O"  # Renamed to avoid ambiguous variable name


class Move(BaseModel):
    """Represents a player's move."""
    row: int = Field(..., ge=0, le=2, description="Row (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column (0-2)")


class GameState(BaseModel):
    """Represents the current Tic Tac Toe board and state."""
    board: List[List[CellValue]] = Field(
        ..., description="The 3x3 board"
    )
    current_player: Optional[Player] = Field(
        ..., description="Player whose turn it is next, or null if game ended"
    )
    winner: Optional[Player] = Field(
        None, description="Winner of the game if any"
    )
    status: Literal["ongoing", "win", "draw"] = Field(
        ..., description="Current game status"
    )
    message: Optional[str] = Field(
        "", description="Status message (optional)"
    )


class StartGameResponse(BaseModel):
    """Response for starting or restarting a game."""
    state: GameState


class MoveResponse(BaseModel):
    """Response after performing a move."""
    state: GameState

# --- In-memory game state management ---
# Two blank lines before the next class as required by E302


class _TicTacToeGame:

    def __init__(self):
        self.restart()

    # PUBLIC_INTERFACE
    def restart(self):
        """Reset or start new game."""
        self.board = [["" for _ in range(3)] for _ in range(3)]
        self.current_player = Player.X  # X always starts
        self.winner = None
        self.status = "ongoing"
        self.message = ""

    # PUBLIC_INTERFACE
    def get_state(self) -> GameState:
        """Return current board and game state."""
        return GameState(
            board=[
                [CellValue(cell or "") for cell in row]
                for row in self.board
            ],
            current_player=(self.current_player if self.status == "ongoing" else None),
            winner=self.winner,
            status=self.status,  # "ongoing", "win", "draw"
            message=self.message
        )

    # PUBLIC_INTERFACE
    def make_move(self, row: int, col: int):
        """Apply a player's move, checking turn, bounds, validity, and detect win/draw."""
        if self.status != "ongoing":
            self.message = "Cannot move: game is over."
            raise HTTPException(status_code=409, detail=self.message)
        if not (0 <= row <= 2 and 0 <= col <= 2):
            raise HTTPException(status_code=400, detail="Position out of bounds.")
        if self.board[row][col] != "":
            self.message = "Cell already filled."
            raise HTTPException(status_code=409, detail=self.message)
        player = self.current_player
        self.board[row][col] = player.value

        # Win/draw detection
        if self._check_win(player):
            self.winner = player
            self.status = "win"
            self.message = f"Player {player} wins!"
            self.current_player = None
        elif self._is_draw():
            self.status = "draw"
            self.message = "Game is a draw."
            self.current_player = None
        else:
            # Switch player
            if player == Player.X:
                self.current_player = Player.O_player
            else:
                self.current_player = Player.X
            self.message = f"Turn: Player {self.current_player}"

    def _check_win(self, player: Player):
        b = self.board
        lines = (
            b[0], b[1], b[2],  # Rows
            [b[0][0], b[1][0], b[2][0]],  # Columns
            [b[0][1], b[1][1], b[2][1]],
            [b[0][2], b[1][2], b[2][2]],
            [b[0][0], b[1][1], b[2][2]],  # Diagonal
            [b[0][2], b[1][1], b[2][0]],
        )
        return any(all(cell == player.value for cell in line) for line in lines)

    def _is_draw(self):
        return (
            all(cell != "" for row in self.board for cell in row)
            and self.status == "ongoing"
        )


# Single game for this simple implementation (no user accounts or persistence)
game = _TicTacToeGame()


# --- API Endpoints ---
@app.get("/", tags=["Game"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


@app.post(
    "/game/start",
    summary="Start a new game",
    description=(
        "Initialize or reset a Tic Tac Toe game. "
        "All previous progress is lost."
    ),
    response_model=StartGameResponse,
    tags=["Game"]
)
def start_game():
    """PUBLIC_INTERFACE: Start a new Tic Tac Toe game."""
    game.restart()
    return StartGameResponse(state=game.get_state())


@app.post(
    "/game/move",
    summary="Make a move",
    description="Make a move at the given row and column for the current player.",
    response_model=MoveResponse,
    tags=["Game"]
)
def make_move(move: Move):
    """PUBLIC_INTERFACE: Make a move for the current player at (row, col)."""
    game.make_move(move.row, move.col)
    return MoveResponse(state=game.get_state())


@app.get(
    "/game/state",
    summary="Get current game state",
    description=(
        "Fetch the full current game board, whose turn it is, "
        "status, and winner if any."
    ),
    response_model=GameState,
    tags=["Game"]
)
def get_game_state():
    """PUBLIC_INTERFACE: Return the current board, whose turn, and status."""
    return game.get_state()


@app.post(
    "/game/restart",
    summary="Restart the game",
    description=(
        "Restart the game (same as start), clearing board and resetting all status."
    ),
    response_model=StartGameResponse,
    tags=["Game"]
)
def restart_game():
    """PUBLIC_INTERFACE: Restart the current game. Clears board and sets to initial state."""
    game.restart()
    return StartGameResponse(state=game.get_state())
