# Python script for acting as a server for tic-tac-toe game client.
# Following is the simplified diagram for server-client interaction:
"""
    
                   SERVER                           CLIENT
                 
                 Listening     <---------------   Socket Conn
                 - Conn.accept

                 Recving       <---------------   NEWG,LOAD,ENDG,CLOS,MOVE
                 - NEWG
                    Start a new game
                    BORD       --------------->   Start a new game

                 - LOAD
                    Load the game
                    BORD       --------------->   Start the game
                 
                 - ENDG
                    End the current game
                    OVER       --------------->   The game has ended

                 - CLOS
                    Close the Conn
                    CLOS      ---------------->   The conn has closed

                 - MOVE
                    Process client's move
                    BORD      ---------------->   The board with server's move
                    OVER      ---------------->   The game is over
                    EROR      ---------------->   There's an error

"""

import socket
import random
import math
import sys
import signal
import concurrent.futures


#==============================================================================
# Symbolic Constants
#==============================================================================
# Socket 
HOST = "" # all available interfaces
PORT = 6969

# BOARD stuff
X = 0
O = 1
empty = 2

# Game
x_won = X
o_won = O
draw = -1


#==============================================================================

class Packet:
    """ Class for representing a network packet. """
    id:str
    content:type

    # Packet ids
    new_game = "NEWG"
    load_game = "LOAD"
    end_game = "ENDG"
    move = "MOVE"
    board = "BORD"
    over = "OVER"
    error = "EROR"
    close = "CLOS"


    def __init__(self, id, content=None):
        if not isinstance(id, str):
            raise TypeError
        if id not in (Packet.new_game, Packet.load_game, Packet.end_game,
                Packet.move, Packet.board, Packet.over, Packet.error,
                Packet.close):
            raise ValueError
        self.id = id
        self.content = content

    def to_bytes(self):
        s = self.id
        if self.content != None:
            s += ':'
            if isinstance(self.content, list):
                s += str(self.content)[1:-1].translate(
                                str.maketrans({ch : ""for ch in " '\""}))
            else:
                s += str(self.content)

        return bytes(s, "UTF-8")

    @classmethod
    def from_bytes(self, byte_str):
        """ Create a Packet object from bytes. 
            Throw an ValueError exception if not a validly formatted packet.
        """
        s = str(byte_str, "UTF-8")

        if s in (Packet.new_game, Packet.end_game, Packet.close):  # No content body
            id = s
            content = None
        else:
            id,content = s.split(":", maxsplit=1)
            if id not in (Packet.load_game, Packet.move, Packet.over, Packet.error):
                raise ValueError

        # Parse and validate content
        if content:
            if id == Packet.move:
                content = content.split(',')[:2] 
                if len(content) != 2:
                    raise Error.e_unknown_cmd()
                try:
                    content = list(map(int, content))
                except ValueError:
                    raise Error.e_bad_move()
                if not all(0 <= i <= 2 for i in content):
                    raise Error.e_bad_move()

            elif id == Packet.load_game:
                content = content.split(',')[:10]
                if len(content) != 10:
                    raise Error.e_unknown_cmd()
                if content[0].upper() not in ("X", "O"):
                    content[0] = 'X'
                try:
                    content[1:] = list(map(int, content[1:]))
                except ValueError:
                    raise Error.e_unknown_cmd()
                if not all(i in (X, O, empty) for i in content[1:]):
                    raise Error.e_unknown_cmd()

            elif id == Packet.over:
                content = content.split(',')[:10]
                if len(content) != 10:
                    raise Error.e_unknown_cmd()
                if content[0].upper() not in ("S", "C", "N"):
                    content[0] = 'N'
                try:
                    content[1:] = list(map(int, content[1:]))
                except ValueError:
                    raise Error.e_unknown_cmd()
                if not all(i in (X, O, empty) for i in content[1:]):
                    raise Error.e_unknown_cmd()

        return self(id,content)


class Error(Packet, BaseException):
    """ Class for representing an error packet. """

    def __init__(self, *args, **kwargs):
        super(Error, self).__init__(*args, **kwargs)
        if self.id != Packet.error:
            raise ValueError

    # Error packets
    @classmethod
    def e_unknown_cmd(self):
        return self("EROR", "UNKNOWN CMD")
    @classmethod
    def e_bad_move(self):
        return self("EROR", "BAD MOVE")
    @classmethod
    def e_no_game(self):
        return self("EROR", "NO GAME")


class Board:
    """ Class for representing tic-tac-toe board.
        A board is represented as an int[9] of square values(empty, X, O).
    """
    board:list[int]

    class InvalidMove:
        """ For throwing invalid move exceptions """
        pass

    def __init__(self, board_list=None):
        if board_list == None:
            board_list = [2]*9
        # Check for valilidity
        if not all(isinstance(sq, int) for sq in board_list):
            raise TypeError("board_list is not int array")
        if len(board_list) != 9:
            raise ValueError("board_list's length is not 9")
        for sq in board_list:
            if sq not in [X, O, empty]:
                raise ValueError("board_list contains an invalid sq. value")
        self.board = board_list

    def __getitem__(self, key):
        """ Return evaluation of self[key]. """
        return self.board[key]

    def copy(self):
        """ Return a new instance(independent) of Board derived from self """
        return Board(self.board[:])

    @classmethod
    def create_from_packet(self, board_packet:Packet):
        if board_packet.id != Packet.board:
            raise ValueError("wrong packet type")

        return self(list(map(int, board_packet.content.split(","))))

    def to_packet(self):
        return Packet(Packet.board, self.board[:])

    def is_empty(self):
        for sq in self.board:
            if sq != empty:
                break
        else:
            return True
        return False

    def move(self, x, y, player):
        # Validate x,y
        if (not (0 <= x <= 3)) or (not (0 <= y <= 3)):
            raise InvalidMove()

        # Linearize (x,y) into square_pos
        sq_pos = y*3 + x
        
        if self.board[sq_pos] != empty:
            print(sq_pos)
            raise Board.InvalidMove()
        else:
            self.board[sq_pos] = player

    def get_game_result(self):
        """ Returns the result of game(x_won, o_won, draw)  if it has ended, 
            otherwise return None
        """
        # 2d representation in terms of linear indices [0..8]
        #  0 1 2
        #  3 4 5
        #  6 7 8

        # Check for win
        # For rows
        for y in range(3):
            player = None   # Player to check for win
            for x in range(3):
                # Linearize (x,y) into square_pos
                sq_pos = y*3 + x

                if self.board[sq_pos] == empty:
                    break
                if player == None:
                    player = self.board[sq_pos]

                if player != self.board[sq_pos]:
                    break
            else:
                # Player won
                return player
        # For cols
        for x in range(3):
            player = None # Player to check for win
            for y in range(3):
                # Linearize (x,y) into square_pos
                sq_pos = y*3 + x

                if self.board[sq_pos] == empty:
                    break
                if player == None:
                    player = self.board[sq_pos]

                if player != self.board[sq_pos]:
                    break
            else:
                # Player won
                return player

        # For diagonals
        # principal diagonal
        player = None
        for sq_pos in [0,4,8]:
            if self.board[sq_pos] == empty:
                break
            if player == None:
                player = self.board[sq_pos]

            if player != self.board[sq_pos]:
                break
        else:
            # Player won
            return player
        # secondary diagonal
        player = None
        for sq_pos in [6,4,2]:
            if self.board[sq_pos] == empty:
                break
            if player == None:
                player = self.board[sq_pos]

            if player != self.board[sq_pos]:
                break
        else:
            # Player won
            return player

        # Check for draw
        for sq in self.board:
            if sq == empty:
                break
        else:
            return draw

        # Game has not ended yet
        return None

    def get_turn(self):
        """ Return player with the turn to play (X or O) 
            Note: Assumes that the game has not ended.
        """
        n_x = 0
        n_o = 0

        for sq in self.board:
            if sq == X:
                n_x += 1
            elif sq == O:
                n_o += 1

        return (O if n_x > n_o else X)

    def child_boards(self, player):
        """ A generator method for iterating over all possible board positions
            from current position for `player`s turn.
            Returns an iterator to iterate over child `Board` objects.
            The iterator gives (child:Board, move:int) tuples. (move is move 
            from parent board to get to the child)
        """
        if player not in [X,O]:
            raise ValueError
        for sq_pos in range(9):
            if self[sq_pos] == empty:
                new_board_list = self.board[:]
                new_board_list[sq_pos] = player
                yield (Board(new_board_list), sq_pos)
                


class Game:
    """ Class for representing a game session with a client """
    game_on:bool
    game_ended:bool
    game_result:int # (x_won, o_won, draw) / None if (not game_ended)
    board:Board
    turn:int   # X or O / None if game_ended or (not game_on)

    def __init__(self, game_on=False, game_ended=False, game_result=None,
                    board=None, turn=None):
        # Argument validation
        if not (isinstance(game_on, bool) and isinstance(game_ended, bool)):
            raise TypeError
        if game_result != None and not isinstance(game_result, int):
            raise TypeError
        if board != None and not isinstance(board, Board):
            raise TypeError
        if turn != None and not isinstance(turn, int):
            raise TypeError
        if game_on and (board == None or game_ended or turn not in (X,O)):  
            raise ValueError
        if game_ended and (game_result not in (x_won, o_won, draw) or 
                            board == None or turn != None):
            raise ValueError
        if (not game_ended) and (game_result != None):
            raise ValueError
        if game_on or game_ended:
            if board.get_game_result() != game_result:
                if game_result != draw: # draw might indicate an Aborted Game
                    raise ValueError

        self.game_on = game_on
        self.game_ended = game_ended
        self.game_result = game_result
        self.board = board
        self.turn = turn

    def start_new_game(self):
        self.board = Board()
        self.game_on = True
        self.game_ended = False
        self.game_result = None
        self.turn = X

    def load_game(self, board):
        if not isinstance(board, Board):
            raise TypeError

        self.board = board
        self.game_on = True
        self.game_ended = False

        # Has game ended?
        self.game_result = self.board.get_game_result()
        if self.game_result != None:
            self.game_on = False
            self.game_ended = True
            self.turn = None
        else:
            self.turn = self.board.get_turn()

    def end_game(self):
        """ End/Abort the game based on self.game_result.
            Note: Assumes the self.game_result is already computed.
                 (using Board.get_game_result())
        """
        if self.game_on:
            self.game_on = False
            self.game_ended = True
            if self.game_result == None: # Abort the game if not already ended.
                self.game_result = draw
            self.turn = None

    def move(self, x, y):
        if not self.game_on:
            raise RuntimeError("Can't move without a game")
        
        self.board.move(x,y,self.turn)
        # Check game_result
        self.game_result = self.board.get_game_result()
        if self.game_result != None: # Game has ended
            self.end_game()
        else:
            self.turn = O if self.turn == X else X

    def create_over_packet(self, ai):
        if not self.game_ended:
            if self.game_on:
                raise RuntimeError("Game hasn't ended.")
            else:
                raise RuntimeError("No game.")

        if self.game_result == ai.player:   # AI won
            winner = "S"
        elif self.game_result == ai.player^1:
            winner = "C"
        else:
            winner = "N"

        return Packet(Packet.over, [winner]+self.board.board)

class AI:
    """ Class for representing CPU player. """
    player:int # X/O

    def __init__(self, player=X):
        self.set_player(player)

    def set_player(self, player):
        if player not in (X,O):
            if isinstance(player, int):
                raise ValueError
            raise TypeError

        self.player = player

    def best_move(self, board):
        """ Returns best move as (x,y) """
        # Move random for first move
        if board.is_empty():
            best_move = (0, random.randint(0,8)) # Eval is 0 for any first move
        else:
            best_move = AI.minimax(board, self.player, True)

        return (best_move[1]%3, best_move[1]//3, best_move[0])  # (x,y,eval)
    
    @staticmethod
    def minimax(board, turn, maximizing_player):
        """ Min/max algorithm for tic-tac-toe.
            Returns (minimax_payoff, best_move:int) where `best_move` is the 
            move from parent node to get to the child_node with the best payoff.
        """
        # Check for terminating node and compute payoff
        game_result = board.get_game_result()
        if game_result != None:
            if game_result == draw:
                payoff = 0
            elif game_result == turn:
                payoff = 10
            else:
                payoff = -10
            if not maximizing_player:
                payoff *= -1
            return (payoff, -1)

        # Find all child nodes and get the min/max payoff value
        value = math.inf
        best_move = -1
        if maximizing_player:
            value *= -1
        for child_node,move in board.child_boards(turn):
            if maximizing_player:
                child_payoff = AI.minimax(child_node, O if turn == X else X,
                                            False)[0]
                if child_payoff > value:
                    value = child_payoff
                    best_move = move
            else:
                child_payoff = AI.minimax(child_node, O if turn == X else X,
                                            True)[0]
                if child_payoff < value:
                    value = child_payoff
                    best_move = move

        return (value, best_move)


def recv_all(conn, bufsize):
    """ Receive bufsize num of bytes from conn socket. The function will return
        only when said num of bytes are received.
        Returns a bytes object of length bufsize.
        On error(connection closing on remote before receiving bufsize bytes), 
        a ValueError exception is raised.
    """
    buffer = b""
    while (len(buffer) != bufsize):
        data = conn.recv(bufsize-len(buffer))
        if data == b"":
            raise ValueError
        buffer += data 
    return buffer

def recv_packet(conn):
    """ Receive a packet from client and return corresponding Packet object.
        Raise Error exception if there's problem receiving a packet.
        Throw an ValueError exception if connection is closed.
    """
    if not conn:
        raise ValueError

    packet_id = recv_all(conn, 4)
    s_packet_id = str(packet_id, "UTF-8")
    if s_packet_id in (Packet.new_game,   # Contentless packet
            Packet.end_game, Packet.close): 
        return Packet.from_bytes(packet_id)
    else:
        if recv_all(conn, 1) != b':':
            raise Error.e_unknown_cmd()

        if s_packet_id == Packet.load_game:            
            content = recv_all(conn, 19)     # (X|O),i,i,i,i,i,i,i,i,i
        elif s_packet_id == Packet.move:
            content = recv_all(conn, 3)      # i,i
        else:
            raise Error.e_unknown_cmd()

        return Packet.from_bytes(packet_id+b':'+content)

def packet_handler(packet:Packet, conn, game:Game, ai:AI):
    """ Handle packet received from client, perform the appropriate 
        operations and send packet back to client if needed.
        Raises ValueError exception if client closes connection.
    """
    if packet.id == Packet.new_game:
        game.start_new_game()
        ai.set_player(random.choice((X,O)))
        print("[%d]: New game with client as %s" % (conn.fileno(), 
                                            "X" if ai.player == O else "O"))
        if ai.player == X:
            ai_move = ai.best_move(game.board)
            game.move(*ai_move[:-1])
            print("[%d]: AI move" % (conn.fileno()), ai_move[:-1], 
                    "[%d]" % ai_move[2])
        conn.sendall(game.board.to_packet().to_bytes())
        return

    elif packet.id == Packet.load_game:
        ai.set_player(X if packet.content[0]=="O" else O)
        game.load_game(Board(packet.content[1:]))
        print("[%d]: Loaded game with client as %s:" % (conn.fileno(), 
                                        packet.content[0]), game.board.board)
        if not game.game_ended:
            if game.turn == ai.player:
                ai_move = ai.best_move(game.board)
                game.move(*ai_move[:-1])
                print("[%d]: AI move" % (conn.fileno()), ai_move[:-1], 
                        "[%d]" % ai_move[2])
            conn.sendall(game.board.to_packet().to_bytes())

    elif packet.id == Packet.end_game:
        if not game.game_on:
            raise Error.e_no_game()
        game.end_game()
        print("[%d]: Game aborted by client" % (conn.fileno()))
        conn.sendall(game.create_over_packet(ai).to_bytes())
        return

    elif packet.id == Packet.move:
        if not game.game_on:
            raise Error.e_no_game()
        print("[%d]: Client move" % (conn.fileno()), packet.content[::-1])
        game.move(*packet.content[::-1])
        if not game.game_ended:
            ai_move = ai.best_move(game.board)
            game.move(*ai_move[:-1])
            print("[%d]: AI move" % (conn.fileno()), ai_move[:-1], 
                    "[%d]" % ai_move[2])
            if not game.game_ended:
                conn.sendall(game.board.to_packet().to_bytes())

    elif packet.id == Packet.close:
        try:
            conn.sendall(Packet(Packet.close).to_bytes())
        except OSError:
            pass
        finally:
            raise ValueError    # Connection closed by client
        
    if game.game_ended:
        if game.game_result == ai.player:
            result = "AI won"
        elif game.game_result == draw:
            result = "Draw"
        else:
            result = "Client won"
        print("[%d]: Game end: %s" % (conn.fileno(), result))
        conn.sendall(game.create_over_packet(ai).to_bytes())

def handle_client(conn):
    """ Handle a game session with a client """

    remote_addr = conn.getpeername()
    print("\n[+%d]: Connected to client at" % conn.fileno(), remote_addr)

    game = Game()
    ai = AI()
    while conn:
        # Main loop for receiving packets from client
        try:
            packet = recv_packet(conn)

            packet_handler(packet, conn, game, ai)

        except Error as e:
            print("[%d]: Error - (%s)" % (conn.fileno(), e.content)) 
            # Send error packet
            conn.sendall(e.to_bytes())
        except (BrokenPipeError, ValueError, KeyboardInterrupt):
            break

    # Close the socket
    print("[-%d]: Connection closed to" % conn.fileno(), remote_addr)
    conn.close()


if __name__ == "__main__":

    # Hook the interrupt signal to an exit

    def exit_handler(signum, stack_frame):
        print("Exiting...")
        exit(0)

    signal.signal(signal.SIGINT, exit_handler)

    # Parse arguments
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        # Listen 
        listener.bind((HOST,PORT))
        listener.listen(16)

        print("Listening on port %d..." % PORT, end="", flush=True)
        try:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                while True:
                    conn, addr = listener.accept()
                    future = executor.submit(handle_client,conn)
        except KeyboardInterrupt:
            pass 

