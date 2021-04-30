from __future__ import annotations

import time
from typing import List, Tuple, Dict

import pyautogui

pyautogui.PAUSE = 0


class Minefield:
    TOP_CORNER_PATH = "screenshots/top_corner.png"
    RESET_BUTTON_PATH = "screenshots/reset_button.png"
    RESET_LOST_BUTTON_PATH = "screenshots/reset_lost.png"
    RESET_WON_BUTTON_PATH = "screenshots/reset_won.png"
    TILE_PATH = "screenshots/tile.png"
    TILE_NUMBER_PATH = "screenshots/tile_{}.png"  # {} should be a number between 1 and 8 (inclusive)

    class Tile:
        HIDDEN = -2
        FLAGGED = -1

        # 0 to 8 will represent the number of surrounding mines (also means tile has been clicked)

        def __init__(self, state=HIDDEN):
            self._state = state

        def get_state(self):
            return self._state

        def set_state(self, new_state):
            self._state = new_state

        def __repr__(self):
            return "Tile({})".format(self._state)

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.hidden = width * height

        # Store the limits of the clicked tiles
        self._leftmost_tile = -1
        self._rightmost_tile = -1
        self._upmost_tile = -1
        self._downmost_tile = -1

        # Stores which tiles have been "discovered" (left-click + right-click to show surrounding tiles)
        self._discovered: Dict[Tuple[int, int], bool] = {}

        # Stores how many mines are in the 8 surrounding tiles
        self._surrounding_mines = [[0 for _ in range(self.width)] for _ in range(self.height)]

        # Stores how many tiles are hidden in the 8 surrounding tiles
        self._create_surrounding_hidden_array()

        # Create the field array
        self._field = [[Minefield.Tile() for _ in range(self.width)] for _ in range(self.height)]

        self._find_reset_button()
        self.reset_field()
        self._find_first_tile()

    # -- Getters --

    def get_field(self) -> List[List[Tile]]:
        return self._field

    def get_surrounding_hidden_count(self, row: int, col: int) -> int:
        return self._surrounding_hidden[row][col]

    def get_surrounding_hidden(self, row: int, col: int) -> List[Tuple[int, int]]:
        if self._surrounding_hidden[row][col] != 0:
            return self._get_surrounding_tiles(row, col, Minefield.Tile.HIDDEN)
        else:
            return []

    def get_surrounding_mines_count(self, row: int, col: int) -> int:
        return self._surrounding_mines[row][col]

    def get_leftmost_tile(self) -> int:
        return self._leftmost_tile

    def get_rightmost_tile(self) -> int:
        return self._rightmost_tile

    def get_upmost_tile(self) -> int:
        return self._upmost_tile

    def get_downmost_tile(self) -> int:
        return self._downmost_tile

    # -- Public --

    def click_tile(self, row: int, col: int, right_click: bool = False) -> None:
        if not (0 <= row <= self.height) or not (0 <= col < self.width):
            raise ValueError("Tried to click outside the minefield.")

        if self._field[row][col].get_state() != Minefield.Tile.HIDDEN:
            # Don't click on already clicked tiles
            return

        if right_click:
            pyautogui.click(x=(self._x_offset + col * self._tile_width), y=(self._y_offset + row * self._tile_height),
                            button='right')
        else:
            pyautogui.click(x=(self._x_offset + col * self._tile_width), y=(self._y_offset + row * self._tile_height))

        # Update clicked region
        if self._upmost_tile == -1:
            # If -1, this is first click, no need to do expensive check
            self._upmost_tile = self._downmost_tile = row
            self._leftmost_tile = self._rightmost_tile = col
        else:
            self._upmost_tile = row if row < self._upmost_tile else self._upmost_tile
            self._downmost_tile = row if row > self._downmost_tile else self._downmost_tile
            self._leftmost_tile = col if col < self._leftmost_tile else self._leftmost_tile
            self._rightmost_tile = col if col > self._rightmost_tile else self._rightmost_tile

    def flag_tile(self, row: int, col: int) -> None:
        self.click_tile(row, col, right_click=True)
        self._field[row][col].set_state(Minefield.Tile.FLAGGED)

        # Adjust _surrounding_mines to include this tile
        for tile_row in range(row - 1, row + 2):
            for tile_col in range(col - 1, col + 2):
                if not (0 <= tile_col < self.width) or not (0 <= tile_row < self.height) \
                        or (tile_col == col and tile_row == row):
                    # Out of bounds or given tile in arguments, don't do anything
                    continue

                # Tile at index (tile_row, tile_col) now has one more surrounding mine
                self._surrounding_mines[tile_row][tile_col] += 1

                # Tile also has one less surrounding hidden tile
                self._surrounding_hidden[tile_row][tile_col] -= 1

        self.hidden -= 1

    def discover_tile(self, row: int, col: int, force: bool = False) -> None:
        # Click down with the left and right button at the same time
        if not (0 <= row < self.height) or not (0 <= col < self.width):
            raise ValueError("Tried to click outside the minefield.")

        # Only try to discover if there is at least 1 hidden tile surrounding or force argument is True
        if self._surrounding_hidden != 0 or force:
            x_pos = self._x_offset + col * self._tile_width
            y_pos = self._y_offset + row * self._tile_height

            self._discovered[(row, col)] = True

            pyautogui.mouseDown(x=x_pos, y=y_pos, button='left')
            pyautogui.mouseDown(x=x_pos, y=y_pos, button='right')
            pyautogui.mouseUp(button='left')
            pyautogui.mouseUp(button='right')

    def reset_field(self) -> None:
        pyautogui.click(x=self._reset_x, y=self._reset_y)

    def update_field(self) -> None:
        # To save time, only look in a certain region
        # Add a certain buffer to avoid missing certain tiles
        x1 = self._x_offset - (2 * self._tile_width)
        y1 = self._y_offset - (2 * self._tile_height)
        x2 = self._x_offset + self._tile_width * (self.width + 2)
        y2 = self._y_offset + self._tile_height * (self.height + 2)
        region = (x1, y1, x2, y2)

        time.sleep(0.01)
        # Find clicked tiles
        screen = pyautogui.screenshot(region=region)

        for i in range(0, 9):
            for location in pyautogui.locateAll(Minefield.TILE_NUMBER_PATH.format(i), screen, grayscale=True):
                # Adjust the location by re-adding the x1 and y1 offset to the pyautogui location coordinates
                row, col = self._screen_position_to_field_index(pyautogui.center(location), x_offset=x1, y_offset=y1)

                # Only replace if tile was previously hidden
                if self._field[row][col].get_state() == Minefield.Tile.HIDDEN:
                    self._field[row][col].set_state(i)
                    self.hidden -= 1
                    # Also update the clicked region variables to reflect newly clicked tiles
                    self._upmost_tile = row if row < self._upmost_tile else self._upmost_tile
                    self._downmost_tile = row if row > self._downmost_tile else self._downmost_tile
                    self._leftmost_tile = col if col < self._leftmost_tile else self._leftmost_tile
                    self._rightmost_tile = col if col > self._rightmost_tile else self._rightmost_tile

                    # Update _surrounding_hidden to reflect change
                    for tile_row in range(row - 1, row + 2):
                        for tile_col in range(col - 1, col + 2):
                            if not (0 <= tile_row < self.height) or not (0 <= tile_col < self.width) \
                                    or (row == tile_row and col == tile_col):
                                # Out of bounds or given tile in arguments, don't do anything
                                continue
                            self._surrounding_hidden[tile_row][tile_col] -= 1

    def is_won(self) -> bool:
        return self.hidden == 0

    def is_dead_from_mine(self) -> bool:
        # Check if the reset_lost button is on screen
        time.sleep(0.005)

        # Since the location of the reset button is known, we can set a region to save some time
        x1 = self._reset_x - 16
        x2 = self._reset_x + 16
        y1 = self._reset_y - 16
        y2 = self._reset_y + 16
        region = (x1, y1, x2, y2)

        location = pyautogui.locateOnScreen(Minefield.RESET_LOST_BUTTON_PATH, grayscale=True, region=region)
        return bool(location)  # Return true if a location is found

    # -- Private --

    def _create_surrounding_hidden_array(self):
        # Stores how many tiles are hidden in the 8 surrounding tiles
        self._surrounding_hidden = [[8 for _ in range(self.width)] for _ in range(self.height)]

        # Adjust the edges since they have 3 less tiles
        for col in range(0, self.width):
            self._surrounding_hidden[0][col] -= 3
            self._surrounding_hidden[self.height - 1][col] -= 3

        for row in range(0, self.height):
            self._surrounding_hidden[row][0] -= 3
            self._surrounding_hidden[row][self.width - 1] -= 3

        # Add one to corners since we over compensated in the 2 previous loops
        for col in [0, self.width - 1]:
            for row in [0, self.height - 1]:
                self._surrounding_hidden[row][col] += 1

    def _find_first_tile(self):
        time.sleep(0.05)
        location = pyautogui.locateOnScreen(Minefield.TILE_PATH, grayscale=True)
        self._tile_width = location.width
        self._tile_height = location.height
        self._x_offset, self._y_offset = pyautogui.center(location)

    def _find_reset_button(self):
        time.sleep(0.01)
        location = pyautogui.locateCenterOnScreen(Minefield.RESET_BUTTON_PATH, grayscale=True)
        if not location:
            # The game could be in a lost state, try to find the reset button in lost state
            location = pyautogui.locateCenterOnScreen(Minefield.RESET_LOST_BUTTON_PATH, grayscale=True)

            if not location:
                # The game could be in a won state, try to find the reset button in won state

                location = pyautogui.locateCenterOnScreen(Minefield.RESET_WON_BUTTON_PATH, grayscale=True)

                if not location:
                    print("Error locating the reset button.")
                    exit(1)

        # Successfully found reset button, store location
        self._reset_x, self._reset_y = location

    def _screen_position_to_field_index(self, point: pyautogui.Point, x_offset: int = 0, y_offset: int = 0):
        x = point.x + x_offset
        y = point.y + y_offset
        row = round((y - self._y_offset) / self._tile_height)
        col = round((x - self._x_offset) / self._tile_width)
        return row, col

    def _get_surrounding_tiles(self, row: int, col: int, tile_type) -> List[Tuple[int, int]]:
        tiles = []
        col_min = col - 1
        col_min = 0 if col_min < 0 else col_min  # If near edge, don't go into negative indexes
        col_max = col + 1
        col_max = self.width - 1 if col_max >= self.width else col_max  # If near edge, don't go out of bounds

        row_min = row - 1
        row_min = 0 if row_min < 0 else row_min
        row_max = row + 1
        row_max = self.height - 1 if row_max >= self.height else row_max

        for tile_row in range(row_min, row_max + 1):
            for tile_col in range(col_min, col_max + 1):
                if tile_col == col and tile_row == row:
                    # Don't count the provided tile
                    continue

                if self._field[tile_row][tile_col].get_state() == tile_type:
                    tiles.append((tile_row, tile_col))
        return tiles
