import sys, random, shutil, os, time

def clear():
    os.system("cls")

def _get_keypress_checker():
    """
    Returns a function key_pressed() -> bool that becomes True when user presses any key.
    """
    if os.name == "nt":
        import msvcrt
        def key_pressed():
            return msvcrt.kbhit()
        return key_pressed
    else:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)  # immediate keypress (no Enter)
        def key_pressed():
            r, _, _ = select.select([sys.stdin], [], [], 0)
            return bool(r)
        # also return a cleanup function for terminal state
        def cleanup():
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return key_pressed, cleanup

def matrix_screensaver(fps=30, density=0.035):
    """
    Matrix-themed terminal screensaver.
    Stops when the user presses any key.

    Args:
        fps: frames per second (higher = faster)
        density: spawn chance per column per frame (higher = more rain)
    """
    # ANSI
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    CLEAR = "\033[2J"
    HOME = "\033[H"
    RESET = "\033[0m"

    # Colors (bright head + dim trail)
    GREEN = "\033[32m"
    BRIGHT = "\033[1m"
    DIM = "\033[2m"

    # Character set (Matrix-y)
    charset = "アイウエオカキクケコサシスセソタチツテトナニヌネノ" \
              "ハヒフヘホマミムメモヤユヨラリルレロワヲン" \
              "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Setup keypress handling
    cleanup = None
    if os.name == "nt":
        key_pressed = _get_keypress_checker()
    else:
        key_pressed, cleanup = _get_keypress_checker()

    cols, rows = shutil.get_terminal_size((120, 40))

    # Each column has a drop position;  -1 means inactive
    drops = [-1 for _ in range(cols)]
    speeds = [random.randint(1, 3) for _ in range(cols)]  # how many rows per frame-ish
    tick = [0 for _ in range(cols)]  # per-column timing accumulator

    # We maintain a lightweight "trail" intensity map: dict[(x,y)] = age
    # Age grows each frame; we render younger = brighter.
    trail = {}

    def draw():
        nonlocal cols, rows
        cols, rows = shutil.get_terminal_size((cols, rows))

        # Frame buffer as list of strings for speed
        frame_lines = [" " * cols for _ in range(rows)]
        # We'll overlay characters by building per-line mutable lists
        frame = [list(line) for line in frame_lines]
        style_map = {}  # (x,y)-> style token ("head","trail")

        # Age existing trail (and drop old)
        to_del = []
        for (x, y), age in trail.items():
            age += 1
            if age > 10:   # trail length / fade duration
                to_del.append((x, y))
            else:
                trail[(x, y)] = age
        for k in to_del:
            del trail[k]

        # Spawn/update drops
        for x in range(cols):
            if drops[x] < 0:
                # chance to spawn a new drop
                if random.random() < density:
                    drops[x] = random.randint(-rows, 0)  # start above screen sometimes
                    speeds[x] = random.randint(1, 3)
                    tick[x] = 0
                continue

            tick[x] += 1
            # control speed: only move when tick hits threshold
            if tick[x] < speeds[x]:
                continue
            tick[x] = 0

            drops[x] += 1
            y = drops[x]

            # if it goes off screen, deactivate
            if y > rows + 10:
                drops[x] = -1
                continue

            # Head character (bright)
            if 0 <= y < rows:
                ch = random.choice(charset)
                frame[y][x] = ch
                style_map[(x, y)] = "head"

            # Trail behind head (dim)
            for t in range(1, 12):
                ty = y - t
                if 0 <= ty < rows:
                    # store trail age: younger nearer head
                    trail[(x, ty)] = min(trail.get((x, ty), 10), t)

        # Apply trail rendering
        for (x, y), age in trail.items():
            if 0 <= y < rows and 0 <= x < cols:
                frame[y][x] = random.choice(charset)
                style_map[(x, y)] = "trail"

        # Convert to ANSI output with minimal color switches
        out = [HOME]
        for y in range(rows):
            line_out = []
            current_style = None
            for x in range(cols):
                st = style_map.get((x, y))
                if st != current_style:
                    if st == "head":
                        line_out.append(GREEN + BRIGHT)
                    elif st == "trail":
                        line_out.append(GREEN + DIM)
                    else:
                        line_out.append(RESET)
                    current_style = st
                line_out.append(frame[y][x])
            line_out.append(RESET)
            out.append("".join(line_out))
        return "\n".join(out)

    # Render loop
    try:
        sys.stdout.write(CLEAR + HOME + HIDE_CURSOR)
        sys.stdout.flush()

        while True:
            if key_pressed():
                break
            sys.stdout.write(draw())
            sys.stdout.flush()
            time.sleep(1 / max(1, fps))

    finally:
        # consume the keypress so it doesn't type into your shell after exit
        try:
            if os.name == "nt":
                import msvcrt
                if msvcrt.kbhit():
                    msvcrt.getch()
            else:
                if key_pressed():
                    sys.stdin.read(1)
        except Exception:
            pass

        if cleanup:
            cleanup()
        sys.stdout.write(RESET + SHOW_CURSOR + "\n")
        sys.stdout.flush()
        clear()