import os, random, msvcrt, time


def tetris():
    WIDTH = 10
    HEIGHT = 20

    EMPTY = " ."
    BLOCK = "[]"

    TETROMINOS = [
        [[1, 1, 1, 1]],                  # I
        [[1, 1], [1, 1]],                # O
        [[0, 1, 0], [1, 1, 1]],          # T
        [[1, 0, 0], [1, 1, 1]],          # L
        [[0, 0, 1], [1, 1, 1]],          # J
        [[0, 1, 1], [1, 1, 0]],          # S
        [[1, 1, 0], [0, 1, 1]],          # Z
    ]

    def clear_screen():
        os.system("cls")

    def rotate_clockwise(piece):
        return [list(row) for row in zip(*piece[::-1])]

    def collision(board, piece, px, py):
        for y, row in enumerate(piece):
            for x, cell in enumerate(row):
                if not cell:
                    continue
                bx = px + x
                by = py + y
                if bx < 0 or bx >= WIDTH or by < 0 or by >= HEIGHT:
                    return True
                if board[by][bx]:
                    return True
        return False

    def merge(board, piece, px, py):
        for y, row in enumerate(piece):
            for x, cell in enumerate(row):
                if cell:
                    board[py + y][px + x] = 1

    def clear_lines(board):
        kept = []
        cleared = 0
        for row in board:
            if all(row):
                cleared += 1
            else:
                kept.append(row)
        while len(kept) < HEIGHT:
            kept.insert(0, [0] * WIDTH)
        return kept, cleared

    def spawn_piece():
        piece = random.choice(TETROMINOS)
        px = WIDTH // 2 - len(piece[0]) // 2
        py = 0
        return piece, px, py

    def hard_drop(board, piece, px, py):
        while not collision(board, piece, px, py + 1):
            py += 1
        return py

    def draw(board, piece, px, py, score, lines, level):
        clear_screen()
        print("+" + "-" * (WIDTH * 2) + "+   TETRIS (ASCII)")
        for y in range(HEIGHT):
            line = "|"
            for x in range(WIDTH):
                filled = board[y][x]

                oy = y - py
                ox = x - px
                if 0 <= oy < len(piece) and 0 <= ox < len(piece[0]) and piece[oy][ox]:
                    filled = 1

                line += (BLOCK if filled else EMPTY)
            line += "|"
            print(line)
        print("+" + "-" * (WIDTH * 2) + "+")
        print(f"Score: {score}   Lines: {lines}   Level: {level}")
        print("Controls: A/D = left/right | W = rotate | S = soft drop | Space = hard drop | Q = quit")

    def read_key_nonblocking():
        if not msvcrt.kbhit():
            return None
        ch = msvcrt.getch()

        # Handle special keys (arrows etc.) - we ignore them
        if ch in (b"\x00", b"\xe0"):
            _ = msvcrt.getch()
            return None

        try:
            return ch.decode("utf-8").lower()
        except:
            return None

    def main():
        board = [[0] * WIDTH for _ in range(HEIGHT)]
        score = 0
        total_lines = 0

        piece, px, py = spawn_piece()
        if collision(board, piece, px, py):
            print("GAME OVER (no space to spawn).")
            return

        fall_timer = 0.0
        last_time = time.time()

        # speed: higher level => faster
        level = 1
        base_fall = 0.55  # seconds per drop at level 1

        running = True
        while running:
            now = time.time()
            dt = now - last_time
            last_time = now
            fall_timer += dt

            # update level based on lines
            level = max(1, total_lines // 10 + 1)
            fall_interval = max(0.08, base_fall - (level - 1) * 0.05)

            # input
            key = read_key_nonblocking()
            if key == "q":
                break
            elif key == "a":
                if not collision(board, piece, px - 1, py):
                    px -= 1
            elif key == "d":
                if not collision(board, piece, px + 1, py):
                    px += 1
            elif key == "w":
                rotated = rotate_clockwise(piece)
                if not collision(board, rotated, px, py):
                    piece = rotated
            elif key == "s":
                if not collision(board, piece, px, py + 1):
                    py += 1
            elif key == " ":
                py = hard_drop(board, piece, px, py)
                fall_timer = fall_interval  # force lock check soon

            # gravity
            if fall_timer >= fall_interval:
                fall_timer = 0.0
                if not collision(board, piece, px, py + 1):
                    py += 1
                else:
                    # lock
                    merge(board, piece, px, py)
                    board, cleared = clear_lines(board)
                    if cleared:
                        total_lines += cleared
                        # scoring (simple)
                        score += [0, 100, 300, 500, 800][cleared] * level

                    piece, px, py = spawn_piece()
                    if collision(board, piece, px, py):
                        draw(board, piece, px, py, score, total_lines, level)
                        print("\nGAME OVER!")
                        break

            draw(board, piece, px, py, score, total_lines, level)
            time.sleep(0.02)

    main()