import win32gui
import mss
import mss.tools
from time import sleep
import time
import win32api
import win32con
from random import randint
import numpy as np
from collections import defaultdict
from functools import reduce


class MineField:
    # size of individual field where a mine can be
    FIELD_WIDTH = 16
    FIELD_HEIGHT = 16

    # Color of a pixel that identifies what number a field is
    OPTIONS = {
        "solve_everything": True,
        "use_smart_choice": True,
        "use_lucky_choice": True,
        "clicking_speed"  : 0,
    }

    NUMBERS = {
        (192, 192, 192): 0,
        (0, 0, 255)    : 1,
        (0, 128, 0)    : 2,
        (255, 0, 0)    : 3,
        (0, 0, 128)    : 4,
        (128, 0, 0)    : 5,
        (0, 128, 128)  : 6,
        (0, 0, 0)      : 7,
        (128, 128, 128): 8
    }
    DARK_GREY = (128, 128, 128)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    BLACK = (0, 0, 0)

    # max number of fields that can go into one equation at once?
    LINEAR_SEARCH_RANGE = 300

    # THE MEANING OF NUMBERS IN MAP
    # 0 is an empty field
    # -2 mine
    # -5 missed flag
    # -3 destroyed mine
    # 1,2,3,4,5,6,7,8 a number
    # -1 uncovered field
    # -4 flag
    def __init__(self):
        """
        Searches activate windows for one named `Minesweeper X` getting get coordinates and size
        next takes a screenshot of desktop to extract that windows and processes it.
        
        Functions for user to use:
        restart() - clicks restart button and initalizes itself
        solver() - solves the minesweeper. Returns True if solved, False if not.
        click_middle_field() - clicks the middle field of the minefield
        
        WARNING: Durning solving minesweeper if you cover the window containing the game it will stop.
                 And please dont move the minesweeper window.
        """
        handle = win32gui.FindWindow(None, 'Minesweeper X')
        assert handle != 0, 'Window not found'

        _left, _top, _right, _bottom = win32gui.GetClientRect(handle)
        left, top = win32gui.ClientToScreen(handle, (_left, _top))
        right, bottom = win32gui.ClientToScreen(handle, (_right, _bottom))
        window_rect = dict(top=top,
                           left=left,
                           width=right - left,
                           height=bottom - top)
        self.win_rect = window_rect
        self.map_x, self.map_y = 12, 55
        self.image_map = None
        self.map = []
        self.net_mask = []
        self.sct = mss.mss()
        # mss.tools.to_png(image.rgb, image.size, output='test.png')

        # TODO: jak są kandydaci, to niech nie daje mi żadnych kandydatów co nie mają pustych pól koło siebie!
        self.restart_button = (self.win_rect['width'], 20)
        # mss.tools.to_png(self.image_map.rgb, self.image_map.size, 'minefield/field.png')

        self.init()

        # self.image_map = self.sct.grab(dict(top=0,
        #                                     left=0,
        #                                     width=1920,
        #                                     height=1080))

    def init(self) -> None:
        """
        Creates a new netmask and reflashes game.
        """
        # sleep(1)
        self.rows, self.columns = self.map_dimensions()
        self.net_mask = [[0 for _ in range(self.rows)] for _ in range(self.rows)]
        self.refresh()  # załaduj obraz mape
        # sleep(1)

    def restart(self) -> None:
        """
        Clicks restar button and initializes
        """
        self.click_restart_button()
        self.init()

    def click_restart_button(self) -> None:
        """
        Clicks restart button
        """
        x = self.win_rect['left'] + self.win_rect['width'] // 2  # X of the face
        y = self.win_rect['top'] + 20  # Y of the face

        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def right_click(self, tile_x: int, tile_y: int) -> None:
        """
        Right clicks on a tile using map coordinates
        :param tile_x: X coordinate of the field
        :param tile_y: Y coordinate of the field
        """
        print('({:>2}, {:>2}) ->\tBOMB'.format(tile_x, tile_y))
        x, y = self._from_tile(tile_x, tile_y)
        x += self.win_rect['left']
        y += self.win_rect['top']
        sleep(self.OPTIONS["clicking_speed"])
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)

        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)

    def left_click(self, tile_x: int, tile_y: int) -> None:
        """
        Left clicks on a tile using map coordinates
        :param tile_x: X coordinate of the field
        :param tile_y: Y coordinate of the field
        """
        print('({:>2}, {:>2}) ->\tSAFE'.format(tile_x, tile_y))
        x, y = self._from_tile(tile_x, tile_y)
        x += self.win_rect['left']
        y += self.win_rect['top']
        sleep(self.OPTIONS["clicking_speed"])
        win32api.SetCursorPos((x, y))

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

        # win32api.SetCursorPos((self.win_rect['left'], self.win_rect['top']))
        # self.get_number(x, y)
        # self.get_tile_image(tile_x, tile_y)

    def refresh(self) -> bool:
        """
        Move cursor to a save position, takes screenshot and loads game status to a variable.
        :return: True if the game is lost. 
        """
        win32api.SetCursorPos((self.win_rect['left'], self.win_rect['top']))
        self.image_map = self.sct.grab(self.win_rect)
        return self.load_to_array()

    def get_tile_image(self, tile_x: int, tile_y: int) -> None:
        """
        Extracts individual field to a .png file.
        Fun tool, not used.
        :param tile_x: X coordinate of the field
        :param tile_y: Y coordinate of the field
        """
        x, y = self._from_tile(tile_x, tile_y)
        d = dict(top=y + self.win_rect['top'],
                 left=x + self.win_rect['left'],
                 width=self.FIELD_WIDTH,
                 height=self.FIELD_HEIGHT)
        tile = self.sct.grab(d)
        # print(self.get_number(0,0, tile))
        # print(tile_x, tile_y)
        mss.tools.to_png(tile.rgb, tile.size, output='minefield/field{}x{}.png'.format(tile_y, tile_x))

    def _from_tile(self, tile_x: int, tile_y: int) -> (int, int):
        """
        Translates map coordinates to a display coordinates
        :param tile_x: X coordinate of the field
        :param tile_y: Y coordinate of the field
        :returns tuple (x, y) 
        """
        x = self.map_x + self.FIELD_WIDTH * tile_x
        y = self.map_y + self.FIELD_HEIGHT * tile_y
        return x, y

    def get_number(self, tile_x: int, tile_y: int, image=None) -> int:
        """
        Checks what number is in said position 
        :param tile_x: X coordinate of the field
        :param tile_y: Y coordinate of the field
        :param image: Whatever to use a custom image from PIL. 
                      If not given is uses extracted minesweeper screenshot from display.
        :return: Int representing a field.
                 1, 2, 3, 4, 5, 6, 7, 8 a number
                 0 is an empty field
                 -1 uncovered field
                 -2 mine
                 -3 destroyed mine
                 -4 flag
                 -5 missed flag
        """

        x, y = self._from_tile(tile_x, tile_y)
        if image is None:
            image = self.image_map
        # Game map explanation
        # -2 -2 -1 -2 -2 -1 -2 -2
        # -2 -2 -2 -1 -2 -1 -2 -2
        # -2 -3 -2 -1 -2  6 -2 -2
        # -2 -2 -2 -1 -1 -2 -2 -2
        # -2 -1 -2 -2  5 -1 -2 -2
        # -2 -2 -2 -2 -2 -2 -2 -2
        # -2 -2 -2 -2 -2 -2 -2 -2
        # -1 -2 -1 -1 -2 -2 -2 -2

        # 0 is empty, uncovered field  (Lew upper corner is grey)
        #    -2 a mine (7, 7 is white)
        #        -5 missed flag (8,8 is red)
        #        -3 destroyed mine (1,1 is red)
        #    1,2,3,4,5,6,7,8 a number (8, 9 have colors that indefinites a number)
        # -1 uncovered field (0,0 is white)
        #    -4 flag (8,8 is black)

        if image.pixel(x, y) == self.DARK_GREY:
            # empty field subtree

            if image.pixel(x + 7, y + 7) == self.WHITE:
                # mine subtree
                if image.pixel(x + 8, y + 8) == self.RED:
                    return -5  # missed

                elif image.pixel(x + 1, y + 1) == self.RED:
                    return -3  # destroyed mine

                return -2  # mine
            else:
                # a number or empty field
                return self.NUMBERS[image.pixel(x + 9, y + 8)]

        elif image.pixel(x, y) == self.WHITE:
            # uncovered field subtree
            if image.pixel(x + 8, y + 8) == self.BLACK:
                return -4  # flag
            return -1  # uncovered field
        else:
            raise Exception(
                '{}x{} contains unknown field type\n\nHave you covered minesweeper screen?\nor moved it!?'.format(
                    tile_x, tile_y))

    def map_dimensions(self) -> (int, int):
        """
        Gives dimensions of a game. 
        :return: (collumns, rows) 
        """
        return self.field_dimensions(self.win_rect['width'], self.win_rect['height'])

    def field_dimensions(self, width: int, height: int) -> (int, int):
        """
        Translates width and height to number of fields.
        It excepts size of whole minesweeper game, not only that clickable part.
        It automatically removes the borders!
        :param width: 
        :param height: 
        :return: (number of tiles in X axis, number of tiles in Y axis) 
        """
        h = height - (self.map_y + self.map_x)
        w = width - 2 * self.map_x
        return w // self.FIELD_WIDTH, h // self.FIELD_HEIGHT

    def __str__(self) -> str:
        ans = []
        for row in self.map:
            ans.append(' '.join(' ' + str(n) if n >= 0 else str(n) for n in row))
        return '\n'.join(ans)

    def __repr__(self) -> str:
        """
        Additionally contains net mask
        """
        ans = []
        for row in self.net_mask:
            ans.append(' '.join(str(n) for n in row))
        return str(self) + '\n' + '\n'.join(ans)

    def _lost(self) -> None:
        print('\nYou lost!!! SORRY but YOU asked for it!!!!\n')

    def load_to_array(self) -> bool:
        """
        Processes game image creating new game map containing numbers, 
        that represents actual of actual game.
        :return: True if the game is lost.
        """
        columns, rows = self.map_dimensions()
        self.map = []
        for y in range(rows):
            n = []
            for x in range(columns):
                num = self.get_number(x, y)
                if num == -3:
                    # sorry you lost
                    return True
                n.append(num)
                if self.net_mask[y][x] == 0:
                    if num == 0 or num == -4:
                        # pusta kratka lub flaga
                        self.net_mask[y][x] = 1
            self.map.append(n)
        return False

    def solver(self) -> bool:
        """
        Solves the minesweeper.
        It uses 2 algorithms:
        _solver()
        linear_equasions()
        
        :return: False if lost.
        """
        # TODO: no bo ten rozwiązywacz równań i tak jakoś ma dość duży pustych równań
        # Czemu one się dodaja pomimo że nie powinny?
        # Kto to wie a kto nie ten niech wie....

        while True:
            lost = self.refresh()
            if lost:
                self._lost()
                return False
            changed = self._solver()
            if not changed:
                if self.OPTIONS["use_smart_choice"]:
                    did_smart_changed = self.smart_click()
                    if not did_smart_changed:
                        return False
                else:
                    return False

            if not self.OPTIONS["solve_everything"]:
                break

    def smart_click(self):
        _min, _max, changed = self.linear_equasions()  # does the click
        # print(_min, _max, changed)
        if changed is True:
            return True
        if changed is False:
            if not self.OPTIONS["use_lucky_choice"]:
                return False
            # lets try our luck
            (min, min_prob), (max, max_prob) = _min, _max
            dmin, dmax = abs(min_prob), (1 - max_prob)
            if dmin > dmax:
                # wartości maksymalnej jest bliżej do 0 lub 1
                x, y = max
                print('CHOOSING RANDOM BOMB ({} prob))'.format(abs(max_prob)))
                self.right_click(x, y)

            else:
                # wartości minimalna jest bliżej do 0 lub 1
                print('CHOOSING RANDOM SAVE SPOT ({} prob)'.format(abs(min_prob)))
                x, y = min
                self.left_click(x, y)
            return True # sometching must have changed


    def in_bounds(self, _x: int, _y: int):
        return 0 <= _y < self.columns and 0 <= _x < self.rows

    def _solver(self):
        """The simple version"""
        changed = False

        for y in range(self.columns):
            for x in range(self.rows):
                if self.net_mask[y][x] == 0:
                    num = self.map[y][x]
                    if 0 < num <= 7:
                        mines = num
                        touching = 0
                        for _y in range(-1, 2):
                            _y += y
                            for _x in range(-1, 2):
                                _x += x
                                if self.in_bounds(_x, _y):
                                    if self.map[_y][_x] == -4:
                                        mines -= 1
                                    if self.map[_y][_x] == -1:
                                        touching += 1
                        if mines == 0:
                            self.net_mask[y][x] = 1
                        if (mines == touching) or (mines == 0):
                            for _y in range(-1, 2):
                                _y += y
                                for _x in range(-1, 2):
                                    _x += x
                                    if self.in_bounds(_x, _y) and self.net_mask[_y][_x] == 0:
                                        if mines == touching and self.map[_y][_x] == -1:
                                            # jest to pole do kliknięcia, a ty masz jedną minę
                                            # print('Right click for', _x, _y)
                                            self.map[_y][_x] = -4
                                            # self.net_mask[_y][_x] = 1
                                            self.right_click(_x, _y)
                                            changed = True
                                        elif mines == 0 and self.map[_y][_x] == -1:
                                            # nie żadnych min, a ty szukasz pola do kliknięcia
                                            # print('Left click for', _x, _y)

                                            self.left_click(_x, _y)
                                            changed = True

                                            # self.net_mask[_y][_x] = 1
        return changed

    def press_random_field(self):
        self._press_random_field()

    def _press_random_field(self):
        """
        For now it just click first bomb.
        :return: (x, y) of clicked position. 
        """
        for y in range(self.columns):
            for x in range(self.rows):
                if self.map[y][x] == -1:
                    print('Random choice! ({}, {})'.format(x, y))
                    self.left_click(x, y)
                    return x, y
        return None, None

    def linear_equasions(self):
        """
        Advanced version of solver.
        If it have 100% chance of successful click, it does it.
        If not, it returns positions of prob safe spots/bombs and
        :return: (((x,y), prob) ((x, y), prob), changed) 
        #TODO: i think. Not sure
        """

        def do_equasion(x, y):
            eq = dict()
            sum = self.map[y][x]
            for _x, _y in self.field_neighborhood(x, y):
                if self.in_bounds(_x, _y):
                    if self.map[_y][_x] == -1:
                        # jeżeli puste pole
                        eq[(_x, _y)] = 1
                    if self.map[_y][_x] == -4:
                        # jeżeli falga
                        # eq[(_x, _y)] = 1
                        sum -= 1
            return eq, sum

        candidates = self._get_candidate()
        # print('Kandydaci', sorted(list(candidates)))
        # print('*' * 10)
        sums = []
        equasions = []
        variables = set()
        if candidates is None:
            return None, None, None

        for _x, _y in candidates:
            equasion, sum = do_equasion(_x, _y)
            # print(equasion, sum, 'for {} x {}'.format(_x, _y))

            variables.update(equasion)
            equasions.append(equasion)
            sums.append(sum)

        for eq in equasions:
            for var in variables:
                if var not in eq:
                    eq[var] = 0

        keys = sorted(list(variables))

        new_equasions = []

        for eq in equasions:
            new = []
            for key in keys:
                new.append(eq[key])
            new_equasions.append(new)

        a = np.array(new_equasions)
        b = np.array(sums)
        # print(keys)
        for eq, s in zip(a, b):
            pass
            # print(eq, '->', s)
        # [print(c, '=', o) for c, o in zip(equasions, sums)]
        try:
            solution = np.linalg.solve(a, b).round(3)
            # print('Dokładne obliczanie równanie!!!!')
        except:
            x = np.linalg.lstsq(a, b)
            # print(x)
            solution = x[0].round(decimals=3)
            # print('-' * 10)
            # print('Niedokładne obliczanie równania')

        # print('[\n',
        #       '\n'.join([str(key) + ' -> ' + str(h) for h, key in zip(solution, keys)]),
        #       '\n]')

        changed = False
        for i, prob in enumerate(solution):
            key = keys[i]

            if prob == 0:
                print("SMART CHOICE:")
                self.left_click(*key)
                changed = True
            if prob == 1:
                print("SMART CHOICE:")
                self.right_click(*key)
                changed = True
        min_index, min_prob = min(enumerate(solution), key=lambda p: abs(p[1]))
        max_index, max_prob = max(enumerate(solution), key=lambda p: abs(p[1]))
        # print('{} with {} probability that its a mine!'.format((x, y), prob))
        # self.left_click(x, y)
        return (keys[min_index], min_prob), (keys[max_index], max_prob), bool(changed)
        # return None, None

    def field_neighborhood(self, x, y):
        for _y in range(-1, 2):
            _y += y
            for _x in range(-1, 2):
                _x += x
                if self.in_bounds(_x, _y):
                    yield _x, _y

    def _get_candidate(self):
        for y in range(self.columns):
            for x in range(self.rows):
                if self.net_mask[y][x] == 0 and 0 < self.map[y][x] <= 8:
                    q = set()
                    # print('The candidate!', x, y)
                    self._for_search(x, y, q)
                    return q
        return None

    def test(self):
        self.test_show_map()

    def test_show_map(self):
        ans = []
        rows, columns = self.map_dimensions()
        for y in range(rows):
            row = []
            for x in range(columns):
                ans.append(self.get_number(x, y))
                row.append(self.get_number(x, y))
            print(' '.join(' ' + str(n) if n >= 0 else str(n) for n in row))

    def click_middle_field(self):
        """
        Clicks middle field.
        """
        print('CHOOSING MIDDLE FIELD')
        width, height = self.map_dimensions()
        width, height = width // 2, height // 2
        self.left_click(width, height)

    def _for_search(self, x, y, queue):
        new = set()
        val = self.map[y][x]

        if self.LINEAR_SEARCH_RANGE <= len(queue):
            return
        for _x, _y in self.field_neighborhood(x, y):
            if self.map[_y][_x] == -4:
                val -= 1
            if 0 < self.map[_y][_x] <= 7:
                if (_x, _y) not in queue:
                    # print('FROM ({}, {}) ADDING ({}, {})'.format(x, y, _x, _y))
                    new.add((_x, _y))

        queue.update(new)
        for x_, y_ in new:
            self._for_search(x_, y_, queue)


def test_number_finding():
    """
    Tests that check if exctraction numbers from a image still works! 
    """

    def _test_number_finding(path):
        from PIL import Image

        mine_field = MineField()
        img = Image.open(path)
        h = img.height - 2 * mine_field.map_x
        # print(img.height)
        columns, rows = mine_field.field_dimensions(img.width, img.height)

        class Img:
            @staticmethod
            def pixel(x, y):
                return img.getpixel((x, y))

        row = []
        for y in range(rows):
            for x in range(columns):
                row.append(mine_field.get_number(x, y, Img))
        return row

    import sys
    cases = [
        [-1, -1, -1, -1, -1, -1, 1, 0, -1, -1, -1, -1, 3, -1, 1, 0, -1, 1, 1, 2, -1, -1, 1, 0, -1, 1, 0, 2, -1,
         -1, 1,
         0, -1, 1, 0, 1, 2, 2, 1, 0, -1, 2, 1, 0, 0, 0, 0, 0, -1, -1, 2, 0, 1, 1, 1, 0, -1, -1, 2, 0, 1, -1, 1, 0],
        [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1],
        [0, 0, 0, 0, 0, 1, -1, -1, 0, 0, 0, 0, 0, 2, -1, -1, 0, 0, 0, 0, 0, 3, -1, -1, 1, 1, 1, 0, 0, 2, -1, -1, -1, -1,
         1, 0, 0, 1, 2, 2, -1, -1, 3, 1, 1, 0, 0, 0, -1, -1, -1, -1, 2, 1, 0, 0, -1, -1, -1, -1, -1, 1, 0, 0],
        [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1],
        [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1],
        [-2, -2, -1, -2, -2, -1, -2, -2, -2, -2, -2, -1, -2, -1, -2, -2, -2, -3, -2, -1, -2, 6, -2, -2, -2, -2, -2, -1,
         -1, -2, -2, -2, -2, -1, -2, -2, 5, -1, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2,
         -1, -2, -1, -1, -2, -2, -2, -2],
        [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, 1, 3, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, 1, 0, 2, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, 2, 1, 1, 0, 2, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 0, 0, 0, 2, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, 2, 0, 1, 1, 3,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, 1, -1, -1, -1, 1, 0, 1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 0, 1,
         1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, 0, 0,
         0, 0, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, 1,
         1, 0, 0, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, 1, 0, 1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, 1, 1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]

    ]
    pased_tests = 0
    for i, ans in enumerate(cases):
        path = "tests/num_test{}.png".format(i + 1)
        try:
            got = _test_number_finding(path)
            assert ans == got
            pased_tests += 1
        except AssertionError:
            print('<<<TEST FAILED {}: got:\n{}\nexpexted:\n{}'.format(path, got, ans))
    print('<<<', sys._getframe().f_code.co_name, 'passed ({} of {})>>>'.format(pased_tests, len(cases)))
    assert got == ans


# test_number_finding()

if __name__ == '__main__':
    mine_field = MineField()
    mine_field.click_restart_button()

    solved = False
    while solved is False:
        mine_field.restart()
        mine_field.click_middle_field()
        start = time.time()
        solved = mine_field.solver()
    print("Done in {} seconds".format(time.time() - start))

# mine_field.click(0, 0)
# mine_field.get_tile_image(7, 0)
# mine_field.get_number(6, 0)
# columns, rows = mine_field.map_dimensions()
# for _ in range(4000):
#     x = randint(0, columns - 1)
#     y = randint(0, rows - 1)
#     mine_field.left_click(x, y)
#     mine_field.refresh()
#     field_num = mine_field.get_number(x, y)
#     if field_num == -3:
#         mine_field.restart()
#
# ans = []
#
# print(mine_field.map_dimensions())
# print(mine_field.win_rect)

# print(ans)
