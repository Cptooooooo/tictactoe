# A Python program that acts as a client for a tictactoe server program.
# Much of the game logic is handled by server such as the game board, win/loss/
# draw logic and cpu opponent's move. The client handles displaying of board,
# managing saved games and score records through a config file.


import sockets
import os

#==============================================================================
# Symbolic constants
#==============================================================================
# Game states
menu = 1
game = 2

# Networking
# Packet Types
newGame = "NEWG"        # Start a new game       'NEWG'
endGame = "ENDG"        # End the current game   'ENDG'
move    = "MOVE"        # Send a move            'MOVE:<int>,<int>'
board   = "BORD"        # Get Board from server  'BORD:<i>,<i>,...<i>' (9 <i>s)
loadGame    = "LOAD"    # Send a game to load    'LOAD:<X/O>,<i>,...<i>'
gameOver    = "OVER"    # Game is over
closeConn   = "CLOS"
error   = "EROR"


#==============================================================================

class GameManager:
    """ Main class for managing the game states """
    pass

class Menu:
    """ Class for managing and displaying main game menu """
    pass

class Game:
    """ Class for managing and displaying the actual game. """
    pass

class Board:
    """ Class for representing game Board. """
    pass

class NetworkManager:
    """ Class for managing networking with server """
    conn:socket.socket  # Socket connected to game server

    def __init__(self, serverAddr):

        # Create a connected socket with game server
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect(serverAddr)

    def send(packType, payload:str):
        """ Send a packet of type `packType` and payload `payload` in format
            'packType:payload' to the server.
        """

class InputManager:
    """ Class for managing user input from console """
    pass

class ConfigManager:
    """ Class to read and write config for the game """
    pass

class Client:
    """ Class for managing all the client objects """
    pass

if __name__ == "__main__":

    # Testing 
