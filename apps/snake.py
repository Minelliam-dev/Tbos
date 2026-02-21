import os, time, msvcrt, random

def snake_main():
    # Board size (playable area)
    W = 30
    H = 20

    # Rendering
    EMPTY = "  "
    SNAKE = "[]"
    FOOD = "<>"
    WALL = "##"

    def clear():
        os.system("cls")

    def read_key():
        """Non-blocking key read. Returns 'w','a','s','d','q' or None."""
        if not msvcrt.kbhit():
            return None
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):  # special keys (arrows), ignore
            _ = msvcrt.getch()
            return None
        try:
            return ch.decode("utf-8").lower()
        except:
            return None

    def place_food(snake_set):
        while True:
            fx = random.randint(1, W - 2)
            fy = random.randint(1, H - 2)
            if (fx, fy) not in snake_set:
                return (fx, fy)

    def draw(snake, food, score, speed):
        clear()
        print("+" + "-" * (W * 2) + "+   SNAKE (ASCII)")
        snake_set = set(snake)

        for y in range(H):
            row = "|"
            for x in range(W):
                if x == 0 or x == W - 1 or y == 0 or y == H - 1:
                    row += WALL
                elif (x, y) == food:
                    row += FOOD
                elif (x, y) in snake_set:
                    row += SNAKE
                else:
                    row += EMPTY
            row += "|"
            print(row)

        print("+" + "-" * (W * 2) + "+")
        print(f"Score: {score}   Speed: {speed:.2f}s/tick")
        print("Controls: W/A/S/D move | Q quit")

    def main():
        # Snake starts in the middle moving right
        start_x = W // 2
        start_y = H // 2
        snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        direction = (1, 0)  # dx, dy
        pending_dir = direction

        snake_set = set(snake)
        food = place_food(snake_set)

        score = 0
        base_speed = 0.12  # smaller = faster

        running = True
        while running:
            # Speed up slightly as score increases (clamped)
            speed = max(0.05, base_speed - score * 0.002)

            # Read input (non-blocking) and update pending direction
            key = read_key()
            if key == "q":
                break
            elif key == "w":
                pending_dir = (0, -1)
            elif key == "s":
                pending_dir = (0, 1)
            elif key == "a":
                pending_dir = (-1, 0)
            elif key == "d":
                pending_dir = (1, 0)

            # Prevent instant reverse into itself
            if (pending_dir[0] != -direction[0]) or (pending_dir[1] != -direction[1]):
                direction = pending_dir

            # Move snake
            head_x, head_y = snake[0]
            dx, dy = direction
            new_head = (head_x + dx, head_y + dy)

            # Wall collision
            if new_head[0] == 0 or new_head[0] == W - 1 or new_head[1] == 0 or new_head[1] == H - 1:
                draw(snake, food, score, speed)
                print("\nGAME OVER! You hit a wall.")
                break

            # Self collision (tail exception: if tail moves away this tick, it’s ok)
            tail = snake[-1]
            if new_head in snake_set and new_head != tail:
                draw(snake, food, score, speed)
                print("\nGAME OVER! You ran into yourself.")
                break

            # Add head
            snake.insert(0, new_head)
            snake_set.add(new_head)

            # Eat food?
            if new_head == food:
                score += 1
                food = place_food(snake_set)
                # keep tail (snake grows)
            else:
                # remove tail (snake moves)
                removed = snake.pop()
                snake_set.remove(removed)

            draw(snake, food, score, speed)
            time.sleep(speed)

        print("\nThanks for playing!")

    main()