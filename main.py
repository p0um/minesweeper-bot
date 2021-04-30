import time

import pyautogui
import keyboard

from Minefield import Minefield


def next_move(minefield: Minefield) -> bool:
    made_move = False
    # Flag every tiles that have to be bombs
    for row in range(minefield.height):
        for col in range(minefield.width):
            tile = minefield.get_field()[row][col]

            if tile.get_state() != Minefield.Tile.HIDDEN:
                missing = tile.get_state() - minefield.get_surrounding_mines_count(row, col)

                # If there are no missing, don't waste time finding hidden tiles
                if missing == 0:
                    # Try to discover more tiles unless state is 0 (all tiles will already have been discovered)
                    # or it has no undiscovered tiles surrounding it
                    if tile.get_state() != 0 and minefield.get_surrounding_hidden_count(row, col) != 0:
                        minefield.discover_tile(row, col)
                    continue

                surroundings = minefield.get_surrounding_hidden(row, col)

                # Number of missing mines is equal to the number of hidden tiles
                # Flag all hidden tiles
                if len(surroundings) == missing:
                    print("({}, {}) : {}".format(row, col, surroundings))
                    for surrounding in surroundings:
                        minefield.flag_tile(surrounding[0], surrounding[1])
                    minefield.discover_tile(row, col)
                    made_move = True

    return made_move


def guess(minefield: Minefield) -> bool:
    probability = [[0 for _ in range(minefield.width)] for _ in range(minefield.height)]
    # For tile in field, if not hidden and not 0, set probability to surrounding hidden tiles
    # Keep highest
    # Store overall highest with position
    highest_probability = -1
    highest_position = (0, 0)

    # Only try to guess within the zone of already clicked tiles
    row_min = minefield.get_upmost_tile()
    row_min = 0 if row_min < 0 else row_min
    row_max = minefield.get_downmost_tile() + 1
    row_max = minefield.height if row_max > minefield.height else row_max  # Don't subtract 1 since only used in range.

    col_min = minefield.get_leftmost_tile()
    col_min = 0 if col_min < 0 else col_min
    col_max = minefield.get_rightmost_tile() + 1
    col_max = minefield.width if col_max > minefield.height else col_max

    for row in range(row_min, row_max):
        for col in range(col_min, col_max):
            tile = minefield.get_field()[row][col]
            if tile.get_state() not in [Minefield.Tile.HIDDEN, Minefield.Tile.FLAGGED, 0]:
                mines = minefield.get_surrounding_mines_count(row, col)
                missing_mines = tile.get_state() - mines
                hidden = minefield.get_surrounding_hidden_count(row, col)

                if hidden == 0:
                    # If there are no hidden tiles, cannot guess for this tile
                    # Continue to avoid division by 0
                    continue

                prob = missing_mines / hidden  # Missing mines divided by possible spot

                surrounding_hidden_tiles = minefield.get_surrounding_hidden(row, col)
                if surrounding_hidden_tiles:
                    for surr_tile in surrounding_hidden_tiles:
                        surr_row, surr_col = surr_tile

                        # To help expansion, give multiplier if going outwards from clicked region
                        multiplier = 1
                        if surr_row < minefield.get_upmost_tile() or surr_row > minefield.get_downmost_tile():
                            multiplier += 0.02
                        if surr_col < minefield.get_leftmost_tile() or surr_col > minefield.get_rightmost_tile():
                            multiplier += 0.02

                        new_prob = probability[surr_row][surr_col] + (prob * multiplier)
                        probability[surr_row][surr_col] = new_prob

                        if new_prob > highest_probability:
                            highest_probability = new_prob
                            highest_position = (surr_row, surr_col)

    if highest_probability == -1:
        # Couldn't make a guess
        return False
    else:
        minefield.flag_tile(highest_position[0], highest_position[1])
        print("Guess location: ({}, {})".format(highest_position[0], highest_position[1]))
        return True


def main():
    print("Please focus on the minesweeper tab.")
    time.sleep(1)
    # minefield = Minefield(width=9, height=9)  # Beginner
    # minefield = Minefield(width=16, height=16)  # Intermediate
    minefield = Minefield(width=30, height=16)  # Expert

    minefield.click_tile(3, 3)
    minefield.update_field()
    print("Updated")

    i = 1
    guessed_moves = 0
    no_move = 0

    while not keyboard.is_pressed('q') and not minefield.is_won():
        if keyboard.is_pressed('a'):
            print(minefield._screen_position_to_field_index(pyautogui.position()))

        if not next_move(minefield):
            no_move += 1
        else:
            no_move = 0

        if no_move >= 2:
            # minefield.update_field()
            # Algorithm couldn't find a tile to uncover, try a guess.
            guessed_moves += 1
            print("Guessing: {}".format(guessed_moves))
            if not guess(minefield):
                print("Unable to guess.")
                # exit(2)
                print("Restarting...")
                main()

        minefield.update_field()

        if i % 5 == 0:
            # Check if dead once every 5 move to not check too often and slow down program
            if minefield.is_dead_from_mine():
                print("Wrong guess.")
                print("Restarting...")
                main()

        i += 1
        print("loop")
    print("done")


if __name__ == '__main__':
    main()
