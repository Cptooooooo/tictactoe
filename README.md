# tictactoe
A tictactoe client implemented using curses in Python.

The server runs the game logic and a cpu player. It can handle multiple clients at a time and is by default listening at port 6969. The client loads the **tictac.ini** config file to get server address and other info needed for saving games and score.

# Usage
- tictactoeServer

      $ ./tictactoeServer [PORT]
      
- tictacClient

    Make sure the server is running and that the **tictac.ini** file is present in working directory of python.
    
    ```
    $ python3 tictacClient
    ```
Note: This program is written and tested with *python3.9* only.
 

# License
This work is licensed under the Creative Commons Attribution-NonCommercial 3.0 Unported License. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/3.0/ or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
