# A Python program that acts as a client for a tictactoe server program.
# Much of the game logic is handled by server such as the game board, win/loss/
# draw logic and cpu opponent's move. The client handles displaying of board,
# managing saved games and score records through a config file.

# This script uses curses library to grab control over the terminal window and
# paint each character cell with precision. Since Fred is dead, I left no OOP
# stone unturned and implemented the whole things using Classes.


import socket
import os
import curses
import time

#==============================================================================
# Symbolic constants
#==============================================================================
DEBUG = False

# Game modes
menuMode = 1
gameMode = 2

# GameEnd states
humanWon = 'C'
cpuWon   = 'S'
drawn    = 'N'
ended    = 'E'

#==============================================================================
# Terminal Display
#==============================================================================
# Terminal modes
draw = 0
normal = 1

#==============================================================================
# Menu
#==============================================================================
# Items to draw
iBanner = 0
iNewGame = 1
iLoadGame = 2
iLoadConfig = 3
iShowScore = 4
iExit = 5

# Pixel map for Banner (16x3) without the 's's at (7,2) & (17,2)
# These cells represented by (col, row) will be lit.
m_Banner = [(0,0), (1,0), (4,0), (5,0), (10,0), (11,0), (12,0), (13,0), (14,0),
    (15,0), (2,1), (3,1), (10,1), (11,1), (14,1), (15,1),
            (0,2), (1,2), (4,2), (5,2), (10,2), (11,2), (12,2), (13,2), (14,2),
    (15,2) ] 


#==============================================================================
# Game
#==============================================================================
# Items to draw
iBoard = 1
iSave = 2
iReserve = 3

#==============================================================================
# BOARD STUFF
#==============================================================================
# int representation
O = 1
X = 0
empty = 2

# "Pixel" maps for all 3 possible squares. 
# For 8x5 squares, these cells represented by (col, row) will be lit.
m_O = [(1,1), (2,1), (3,1), (4,1), (5,1), (6,1),
       (1,2), (2,2),               (5,2), (6,2),
       (1,3), (2,3), (3,3), (4,3), (5,3), (6,3)]

m_X = [(1,1), (2,1),               (5,1), (6,1),
                     (3,2), (4,2),             
       (1,3), (2,3),               (5,3), (6,3)]

m_empty = []

# Winning cross
r1 = 1  # row 1
r2 = 2  # row 2
r3 = 3  # row 3
c1 = 4  # col 1
c2 = 5  # col 2
c3 = 6  # col 3
d1 = 7  # diagonal 1 \
d2 = 8  # diagonal 2 /

# Fill these pixels with '=', '|' , '/' or '\' to draw a cross.
m_crossT = { r1: [(x,2) for x in range(28)],
             r2: [(x,8) for x in range(28)],
             r3: [(x,14) for x in range(28)],
             c1: [(3,y) for y in range(17)]+[(4,y) for y in range(17)],
             c2: [(13,y) for y in range(17)]+[(14,y) for y in range(17)],
             c3: [(23,y) for y in range(17)]+[(24,y) for y in range(17)],
             d1: [(0,0),(1,1),(2,1),(3,2),(4,2),(5,3),(6,3),(7,4),(8,5),(9,5),
                    (10,6),(11,7),(12,7),(13,8),(14,8),(15,9),(16,9),(17,10),
                    (18,11),(19,11),(20,12),(21,13),(22,13),(23,14),(24,14),
                    (25,15),(26,15),(27,16) ],
             d2: [(27,0),(25,1),(26,1),(23,2),(24,2),(21,3),(22,3),(20,4),
                    (18,5),(19,5),(17,6),(15,7),(16,7),(13,8),(14,8),(12,9),
                    (11,9),(10,10),(9,11),(8,11),(7,12),(6,13),(5,13),(4,14),
                    (3,14),(2,15),(1,15),(0,16) ]
            }

#==============================================================================
# Input
#==============================================================================
# Keys
arrowUp = "KEY_UP"
arrowDown = "KEY_DOWN"
arrowLeft = "KEY_LEFT"
arrowRight = "KEY_RIGHT"
returnKey = "\n"

# Game Movements
up = 0
down = 1
left = 2
right = 3
random = 4

#==============================================================================
# Networking
#==============================================================================
timeOutInSecs = 5

# Packet Types
newGame = b"NEWG"       # Start a new game       'NEWG'
endGame = b"ENDG"       # End the current game   'ENDG'
move    = b"MOVE"       # Send a move            'MOVE:<int>,<int>'
board   = b"BORD"       # Get Board from server  'BORD:<i>,<i>,...<i>' (9 <i>s)
loadGame    = b"LOAD"   # Send a game to load    'LOAD:<X/O>,<i>,...<i>'
gameOver    = b"OVER"   # Game is over           'OVER:<C/S/N>,<i>,...<i>'
closeConn   = b"CLOS"   # Close connection       'CLOS'
error   = b"EROR"       # Error                  'EROR:<UNKNOWN CMD/BAD MOVE/
                        #                               NO GAME>'
# Errors
unknownCmd = 0
badMove = 1
noGame = 2

#==============================================================================
# Config
#==============================================================================
configFile = "tictac.ini"

#==============================================================================

class GameManager:
    """ Main class for managing the game states """
    gameMode:int #menuMode/gameMode
    gameOver:bool 

    def __init__(self):
        self.gameMode = None
        self.gameOver = True
        self.__menu = None
        self.__game = None

    def startMenu(self, *args, **kwargs):
        self.__menu = Menu(*args, **kwargs)
        self.gameMode = menuMode
        self.__menu.run()

    def startGame(self, *args, **kwargs):
        self.__game = Game(*args, **kwargs)
        self.gameMode = gameMode
        self.gameOver = False
        self.__game.run()
    
class Menu:
    """ Class for managing and displaying main game menu """
    
    def __init__(self, client):
        self.__client = client
        self.showScore = False
        self.__message = "Use wasd/arrows + Enter/Space + q"

        # Input pointer
        self.__pointer = { iNewGame: True,      # New Game Button
                           iLoadGame: False,    # Load Saved Game button
                           iLoadConfig: False,  # Load config button
                           iShowScore: False,   # ShowScore/HideScore
                           iExit: False         # Exit button
                            }

        # Check config loading
        if not self.__client.cm.configLoaded:
            self.__message = self.__client.cm.errorMessage
            # Check Network connection 
            if not self.__client.nm.connected:
                self.__message += ' + ' + self.__client.nm.errorMessage
        else:
            # Check Network connection 
            if not self.__client.nm.connected:
                self.__message = self.__client.nm.errorMessage

    def run(self):
        """ Main menu loop. """

        while True:
            
            # Draw menu
            self.drawMenu()

            # Wait for Input
            key = self.__client.input.getKey()
            if key == 'q':
                break

            # Process Input
            if self.handleInput(key) == 1:
                break
    
    def drawMenu(self):

        # Clear the previous stuff
        self.__client.display.clear()

        # Draw banner
        self.drawBanner(1,1)

        # Draw options
        self.drawOptions(6,6)

        # Draw a message if any
        if self.__message:
            maxX, maxY = self.__client.display.getDisplayDimensions()
            maxX -= 1
            maxY -= 2 if DEBUG else 1
            self.__client.display.drawText(0, maxY, self.__message,
                                            curses.A_REVERSE)
            self.__message = None

        # Draw A Debug Bar
        if DEBUG:
            maxX, maxY = self.__client.display.getDisplayDimensions()
            maxX -= 1
            maxY -= 1
            self.__client.display.drawText(0, maxY, "Debug Bar: %s" % (
                                            str(self.__pointer[iNewGame])),
                                            curses.A_REVERSE)

        # Render the menu onto screen
        self.__client.display.render()

    def drawBanner(self, x, y):

        # Create pixelMap
        bannerMap = [[(' ', None)]*16 for row in range(3)]

        # Light the 'pixels'
        for row in range(3):
            for col in range(16):
                if (col,row) in m_Banner:
                    bannerMap[row][col] = (' ', curses.A_REVERSE)

        # Draw pixel map
        self.__client.display.drawPixelMap(bannerMap, x, y)

        # Add the 's's
        self.__client.display.drawText(x+7, y+2, 's', curses.A_REVERSE)
        self.__client.display.drawText(x+17, y+2, 's', curses.A_REVERSE)

    def drawOptions(self, x, y):

        # New Game
        if self.__pointer[iNewGame]:
            self.__client.display.drawText(x, y, "New Game", curses.A_REVERSE)
        else:
            self.__client.display.drawText(x, y, "New Game")

        # Load Game
        if self.__pointer[iLoadGame]:
            self.__client.display.drawText(x-3, y+1, "Load Saved Game", 
                                            curses.A_REVERSE)

            # Show Selected Saved Game when no other important message to show.
            if self.__client.cm.saveDirLoaded and self.__message == None:
                if self.__client.cm.selectedGame == None:
                    self.__message = " (None) "
                else:
                    aL = '<'
                    aR = '>'
                    if self.__client.cm.selectedGame == 0:
                        aL = ' '
                    elif self.__client.cm.selectedGame == len(
                                                self.__client.cm.savedGames)-1:
                        aR = ' '
                    if len(self.__client.cm.savedGames) == 1:
                        aR = ' '
                    self.__message = "%s(%s)%s" % (aL, 
                            self.__client.cm.savedGames[(
                                self.__client.cm.selectedGame)], aR)
        else:
            self.__client.display.drawText(x-3, y+1, "Load Saved Game")

        # Load config
        if self.__pointer[iLoadConfig]:
            self.__client.display.drawText(x-1, y+2, "Load Config", 
                                            curses.A_REVERSE)
        else:
            self.__client.display.drawText(x-1, y+2, "Load Config")

        # Show Score/Hide Score
        text = "Hide Score" if self.showScore else "Show Score"
        if self.__pointer[iShowScore]:
            self.__client.display.drawText(x, y+3, text, 
                                            curses.A_REVERSE)
        else:
            self.__client.display.drawText(x, y+3, text)

        # Exit
        if self.__pointer[iExit]:
            self.__client.display.drawText(x+3, y+4, "Exit", 
                                            curses.A_REVERSE)
        else:
            self.__client.display.drawText(x+3, y+4, "Exit")

    def handleInput(self, iKey):

        # Movements
        if iKey == arrowDown or iKey == 's':
            self.movePointer(down)
        elif iKey == arrowUp or iKey == 'w':
            self.movePointer(up)
        elif iKey == arrowRight or iKey == 'd':
            self.movePointer(right)
        elif iKey == arrowLeft or iKey == 'a':
            self.movePointer(left)

        # Enter/Space
        elif iKey == returnKey or iKey == ' ':
            return self.processReturnKey()

    def movePointer(self, pDir):

        if pDir == down:
    
            # Wrap at last option
            if self.__pointer[iExit] == True:
                self.__pointer[iNewGame] = True
                self.__pointer[iExit] = False
                return

            for item in self.__pointer:
                if self.__pointer[item] == True:
                    self.__pointer[item+1] = True
                    self.__pointer[item] = False
                    return

        elif pDir == up:

            # Wrap at first option
            if self.__pointer[iNewGame] == True:
                self.__pointer[iNewGame] = False
                self.__pointer[iExit] = True
                return

            for item in self.__pointer:
                if self.__pointer[item] == True:
                    self.__pointer[item-1] = True
                    self.__pointer[item] = False
                    return

        elif pDir == right:

            # iLoadGame
            if self.__pointer[iLoadGame] == True:
                
                # Switch b/w saved Games
                if self.__client.cm.saveDirLoaded:
                    if self.__client.cm.selectedGame != None:
                        self.__client.cm.selectedGame += 1
                        if self.__client.cm.selectedGame == len(
                                self.__client.cm.savedGames):
                            self.__client.cm.selectedGame = 0

        elif pDir == left:

            # iLoadGame
            if self.__pointer[iLoadGame] == True:
                
                # Switch b/w saved Games
                if self.__client.cm.saveDirLoaded:
                    if self.__client.cm.selectedGame != None:
                        self.__client.cm.selectedGame -= 1
                        if self.__client.cm.selectedGame == -1:
                            self.__client.cm.selectedGame = len(
                                    self.__client.cm.savedGames)-1
                    


    def processReturnKey(self):
        """ Execute the function corresponding to current selection. 
            Returns 1 if function is exiting from Menu otherwise None.
        """

        if self.__pointer[iNewGame]:
            self.newGame()

        elif self.__pointer[iLoadGame]:
            self.loadGame()

        elif self.__pointer[iLoadConfig]:
            self.loadConfig()

        elif self.__pointer[iShowScore]:
            self.toggleScore()

        elif self.__pointer[iExit]:
            return self.exit()

    def newGame(self):

        # Check network connection
        if not self.__client.nm.connected:
            if not self.__client.nm.connect(self.__client.cm.getServAddr()):
                self.__message = self.__client.nm.errorMessage
                return

        # Send newGame to server
        if not self.__client.nm.sendNewGame():
            self.__message = self.__client.nm.errorMessage
            return

        # Receive Board from server
        packet = self.__client.nm.recv()
        if packet == None:
            self.__message = self.__client.nm.errorMessage
            return
        packType = packet[0]
        payload = packet[1]
        if packType == error:
            if payload == unknownCmd:
                self.__message = "Invalid packet sent to server"
            elif payload == badMove:
                self.__message = "Bad move sent to server"
            elif payload == noGame:
                self.__message = "Move sent without initializing game"
            return
        if packType != board:
            self.__message = "Wrong reply received. Was excepting 'BORD'."
            return
        boardList = Board.convertTo2D(payload)

        boardObj = Board(boardList)
        turn = X if boardObj.isEmpty() else O

        # Start a Game from board received
        self.__client.gm.startGame(boardObj, turn, self.showScore, 
                                    self.__client)

    def loadGame(self):

        # Load Selected saved game
        loadedGame = self.__client.cm.loadSelectedGame()
        if loadedGame == None:
            self.__message = self.__client.cm.errorMessage
            return

        # Check network connection
        if not self.__client.nm.connected:
            if not self.__client.nm.connect(self.__client.cm.getServAddr()):
                self.__message = self.__client.nm.errorMessage
                return
        
        # Send the loaded game to server
        if not self.__client.nm.sendLoadGame(*loadedGame):
            self.__message = self.__client.nm.errorMessage
            return

        # Receive Board from server
        packet = self.__client.nm.recv()
        if packet == None:
            self.__message = self.__client.nm.errorMessage
            return
        packType = packet[0]
        payload = packet[1]
        if packType == error:
            if payload == unknownCmd:
                self.__message = "Invalid packet sent to server"
            elif payload == badMove:
                self.__message = "Bad move sent to server"
            elif payload == noGame:
                self.__message = "Move sent without initializing game"
            return
        if packType != board:
            self.__message = "Wrong reply received. Was excepting 'BORD'."
            return
        boardList = Board.convertTo2D(payload)

        boardObj = Board(boardList)
        turn = loadedGame[0]

        # Start a Game from board received
        self.__client.gm.startGame(boardObj, turn, self.showScore, 
                                    self.__client)


    def loadConfig(self):
        self.__client.cm.loadConfigFile(configFile)
        if self.__client.cm.configLoaded:
            self.__message = "Config loaded successfully."
        else:
            self.__message = self.__client.cm.errorMessage

    def toggleScore(self):
        self.showScore = not self.showScore

    def exit(self):
        return 1


class Game:
    """ Class for managing and displaying the actual game. """

    def __init__(self, board, turn, showScore ,client):
        self.__client = client
        self.board = board
        self.turn = turn
        self.showScore = showScore
        self.gameOver = False
        self.gameEnd = None
        self.__message = "Use wasd/arrows + Enter/Space + q"

        # Input Pointer
        self.__pointer = { iBoard: (0,0),  # Board       - (x,y) / False
                           iSave: False,  # SaveButton  - True / False
                           iReserve: False   # reserved    - True / False
                           }

        # Set pointer to an empty square
        if not self.board.isEmpty():
            self.movePointer(random)

    def run(self):
        """ Main Game loop. """

        while True:

            # Draw the Game
            self.drawGame()

            # Wait for Input
            key = self.__client.input.getKey()
            if key == 'q':
                if not self.gameOver:
                    self.end(ended)
                break

            # Process Input
            if self.handleInput(key) == 1:
                break

    def drawGame(self):

        # Clear the previous stuff
        self.__client.display.clear()

        # Draw the board.
        self.drawBoard(2,1)

        # Draw Scores
        if self.showScore:
            scores = self.__client.cm.calcScores()
            self.__client.display.drawText(39,7, "Scores", curses.A_UNDERLINE)
            self.__client.display.drawText(37,8, "Player : %s" % scores[0])
            self.__client.display.drawText(37,9, "Draws  : %s" % scores[1])
            self.__client.display.drawText(37,10, "CPU    : %s" % scores[2])

        # Draw Save button
        self.drawSaveButton(13,19)

        # Draw a message if any
        if self.__message:
            maxX, maxY = self.__client.display.getDisplayDimensions()
            maxX -= 1
            maxY -= 2 if DEBUG else 1
            self.__client.display.drawText(0, maxY, self.__message,
                                            curses.A_REVERSE)
            self.__message = None

        # Draw A Debug Bar
        if DEBUG:
            maxX, maxY = self.__client.display.getDisplayDimensions()
            maxX -= 1
            maxY -= 1
            self.__client.display.drawText(0, maxY, "Debug Bar: %s" % (
                                            str(self.__pointer[iSave])),
                                            curses.A_REVERSE)

        # Render the game onto screen
        self.__client.display.render()

    def drawBoard(self, bx, by):

        # Get board pixel map
        boardMap = self.board.createBoardMap()

        # Highlight input pointer
        if self.__pointer[iBoard] != False:
            sq_row, sq_col = self.__pointer[iBoard]

            if self.board.board[sq_row][sq_col] != empty:
                raise Exception("Game.drawBoard(): pointer at occupied pos")

            m_sq = m_O if self.turn == O else m_X
            Board.fillSquare(sq_row, sq_col, m_sq, boardMap, (curses.A_REVERSE 
                                                              | curses.A_DIM))


        # Draw the cross
        if self.gameOver:
            if self.gameEnd == humanWon or self.gameEnd == cpuWon:
                Board.addCross(self.board.winLine(), boardMap)
       
        # Draw the board
        self.__client.display.drawPixelMap(boardMap, bx, by)

    def drawSaveButton(self, x, y):
        
        if self.gameOver:
            text = "(Menu)"
        else:
            text = "(Save)"

        if self.__pointer[iSave]:
            self.__client.display.drawText(x, y, text, curses.A_REVERSE)
        else:
            self.__client.display.drawText(x, y, text)


    def handleInput(self, iKey):
        
        # Movements
        if iKey == arrowDown or iKey == 's':
            self.movePointer(down)
        elif iKey == arrowUp or iKey == 'w':
            self.movePointer(up)
        elif iKey == arrowRight or iKey == 'd':
            self.movePointer(right)
        elif iKey == arrowLeft or iKey == 'a':
            self.movePointer(left)

        # Enter/Space
        elif iKey == returnKey or iKey == ' ':
            return self.processReturnKey()
    
    def movePointer(self, pDir):

        if self.gameOver:
            return

        if pDir == down:
            if self.__pointer[iBoard] != False:
                pRow, pCol = self.__pointer[iBoard]

                if pRow == 2:   # Already at edge
                    self.__pointer[iSave] = True
                    self.__pointer[iBoard] = False
                    return

                # Find an empty sq at a lower row
                # For same/leftward cols
                for col in range(pCol, -1, -1):
                    for row in range(pRow+1, 3):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return
                # For diff col towards right
                for col in range(pCol+1, 3):
                    for row in range(pRow+1, 3):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return

                # No empty sq below
                self.__pointer[iSave] = True
                self.__pointer[iBoard] = False
                return

            elif self.__pointer[iSave] == True:
                for row in range(3):
                    for col in range(3):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            self.__pointer[iSave] = False
                            return
                return

        elif pDir == up:
            if self.__pointer[iBoard] != False:
                pRow, pCol = self.__pointer[iBoard]

                if pRow == 0:   # Already at edge
                    self.__pointer[iSave] = True
                    self.__pointer[iBoard] = False
                    return

                # Find an empty sq at a upper row
                # For same/leftward cols
                for col in range(pCol, -1, -1):
                    for row in range(pRow-1, -1, -1):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return
                # For diff col towards right
                for col in range(pCol+1, 3):
                    for row in range(pRow-1, -1, -1):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return

                # No empty sq above
                self.__pointer[iSave] = True
                self.__pointer[iBoard] = False
                return

            elif self.__pointer[iSave] == True:
                for row in range(2,-1,-1):
                    for col in range(2,-1,-1):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            self.__pointer[iSave] = False
                            return
                return

        elif pDir == left:
            if self.__pointer[iBoard] != False:
                pRow, pCol = self.__pointer[iBoard]

                if pCol == 0:   # Already at edge
                    return

                # Find an empty sq at a lower col
                # For same/lower rows
                for row in range(pRow, -1, -1):
                    for col in range(pCol-1, -1, -1):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return
                # For diff higher row 
                for row in range(pRow+1, 3):
                    for col in range(pCol-1, -1, -1):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return

                # No empty sq leftward
                return

            elif self.__pointer[iSave] == True:
                return

        elif pDir == right:
            if self.__pointer[iBoard] != False:
                pRow, pCol = self.__pointer[iBoard]

                if pCol == 2:   # Already at edge
                    return

                # Find an empty sq at a higher col
                # For same/lower rows
                for row in range(pRow, -1, -1):
                    for col in range(pCol+1, 3):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return
                # For diff higher row 
                for row in range(pRow+1, 3):
                    for col in range(pCol+1, 3):
                        if self.board.board[row][col] == empty:
                            self.__pointer[iBoard] = (row, col)
                            return

                # No empty sq towards right
                return

            elif self.__pointer[iSave] == True:
                return

        elif pDir == random:

            for sq_row in range(len(self.board.board)):
                for sq_col in range(len(self.board.board[0])):
                    if self.board.board[sq_row][sq_col] == empty:
                        self.__pointer[iBoard] = (sq_row, sq_col)
                        return

            # No empty sq
            self.__pointer[iSave] = True
            self.__pointer[iBoard] = False
            return
                        

    def processReturnKey(self):
        """ Execute the function corresponding to current selection. 
        """
        # Inside Board
        if self.__pointer[iBoard] != False:
            row, col = self.__pointer[iBoard]

            self.move(row, col)

        elif self.__pointer[iSave]:
            return self.saveGame()

    def move(self, row, col):
        
        # Update the board
        self.board.move(self.turn, row, col)
        self.__pointer[iBoard] = False
        self.drawGame()
        
        # Send Move to server
        self.__client.nm.sendMove(row,col)

        # Get Reply from server
        packet = self.__client.nm.recv()
        if packet == None:
            self.__message = self.__client.nm.errorMessage
            # End Game
            self.end(ended)
            return
        packType = packet[0]
        payload = packet[1]
        if packType == error:
            if payload == unknownCmd:
                self.__message = "Invalid packet sent to server"
            elif payload == badMove:
                self.__message = "Bad move sent to server"
            elif payload == noGame:
                self.__message = "Move sent without initializing game"
            # End Game
            self.end(ended)
            return
        if packType != board and packType != gameOver:
            self.__message = "Wrong reply. Was excepting 'BORD'|'OVER'."
            # End Game
            self.end(ended)
            return

        if packType == gameOver:
            self.end(payload[0])
            payload = payload[1]

        boardGrid = Board.convertTo2D(payload)

        # Update Board from reply
        self.board = Board(boardGrid)

        # Move pointer to an random empty square if the game's not over.
        if not self.gameOver:
            self.movePointer(random)

    def end(self, gameEnd):
        self.gameOver = True
        self.__client.gm.gameOver = True
        self.gameEnd = gameEnd
        # Move the pointer to Save/Menu button
        self.__pointer[iSave] = True
        self.__pointer[iBoard] = False

        # Update Score
        if self.gameEnd in [humanWon, cpuWon, drawn]:
            if not self.__client.cm.saveScore(self.gameEnd):
                self.__message = self.__client.cm.errorMessage
                return
            else:
                if self.gameEnd == humanWon:
                    self.__message = " You Win! :) "
                elif self.gameEnd == drawn:
                    self.__message = " Draw. "
                else:
                    self.__message = " You Lost! :( "


    def saveGame(self):

        # Menu function
        if self.gameOver:
            return 1

        # Save function
        if self.__client.cm.saveGame(self.turn, 
                                    Board.linearize(self.board.board)):
            self.end(ended)
        else:
            self.__message = self.__client.cm.errorMessage



class Board:
    """ Class for representing game Board. 
        A board occupies 28x17 char-cells in total.
    """
    
    def __init__(self, board=None):
        if board == None:

            # Initialize an empty board
            self.board = [[empty]*3 for row in range(3)]

        elif (len(board) == 3 and len(board[0]) == 3):
            for row in range(3):
                for col in range(3):
                    if type(board[row][col]) != int:
                        raise Exception(
                                "Board.__init__(): invalid board passed")

            self.board = board

        else:
            raise Exception("Board.__init__(): invalid board passed")

    def isEmpty(self):
        for sq_row in range(len(self.board)):
            for sq_col in range(len(self.board[0])):
                if self.board[sq_row][sq_col] != empty:
                    return False
        return True

    @staticmethod
    def convertTo2D(boardList):
        """ Convert linear board representation int[9] to grid one int[3][3].
        """
        return [ boardList[:3],  # First row
                 boardList[3:6], # Second row
                 boardList[6:]   # Third row
                 ]

    @staticmethod
    def linearize(boardGrid):
        """ Convert grid board representation int[3][3] to linear one int[9]. 
        """
        lBoard = []
        for row in range(3):
            lBoard += boardGrid[row]
        return lBoard

    def winLine(self):
        """ Returns row, col or diagonal across which the win occurs """
        
        # Rows
        for row in range(3):
            for col in range(3):
                if self.board[row][col] == empty:
                    break
                if self.board[row][0] != self.board[row][col]:
                    break
            else:
                return row+1
        # Cols
        for col in range(3):
            for row in range(3):
                if self.board[row][col] == empty:
                    break
                if self.board[0][col] != self.board[row][col]:
                    break
            else:
                return col+4

        # Diagonals
        # d1
        if self.board[0][0] != empty:
            if self.board[0][0] == self.board[1][1] == self.board[2][2]:
                return d1
        # d2
        if self.board[2][0] != empty:
            if self.board[2][0] == self.board[1][1] == self.board[0][2]:
                return d2


    def move(self, shape, row, col):
        """ Moves shape(O/X) to row,col """

        if (row < 0 or row > 2) or (col < 0 or col > 2):
            raise Exception("Board.move(): invalid move position.")
        if not (shape == O or shape == X):
            raise Exception("Board.move(): invalid shape.")

        if self.board[row][col] != empty:
            raise Exception("Board.move(): position already occupied.")

        self.board[row][col] = shape

    
    def createBoardMap(self):
        """ Takes a 3x3 board 2d-array and returns a 28x17 char-cell grid with
            each cell value & attributes as (value, attrs).
        """

        # Initialize an empty board "pixel" map.
        boardMap = [[(" ", None)]*28 for row in range(17)]

        # Add square separating margins
        # Vertical margins
        for col in [8,9,18,19]:
            for row in range(17):
                boardMap[row][col] = (" ", curses.A_REVERSE)
        # Horizontal Margins
        for row in [5,11]:
            for col in range(28):
                boardMap[row][col] = (" ", curses.A_REVERSE)

        # Fill in squares
        for sq_row in range(len(self.board)):
            for sq_col in range(len(self.board[0])):

                # Ignore empty
                if self.board[sq_row][sq_col] == empty:
                    continue
                elif self.board[sq_row][sq_col] == O:
                    m_sq = m_O
                elif self.board[sq_row][sq_col] == X:
                    m_sq = m_X

                # Paint the square
                Board.fillSquare(sq_row, sq_col, m_sq, boardMap, 
                                    curses.A_REVERSE)
        
        return boardMap
                
    @staticmethod
    def fillSquare(row, col, m_sq, boardMap, attr):
        """ Fill an particular square with pixel map `m_sq` """
        
        # Translate 3x3 board's (row,col) to 28x17 pixelMap's row,col
        # sq_width+margin = 10
        # sq_height+margin = 6
        pMapRow, pMapCol = (row*6, col*10)

        # Draw a dim highlighted move in this square
        for m_row in range(pMapRow, pMapRow+5):
            for m_col in range(pMapCol, pMapCol+8):
                
                # Transform m_row,m_col relative to row,col
                r_row = m_row - pMapRow
                r_col = m_col - pMapCol

                # Dim Light the cell
                if (r_col, r_row) in m_sq:
                    boardMap[m_row][m_col] = (" ", attr )
        
    @staticmethod
    def addCross(line, boardMap):

        if line == None:
            return

        # Across row
        if line >= 1 and line <= 3:
            crossCh = "="

        # Across col
        elif line >= 4 and line <= 6:
            crossCh = "|"
        
        # Across diagonal
        # d1
        elif line == d1:
            crossCh = "\\"
        # d2
        elif line == d2:
            crossCh = "/"


        # Set cross chars
        for pRow in range(len(boardMap)):
            for pCol in range(len(boardMap[0])):
                if (pCol, pRow) in m_crossT[line]:
                    boardMap[pRow][pCol] = (crossCh, boardMap[pRow][pCol][1])

class NetworkManager:
    """ Class for managing networking with server """
    serverAddr:tuple    # (IP_addr, port) for server
    conn:socket.socket  # Socket connected to game server
    connected:bool
    errorMessage:str    # Error message for connection 

    def __init__(self, serverAddr):
        self.serverAddr = serverAddr
        self.conn = None
        self.connected = False
        self.errorMessage = "Server Connection not initialized"

        self.connect(self.serverAddr)


    def connect(self, serverAddr):

        # Create a connected socket with game server
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(timeOutInSecs)
        try:
            self.conn.connect(serverAddr)
        except socket.timeout:
            self.errorMessage = (
                        "Unable to connect to server: Connection timeout")
            self.connected = False
        except socket.gaierror:
            self.errorMessage = "Unable to connect to server: socket.gaierror"
            self.connected = False
        except OSError:
            self.errorMessage = "Unable to connect to server"
            self.connected = False
        else:
            self.errorMessage = None
            self.connected = True

    def __del__(self):

        # Gracefully disconnect
        if self.connected:
            self.sendClose()

            packet = self.recv()
            if packet != None and packet[0] != closeConn:
                self.__flush()

            self.conn.close()
            self.connected = False

    def __flush(self):
        """ Recv and discard 4096 bytes from recv stream. """
        if not self.connected:
            return

        # Set socket to non-blocking mode
        timeout = self.conn.gettimeout()
        self.conn.settimeout(0.0)

        try:
            self.conn.recv(4096)
        except (socket.timeout, socket.error):
            return
        finally:
            # Revert to timeout blocking move
            self.conn.settimeout(timeout)

    def send(self, packType, payload:str):
        """ Send a packet of type `packType` and payload `payload` in format
            'packType:payload' to the server.
            Return None on success or raised an error.
        """
        self.conn.sendall(packType)
        if payload != None:
            self.conn.sendall(b":"+bytes(payload,"UTF-8"))

    def sendNewGame(self):
        """ Send NewGame packet ('NEWG') to server. 
            Returns False on failure/ True on success
        """
        if not self.connected:
            raise Exception("nm: sendNewGame()- No connection established")

        # Flush the network buffer
        self.__flush()

        try:
            self.conn.sendall(newGame)
        except OSError:
            self.errorMessage = "Error while trying to send to server"
            return False
        
        return True

    def sendEndGame(self):
        """ Send endGame packet ('ENDG') to server. 
            Returns False on failure/ True on success
        """
        if not self.connected:
            raise Exception("nm: sendEndGame()- No connection established")

        try:
            self.conn.sendall(endGame)
        except OSError:
            self.errorMessage = "Error while trying to send to server"
            return False
        
        return True

    def sendMove(self, row, col):
        """ Send move packet ('MOVE:x,y') to server. 
            Returns False on fail/ True on success
        """
        if not self.connected:
            raise Exception("nm: sendMove()- No connection established")

        payload = bytes(f"{row},{col}", "UTF-8")
        try:
            self.conn.sendall(move+b':'+payload)
        except OSError:
            self.errorMessage = "Error while trying to send to server"
            return False
        
        return True
    
    def sendLoadGame(self, turn, board):
        """ Send loadGame packet ('LOAD:t,i,i,i,i,i,i,i,i,i') to server. 
            Returns False on fail/ True on success
        """
        if not self.connected:
            raise Exception("nm: sendLoadGame()- No connection established")

        if turn == O:
            turn = 'O'
        elif turn == X:
            turn = 'X'
        else:
            raise Exception("nm: sendLoadGame()- Invalid `turn`")

        boardStr = ",".join(str(i) for i in board)
        payload = bytes(f"{turn},{boardStr}", "UTF-8")
        try:
            self.conn.sendall(loadGame+b':'+payload)
        except OSError:
            self.errorMessage = "Error while trying to send to server"
            return False
        
        return True

    def sendClose(self):
        """ Send closeConn packet ('CLOS') to server. 
            Returns False on fail/ True on success
        """
        if not self.connected:
            raise Exception("nm: sendClose()- No connection established")

        try:
            self.conn.sendall(closeConn)
        except OSError:
            self.errorMessage = "Error while trying to send to server"
            return False
        
        return True

    def recv(self):
        """ Recieves a packet from server and returns (PackType, Payload) 
            Return None on failure.
            - PackType      Payload
               error        unknownCmd|badMove|noGame
               board         int[9]
               gameOver     (result, int[9])
               closeConn     None
        """
        if not self.connected:
            raise Exception("nm: recv()- No connection established")

        try:
            # PackType
            packType = self.conn.recv(4)

            if packType == b'': # Connection closed
                self.errorMessage = (
                        "Connection closed by server while receiving")
                return None

            elif packType == error:
                # Payload Seperator
                if self.recvSep() == None:
                    return None

                # Payload
                payload = self.recvError()
                if payload == b"UNKNOWN CMD":
                    return (error, unknownCmd)
                elif payload == b"BAD MOVE":
                    return (error, badMove)
                elif payload == b"NO GAME":
                    return (error, noGame)
                elif payload == b'':
                    self.errorMessage = (
                            "Connection closed by server while receiving")
                    return None
                else:
                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None

            elif packType == board:
                # Payload Seperator
                if self.recvSep() == None:
                    return None

                # Payload
                payload = self.recvBoard()
                if payload == b'':
                    self.errorMessage = (
                            "Connection closed by server while receiving")
                    return None
                if len(payload) != 17:
                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None

                payloadStr = str(payload, "UTF-8")
                payloadList = payloadStr.split(",")
                if len(payloadList) != 9:
                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None
                # Convert str list to int list
                try:
                    payload = [int(i) for i in payloadList]
                except ValueError:
                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None

                return (board, payload)

            elif packType == gameOver:
                # Payload Seperator
                if self.recvSep() == None:
                    return None

                # Payload
                payload = self.recvGameOver()
                if payload == b'':
                    self.errorMessage = (
                            "Connection closed by server while receiving")
                    return None
                if len(payload) != 19:
                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None

                payloadStr = str(payload, "UTF-8")
                result, payloadStr = payloadStr.split(",", maxsplit=1)
                payloadList = payloadStr.split(",")
                if result not in (humanWon, cpuWon, drawn) or (
                    len(payloadList) != 9):

                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None
                # Convert str list to int list
                try:
                    payload = [int(i) for i in payloadList]
                except ValueError:
                    self.errorMessage = "Error while receiving from server"
                    self.__flush()
                    return None

                return (gameOver, (result,payload))

            elif packType == closeConn:
                return (closeConn, None)

        except socket.timeout:
            self.errorMessage = "Timeout Error while receiving from server"
            return None



    def recvSep(self):
        """ Receives payload separator ':'
            Returns None on failure.
        """

        # Payload Separator
        sep = self.conn.recv(1)
        if sep != b':': # Corrupted Stream
            self.errorMessage = "Error while receiving from server"
            return None
        if sep == b'': # Connection closed
            self.errorMessage = (
                    "Connection closed by server while receiving")
            return None

        return sep

    def recvError(self):
        """ Receives payload for the 'EROR' packet type. """
        readBytes = 1
        byte = self.conn.recv(readBytes)
        if byte == b'U':
            readBytes = 10
        elif byte == b'B':
            readBytes = 7
        elif byte == b'N':
            readBytes = 6
        elif byte == b'':
            readBytes = 0
        payload = byte + self.conn.recv(readBytes)
        return payload

    def recvBoard(self):
        """ Receives payload for the 'BORD' packet type. """
        return self.conn.recv(17)

    def recvGameOver(self):
        """ Receives payload for the 'OVER' packet type. """
        return self.conn.recv(19)



class InputManager:
    """ Class for managing user input from console """
    
    def __init__(self, term):
        self.__terminal = term

    def getKey(self):
        """ Retrives the key pressed in draw mode as str.
            Note: This function will wait till a key is pressed.
        """
        assert self.__terminal.mode == draw
        return self.__terminal.getScreen().getkey()

    def input(prompt):
        """ Take input from console (normal mode) after prompt."""
        if self.__terminal.mode == draw:
            raise Exception("Input - input(): called in draw mode") 

        return input(prompt)


class DisplayManager:
    """ Class for managing the output display. """
    displayMode:int # draw/normal

    def __init__(self, term, displayMode=draw):
        self.__terminal = term

        # Set display mode to draw
        self.__terminal.setMode(draw)
        self.displayMode = draw

    def getDisplayDimensions(self):
        """ Returns (numOfRows, numOfColumns) in the display """
        assert self.displayMode == draw
        y,x = self.__terminal.getScreen().getmaxyx()
        return (x,y)

    def drawPixelMap(self, pMap, o_x, o_y):
        """ Draw a 2d pixel map onto screen with origin at (o_x,o_y).
            - pMap: a 2d-list with element format (pixelChar, pixelAttr)
        """
        if o_x < 0 or o_y < 0:
            raise Exception("Display: drawPixelMap - invalid origin coords")

        n_rows = len(pMap)
        n_cols = len(pMap[0])

        stdscr = self.__terminal.getScreen()

        # y is row no. and x is col no.
        for y in range(n_rows):
            for x in range(n_cols):
                char, attr = pMap[y][x]
                maxyx = stdscr.getmaxyx()
                if (o_y+y) >= maxyx[0] or (o_x+x) >= maxyx[1]:
                    continue
                if attr == None:
                    stdscr.addch(o_y+y, o_x+x, char)
                else:
                    stdscr.addch(o_y+y, o_x+x, char, attr)

    def drawText(self, x, y, text, attr=None):

        stdscr = self.__terminal.getScreen()
        for ch in text:
            maxyx = stdscr.getmaxyx()
            if y >= maxyx[0] or x >= maxyx[1]:
                break
            if attr == None:
                stdscr.addch(y, x, ch)
            else:
                stdscr.addch(y, x, ch, attr)
            x += 1
    
    def clear(self):
        """ Clear the previous stuff drawn to screen. """
        self.__terminal.getScreen().erase()

    def render(self):
        """ Render the stuff drawn on screen. """
        self.__terminal.getScreen().refresh()

    def printToConsole(*args, **kwargs):
        """ Print to console when in normal mode """

        if self.displayMode == draw:
            raise Exception("Display - printToConsole(): called in draw mode") 

        print(*args, **kwargs)


class Terminal:
    """ Class for handling terminal window. """
    mode:int # Terminal mode - draw/normal

    def __init__(self, mode=draw):
        self.__stdscr = None
        self.mode = normal
        self.setMode(mode)

    def __del__(self):
        self.setMode(normal)
    
    def setMode(self, mode):
        
        if mode == draw and self.mode == normal:
            self.__initScr()
        elif mode == normal and self.mode == draw:
            self.__endWin()

        self.mode = mode

    def getScreen(self):
        """ Returns the window object for the terminal. 
            NOTE: Make sure to call it only if Terminal is in draw mode.
        """

        # Terminal in normal mode
        if self.__stdscr == None:
            raise Exception(
                    "Terminal:self.getScreen(): called in normal mode") 

        return self.__stdscr

    
    def __initScr(self):
        """ Init curses library and set screen object __stdscr. """

        assert self.__stdscr == None # Mode is normal

        # Initialize curses library
        self.__stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.__stdscr.keypad(True)

    def __endWin(self):
        """ Deinit curses library and unset __stdscr object. """

        assert self.mode == draw

        # Restore terminal settings and deinit curses library.
        curses.echo()
        curses.nocbreak()
        self.__stdscr.keypad(False)
        curses.curs_set(True)
        curses.endwin()
        self.__stdscr = None


class ConfigManager:
    """ Class to read and write config for the game """
    configLoaded:bool  # Config is fully loaded
    scoreLoaded:bool
    saveDirLoaded:bool

    def __init__(self, configfile):

        self.loadConfigFile(configfile)

    def calcScores(self):
        """ Reads scoreFile and return (playerWins, draws, cpuWins) within 
            score filter.
        """
        if not self.scoreLoaded:
            return (None, None, None)

        scores = [0,0,0]
        with open(self.__scoreFile, 'r') as f:
            for line in f:
                line = line.strip()
                fields = line.split()
                if len(fields) != 2:
                    continue
                if fields[0] not in [humanWon, drawn, cpuWon]:
                    continue
                try:
                    time = float(fields[1])
                except ValueError:
                    continue

                if time > self.__scoreFrom and time < self.__scoreTo:
                    if fields[0] == humanWon:
                        scores[0] += 1
                    elif fields[0] == drawn:
                        scores[1] += 1
                    elif fields[0] == cpuWon:
                        scores[2] += 1
        return scores

    def saveScore(self, score):
        """ Append 'playerWon|drawn|cpuWon <timestamp> to score file. 
            Return False on error.
        """
        if not self.scoreLoaded:
            self.errorMessage = "ScoreFile not loaded"
            return False
        
        if score not in [humanWon, cpuWon, drawn]:
            raise Exception("cm:saveScore() - invalid score passed")

        try:
            with open(self.__scoreFile, 'a') as f:
                f.write(score)
                f.write(' ')
                f.write(str(int(time.time())))
                f.write('\n')

            return True
        except OSError:
            self.errorMessage = "Unable to update Score"
            return False


    def loadSelectedGame(self):
        """ Returns (turn, board[9]) for the saved game. 
            Otherwise None on error.
        """
        if not self.saveDirLoaded:
            self.errorMessage = "saveDir not loaded"
            return None

        if self.selectedGame == None:
            self.errorMessage = "No saved Games to load"
            return None

        try:
            with open(os.path.join(self.__saveDir, 
                        self.savedGames[self.selectedGame]), 'r') as f:
                rawGame = f.read()
                rawGame = rawGame.strip()
                fields = rawGame.split()
                if len(fields) != 2:
                    self.errorMessage = "Corrupted Save File"
                    return None
                try:
                    turn = int(fields[0])
                except ValueError:
                    self.errorMessage = "Corrupted Save File"
                    return None
                else:
                    if turn not in [O,X]:
                        self.errorMessage = "Corrupted Save File"
                        return None
                boardList = fields[1].split(",")
                if len(boardList) != 9:
                    self.errorMessage = "Corrupted Save File"
                    return None

                try:
                    boardList = [int(s) for s in boardList]
                except ValueError:
                    self.errorMessage = "Corrupted Save File"
                    return None

                return (turn, boardList)

        except OSError:
            self.errorMessage = "Couldn't load Save File"
            return None


    def saveGame(self, turn, board):
        """ Returns False on failure. 
            Note: board is int[9]
        """
        if not self.saveDirLoaded:
            self.errorMessage = "saveDir not loaded"
            return False
        
        saveNo = len(self.savedGames)
        saveName = f"save{saveNo}"

        try:
            with open(os.path.join(self.__saveDir, saveName), 'w') as f:
                f.write(str(turn))
                f.write(' ')
                f.write(",".join(str(i) for i in board))
            
            if len(self.savedGames) == 0:
                self.selectedGame = 0
            self.savedGames.append(saveName)
            return True

        except OSError as e:
            self.errorMessage = "Couldn't Save File"
            return False

    def getServAddr(self):
        return self.__servAddr

    def loadConfigFile(self, configfile):
        self.configLoaded = False
        self.scoreLoaded = False
        self.saveDirLoaded = False
        self.servAddrLoaded = False
        self.__servAddr = ("localhost", 6969)
        self.__saveDir = None
        self.__scoreFile = None
        self.__scoreFrom = float('-inf')
        self.__scoreTo = float('inf')
        self.savedGames = []
        self.selectedGame = None
        self.errorMessage = "Config not loaded. Trying (localhost, 6969)"

        # Check if config file exists
        if os.path.isfile(configfile):
            try:
                self.parseConfigFile(configfile)
            except OSError:
                self.configLoaded = False
                self.errorMessage = "Config not loaded properly"

        # Scan saveDir
        self.scanSaveDir()

        if self.servAddrLoaded == 2:
            self.servAddrLoaded = True
        if self.scoreLoaded and self.saveDirLoaded and self.servAddrLoaded:
            self.configLoaded = True
            self.errorMessage = None
        else:
            self.errorMessage = "Config not loaded properly"

    def scanSaveDir(self):
        if not self.saveDirLoaded:
            self.savedGames = []
            self.selectedGame = None

        for entry in os.scandir(self.__saveDir):
            if entry.is_file():
                self.savedGames.append(entry.name)

        if len(self.savedGames) != 0:
            self.selectedGame = 0


    def parseConfigFile(self, configfile):
        """ Ignores invalid config lines """
        with open(configfile, 'r') as f:

            cType = None
            for line in f:
                line = line.strip()

                # Ignore comments
                if line[0] == '#':
                    continue

                # Read config type
                if line[0] == '[' and line[-1] == ']':
                    cType = line[1:-1]
                    cType = cType.upper()
                    continue

                # Parse config line
                fields = line.split("=", maxsplit=1)
                if len(fields) != 2:
                    continue
                fields = [field.strip() for field in fields]
                fields[0] = fields[0].lower()
                
                if cType == "BASIC":
                    if fields[0] == 'savedir':
                        self.setSaveDir(fields[1])
                    elif fields[0] == 'score':
                        self.setScoreFile(fields[1])

                elif cType == "NETWORKING":
                    if fields[0] == 'serverip':
                        self.__servAddr = (fields[1], self.__servAddr[1])
                        self.servAddrLoaded += 1
                    elif fields[0] == 'port':
                        try:
                            port = int(fields[1])
                            self.__servAddr = (self.__servAddr[0], port)
                            self.servAddrLoaded += 1
                        except ValueError:
                            continue
                elif cType == "FILTER_SCORE":
                    if fields[0] == 'scoretimefrom':
                        self.setScoreTime("from", fields[1])
                    elif fields[0] == 'scoretimeto':
                        self.setScoreTime("to", fields[1])

    def setSaveDir(self, saveDir):

        # Check if `saveDir` is non-directory
        if os.path.exists(saveDir):
            if not os.path.isdir(saveDir):
                self.errorMessage = (
                        "Couldn't load a file as a saveDir from config")
                self.saveDirLoaded = False
                self.configLoaded = False
                return

        else:  # `saveDir` doesn't exist
            try:
                os.makedirs(saveDir)
            except OSError:
                self.errorMessage = (
                        "Couldn't make saveDir from config")
                self.saveDirLoaded = False
                self.configLoaded = False
                return

        self.saveDirLoaded = True
        self.__saveDir = os.path.normpath(saveDir)

    def setScoreFile(self, scoreFile):

        # Check if `scoreFile` is non-file
        if os.path.exists(scoreFile):
            if not os.path.isfile(scoreFile):
                self.errorMessage = (
                        "Couldn't load a non-file as scoreFile from config")
                self.scoreLoaded = False
                self.configLoaded = False
                return

        else:  # `saveDir` doesn't exist
            try:
                f = open(scoreFile, "w")
                f.close()
            except OSError:
                self.errorMessage = (
                        "Couldn't create a scoreFile from config")
                self.scoreLoaded = False
                self.configLoaded = False
                return

        self.scoreLoaded = True
        self.__scoreFile = scoreFile

        # Make sure we can open for reading
        try:
            f = open(scoreFile, "r")
            f.close()
        except OSError:
            self.scoreLoaded = False

    def setScoreTime(self, which, timeStr):
        try:
            timeStruct = time.strptime(timeStr, "%b %d %H:%M")
        except ValueError:
            if which == 'from':
                self.__scoreFrom = float('-inf')
            elif which == 'to':
                self.__scoreTo = float('inf')
            return

        # To get year field
        localTime = time.localtime()
        scoreTime = (localTime.tm_year, timeStruct.tm_mon, timeStruct.tm_mday,
                        timeStruct.tm_hour, timeStruct.tm_min, 
                        timeStruct.tm_sec, timeStruct.tm_wday, 
                        timeStruct.tm_yday, timeStruct.tm_isdst)

        if which == 'from':
            self.__scoreFrom = time.mktime(scoreTime)
        elif which == 'to':
            self.__scoreTo = time.mktime(scoreTime)

class Client:
    """ Class for managing all the client objects """
    gameManager:GameManager
    menu:Menu
    game:Game
    terminal:Terminal
    display:DisplayManager
    input:InputManager
    nm:NetworkManager

    def __init__(self):
        """ Initialize all needed objects """
        self.terminal = Terminal()
        self.display = DisplayManager(self.terminal)
        self.input = InputManager(self.terminal)
        self.cm = ConfigManager(configFile)
        self.gm = GameManager()
        self.nm = NetworkManager(self.cm.getServAddr())

    def run(self):
        self.gm.startMenu(self)

def test():

    board = Board([[1,0,2],
                   [2,1,2],
                   [2,2,2]])
    boardMap = board.createBoardMap()
    client = Client()
    client.gm.startMenu(client)
    #client.gm.startGame(board, 0, True, client)
    
    #display.drawPixelMap(boardMap, 2, 1)
    #display.drawText(37,7, "Player : 0")
    #display.drawText(37,8, "Draws  : 45")
    #display.drawText(37,9, "CPU    : 23")
    #display.render()

    time.sleep(1)


if __name__ == "__main__":

    cl = Client()
    cl.run()
    


