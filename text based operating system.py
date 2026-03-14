import os
import sys
from utils import data
import time
import random
import test_all
from apps import (
snake,
tetris, 
image, 
screensaver, 
text_editor
)
from apps.screensaver import clear

ANSI_GREEN = "\033[32m"
ANSI_DIM = "\033[2m"
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"
ANSI_CLEAR = "\033[2J\033[H"

computer_ASCII = """
  .---------.
  |.-------.|
  ||>tbos  ||
  ||       ||
  |"-------'|
.-^---------^-.
| ---~        |
"-------------'
"""

def startup():
    print("starting tbos.")
    time.sleep(random.randint(0, 3))
    clear()
    print("starting tbos..")
    time.sleep(random.randint(0, 3))
    clear()
    print("starting tbos...")
    time.sleep(random.randint(0, 3))
    clear()
    test_all.main()

startup()

print(computer_ASCII)

apps = []

if not data.getFileExists("save_data/installed_apps.txt"):
    data.create("save_data/installed_apps", ".txt")
else:
    apps = data.readLine("save_data/installed_apps.txt", 1)


def install_app(app_id, install_text):
    global apps
    if str(app_id) in apps:
        print("app already installed")
        return
    apps += str(app_id)
    if install_text != "":
        print(install_text)

while True:
    inp = input("tbos> ")

    if inp == "exit":
        data.write("save_data/installed_apps.txt", str(apps))
        break

    elif inp == "install snake":
        install_app(1, "installed snake")

    elif inp == "install tetris":
        install_app(2, "installed tetris")

    elif inp == "run snake":
        if "1" in apps:
            snake.snake_main()
        else:
            print("snake not installed yet. install with: install snake")

    elif inp == "run tetris":
        if "2" in apps:
            tetris.tetris()
        else:
            print("tetris not installed yet. install with: install tetris")

    elif inp == "":
        pass

    elif inp == "help":
        print("available commands:")
        print("")
        print("install [app]")
        print("run [app]")
        print("exit")
        print("screensaver")
        print("file write")

    elif inp == "file write":
        text_editor.main()

    elif inp == "install img":
        install_app(3, """        
installed image --> terminal extension!
new commands: 
        
display: opens display submenu
[path]: loads .png files when in the display submenu
      """)

    elif inp == "install all":
        apps += "1"
        apps += "2"
        apps += "3"
        apps += "4"

    elif inp == "display":
        if "3" in apps:
            print("enter file path:")
            inp2 = input("display> ")
            
            if inp2 != "":
                try: 
                    image.display_png_grayscale_ansi256(inp2)
                except:
                    print("could not find image")
        else:
            print("invalid command! see commands with: help")

    elif inp == "neofetch":
        os.system("cls")
        print(computer_ASCII)
        print("Python version: ", sys.version_info[0])
        print("Tbos v. 0.0.1 Beta")
        print("")

    elif inp == "test":
        test_all.main()

    elif inp == "clear":
        clear()

    elif inp == "screensaver":
        screensaver.matrix_screensaver(30, 0.035)

    else:
        print("invalid command! see commands with: help")
