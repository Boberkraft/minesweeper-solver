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
    FIELD_WIDTH = 16
    FIELD_HEIGHT = 16
    NUMBERS = {
        (192, 192, 192): 0,
        (0, 0, 255): 1,
        (0, 128, 0): 2,
        (255, 0, 0): 3,
        (0, 0, 128): 4,
        (128, 0, 0): 5,
        (0, 128, 128): 6,
        (0, 0, 0): 7,
        (128, 128, 128): 8
    }
    DARK_GREY = (128, 128, 128)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    BLACK = (0, 0, 0)
    LINEAR_SEARCH_RANGE = 5

    # 0 to pusta kratka
    # -2 mina
    # -5 źle postawiona flaga
    # -3 nadepnięta miną
    # 1,2,3,4,5,6,7,8 liczba
    # -1 nieodkryta krata
    # -4 flaga
    def __init__(self):
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

    def init(self):

        # sleep(1)
        self.rows, self.columns = self.map_dimensions()
        self.net_mask = [[0 for _ in range(self.rows)] for _ in range(self.rows)]
        self.refresh()  # załaduj obraz mape
        # sleep(1)

    def click_restart_button(self):
        x = self.win_rect['left'] + self.win_rect['width'] // 2  # X of the face
        y = self.win_rect['top'] + 20  # Y of the face

        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def right_click(self, tile_x: int, tile_y: int):
        x, y = self._from_tile(tile_x, tile_y)
        x += self.win_rect['left']
        y += self.win_rect['top']
        # sleep(0.02)
        win32api.SetCursorPos((x, y))
        # sleep(0.02)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)

        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)

    def left_click(self, tile_x: int, tile_y: int):
        x, y = self._from_tile(tile_x, tile_y)
        x += self.win_rect['left']
        y += self.win_rect['top']
        # sleep(0.02)
        win32api.SetCursorPos((x, y))
        # sleep(0.02)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

        # win32api.SetCursorPos((self.win_rect['left'], self.win_rect['top']))
        # self.get_number(x, y)
        # self.get_tile_image(tile_x, tile_y)

    def refresh(self) -> None:
        """Odświeża obraz mapy"""
        win32api.SetCursorPos((self.win_rect['left'], self.win_rect['top']))
        self.image_map = self.sct.grab(self.win_rect)
        self.load_to_array()

    def get_tile_image(self, tile_x: int, tile_y: int) -> None:
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
        """Zamienia koordynaty ekranu na x i y planszy"""
        x = self.map_x + self.FIELD_WIDTH * tile_x
        y = self.map_y + self.FIELD_HEIGHT * tile_y
        return x, y

    def get_number(self, tile_x: int, tile_y: int, image=None) -> int:

        x, y = self._from_tile(tile_x, tile_y)
        if image is None:
            image = self.image_map
        # objaśnienie pól
        # -2 -2 -1 -2 -2 -1 -2 -2
        # -2 -2 -2 -1 -2 -1 -2 -2
        # -2 -3 -2 -1 -2  6 -2 -2
        # -2 -2 -2 -1 -1 -2 -2 -2
        # -2 -1 -2 -2  5 -1 -2 -2
        # -2 -2 -2 -2 -2 -2 -2 -2
        # -2 -2 -2 -2 -2 -2 -2 -2
        # -1 -2 -1 -1 -2 -2 -2 -2

        # 0 to pusta kratka  (lewy górny róg jest szary)
        #    -2 mina (7, 7 jest biały)
        #        -5 źle postawiona flaga (8,8 jest czerwony)
        #        -3 nadepnięta miną (1,1 jest czerwony)
        #    1,2,3,4,5,6,7,8 oznaczaja kratki z napisaną liczbą (8, 9 mają odpowiednie kolory)
        # -1 nieodkryta krata (0,0 jest biały)
        #    -4 flaga (8,8 jest czarny)

        if image.pixel(x, y) == self.DARK_GREY:
            # puste pole

            if image.pixel(x + 7, y + 7) == self.WHITE:
                # mina
                if image.pixel(x + 8, y + 8) == self.RED:
                    # źle postawiona flaga
                    return -5
                elif image.pixel(x + 1, y + 1) == self.RED:
                    # nadepnięta mina
                    return -3
                return -2
            else:
                # liczba lub puste pole
                return self.NUMBERS[image.pixel(x + 9, y + 8)]

        elif image.pixel(x, y) == self.WHITE:
            # nieodkryta krata
            # print('unknown')
            if image.pixel(x + 8, y + 8) == self.BLACK:
                return -4
            return -1
        else:
            # print('?')
            raise Exception('{}x{} contains \n\nZabierz wszystkie rzeczy z gry pacanie'.format(tile_x, tile_y))

    def map_dimensions(self):
        return self.field_dimensions(self.win_rect['width'], self.win_rect['height'])

    def field_dimensions(self, width: int, height: int) -> (int, int):
        h = height - (self.map_y + self.map_x)
        w = width - 2 * self.map_x
        return w // self.FIELD_WIDTH, h // self.FIELD_HEIGHT

    def __str__(self):
        ans = []
        for row in self.map:
            ans.append(' '.join(' ' + str(n) if n >= 0 else str(n) for n in row))
        return '\n'.join(ans)

    def __repr__(self):

        ans = []
        for row in self.net_mask:
            ans.append(' '.join(str(n) for n in row))
        return str(self) + '\n' + '\n'.join(ans)

    def load_to_array(self):

        columns, rows = self.map_dimensions()
        self.map = []
        for y in range(rows):
            n = []
            for x in range(columns):
                num = self.get_number(x, y)
                n.append(num)
                if self.net_mask[y][x] == 0:
                    if num == 0 or num == -4:
                        # pusta kratka lub flaga
                        self.net_mask[y][x] = 1
            self.map.append(n)

    def solver(self):

        last_random_choice = (-1, -1)
        while True:
            changed = self._solver()
            self.refresh()
            if not changed:
                # print(repr(self))
                x, y, prob = self.linear_equasions()
                if prob < 0.5:
                    self.left_click(x, y)
                else:
                    self.right_click(x, y)
                # x, y = self._press_random_field()
                self.refresh()
                if self.get_number(x, y) == -3:
                    print('Wylosowane złą liczbę!')
                    return False
                else:
                    print('Wszystko wygląda spoko!')
                last_random_choice = (x, y)
                # print(repr(self))
                # sleep(3)

    def in_bounds(self, _x: int, _y: int):
        return 0 <= _y < self.columns and 0 <= _x < self.rows

    def _solver(self):

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

    def _press_random_field(self):
        for y in range(self.columns):
            for x in range(self.rows):
                if self.map[y][x] == -1:
                    print('Random choice! ({}, {})'.format(x, y))
                    self.left_click(x, y)
                    return x, y
        return None, None

    def linear_equasions(self):
        def do_equasion(x, y):
            eq = dict()
            sum = self.map[y][x]
            for _y in range(-1, 2):
                _y += y
                for _x in range(-1, 2):
                    _x += x
                    if self.in_bounds(_x, _y):
                        if self.map[_y][_x] == -1:
                            # jeżeli puste pole
                            eq[(_x, _y)] = 1
                        if self.map[_y][_x] == -4:
                            # jeżeli falga
                            eq[(_x, _y)] = -1
            return eq, sum

        candidates = self._get_candidate()
        # print('Kandydaci', candidates)
        print('*'*10)
        sums = []
        equasions = []
        variables = set()
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
        print(keys)
        for eq, s in zip(a, b):
            pass
            print(eq, '->', s)
        [print(c, '=', o) for c, o in zip(equasions,sums)]
        try:
            solution = np.linalg.solve(a, b).round(3)
            print('Dokładne obliczanie równanie!!!!')
        except:
            x = np.linalg.lstsq(a, b)
            print(x)
            solution = x[0].round(decimals=3)
            print('-' * 10)
            print('Niedokładne obliczanie równania')

        print('[\n',
              '\n'.join([str(key) + ' -> ' + str(h) for h, key in zip(solution, keys)]),
              '\n]')

        min_index, prob = min(enumerate(solution), key=lambda p: abs(p[1]))
        x, y = keys[min_index]
        print('{} with {} probability that its a mine!'.format((x, y), abs(prob)))
        # self.left_click(x, y)
        return x, y, prob
        # return None, None

    def _get_candidate(self):
        for y in range(self.columns):
            for x in range(self.rows):
                if self.net_mask[y][x] == 0 and 0 < self.map[y][x] <= 8:
                    q = set()
                    print('The candidate!', x, y)
                    self._for_search(x, y, q)
                    return q
        return None

    def _for_search(self, x, y, queue):

        movement = self.LINEAR_SEARCH_RANGE - len(queue)
        new = set()
        if self.LINEAR_SEARCH_RANGE <= len(queue):
            return
        for _y in range(-1, 2):
            _y += y
            for _x in range(-1, 2):
                _x += x
                if self.in_bounds(_x, _y) and 0 < self.map[_y][_x] <= 7:
                    if (_x, _y) not in queue:
                        new.add((_x, _y))
        queue.update(new)
        for x_, y_ in new:
            self._for_search(x_, y_, queue)


def test_number_finding():
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


test_number_finding()

if __name__ == '__main__':
    mine_field = MineField()
    solved = False
    while True:
        #
        # mine_field.restart()
        start = time.time()
        solved = mine_field.solver()
        break
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
# for y in range(rows):
#     row = []
#     for x in range(columns):
#         ans.append(mine_field.get_number(x, y))
#         row.append(mine_field.get_number(x, y))
#     print(' '.join(' ' + str(n) if n >= 0 else str(n) for n in row))
# print(ans)
