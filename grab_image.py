import win32gui
import mss
import mss.tools
import time

with mss.mss() as sct:

    handle = win32gui.FindWindow(None, 'Minesweeper X')
    assert handle != 0, 'Window not found'

    _left, _top, _right, _bottom = win32gui.GetClientRect(handle)
    left, top = win32gui.ClientToScreen(handle, (_left, _top))
    right, bottom = win32gui.ClientToScreen(handle, (_right, _bottom))
    window_rect = dict(top=top,
                       left=left,
                       width=right - left,
                       height=bottom - top)
    print(window_rect)
    x = time.time()
    image = sct.grab(window_rect)
    print(time.time() - x)
    mss.tools.to_png(image.rgb, image.size, output='test.png')

