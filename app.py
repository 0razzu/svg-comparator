import math
import tkinter as tk
from collections import namedtuple
from tkinter import filedialog
import cairosvg

from svgpathtools import svg2paths, svg2paths2, CubicBezier, QuadraticBezier, Arc, Line

Point = namedtuple('Point', ['x', 'y'])

COLOR_LINE = 'black'
COLOR_CUBIC = 'blue'
COLOR_QUAD = 'green'
COLOR_ARC = 'magenta'
COLOR_INT_POINT = 'orange'
COLOR_END_POINT = 'red'

DIR_LEFT = Point(-1, 0)
DIR_RIGHT = Point(1, 0)
DIR_UP = Point(0, -1)
DIR_DOWN = Point(0, 1)


def _to_x_y(complex_point):
    return Point(complex_point.real, complex_point.imag)


class SVGComparator:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, bg='white', width=50, height=50)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.scale = 10
        self.filename = None
        self.svg = None
        self.int_points = []
        self.end_points = []
        self.create_menu()
        self.bind_events()
        self.drag_data = Point(0, 0)
        self.svg_lt_pos = Point(0, 0)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Open SVG', command=self.open_svg)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.root.quit)
        menubar.add_cascade(label='File', menu=file_menu)

        scale_menu = tk.Menu(menubar, tearoff=0)
        scale_menu.add_command(label='Scale Up', command=self.scale_up)
        scale_menu.add_command(label='Scale Down', command=self.scale_down)
        menubar.add_cascade(label='Scale', menu=scale_menu)

        self.root.config(menu=menubar)

    def bind_events(self):
        self.root.bind('<MouseWheel>', self.mouse_wheel)
        self.root.bind('<Command-equal>', self.scale_up)
        self.root.bind('<Command-minus>', self.scale_down)
        self.root.bind("<Left>", lambda _: self.move_canvas(DIR_LEFT))
        self.root.bind("<Right>", lambda _: self.move_canvas(DIR_RIGHT))
        self.root.bind("<Up>", lambda _: self.move_canvas(DIR_UP))
        self.root.bind("<Down>", lambda _: self.move_canvas(DIR_DOWN))
        fast_move_speed = 10
        self.root.bind("<Shift-Left>", lambda _: self.move_canvas(DIR_LEFT, fast_move_speed))
        self.root.bind("<Shift-Right>", lambda _: self.move_canvas(DIR_RIGHT, fast_move_speed))
        self.root.bind("<Shift-Up>", lambda _: self.move_canvas(DIR_UP, fast_move_speed))
        self.root.bind("<Shift-Down>", lambda _: self.move_canvas(DIR_DOWN, fast_move_speed))
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_doubleclick)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

    def open_svg(self):
        self.filename = filedialog.askopenfilename(filetypes=[('SVG files', '*.svg')])
        if self.filename:
            self._collect_points()
            self.update_canvas()

    def _collect_points(self):
        svg, _ = svg2paths(self.filename)

        for path in svg:
            for segment in path:
                start = _to_x_y(segment.start)
                end = _to_x_y(segment.end)

                if len(self.end_points) == 0 or self.end_points[-1] != start:
                    self.end_points.append(start)
                self.end_points.append(end)

                if type(segment) is CubicBezier:
                    control1 = _to_x_y(segment.control1)
                    control2 = _to_x_y(segment.control2)

                    self.int_points.append(control1)
                    self.int_points.append(control2)

                elif type(segment) is QuadraticBezier:
                    control = _to_x_y(segment.control)

                    self.int_points.append(control)

    def update_canvas(self):
        self.draw_svg()
        self.draw_points()

    def _scale(self, point):
        return self.scale * point.x, self.scale * point.y

    def draw_svg(self):
        self.canvas.delete('svg')

        _, _, meta = svg2paths2(self.filename)
        xlt, ylt, xrb, yrb = map(int, meta['viewBox'].split())
        width, height = xrb - xlt, yrb - ylt
        png = cairosvg.svg2png(file_obj=open(self.filename, "rb"),
                               output_width=self.scale * width,
                               output_height=self.scale * height)
        image = tk.PhotoImage(data=png)
        self.canvas.create_image(*self.svg_lt_pos, anchor=tk.NW, image=image, tags=('svg',))
        self.canvas.image = image  # Keeping a reference to the image to prevent garbage collection

    def _draw_points(self, points, color):
        if len(points) > 0:
            for point in points:
                self.canvas.create_oval(self.svg_lt_pos.x + point.x * self.scale - 3,
                                        self.svg_lt_pos.y + point.y * self.scale - 3,
                                        self.svg_lt_pos.x + point.x * self.scale + 3,
                                        self.svg_lt_pos.y + point.y * self.scale + 3,
                                        fill=color, outline=COLOR_LINE, tags=('point',))

    def draw_points(self):
        self.canvas.delete('point')

        self._draw_points(self.end_points, COLOR_END_POINT)
        self._draw_points(self.int_points, COLOR_INT_POINT)

    def scale_up(self, event=None):
        self.scale *= 1.1
        self.update_canvas()

    def scale_down(self, event=None):
        self.scale /= 1.1
        self.update_canvas()

    def move_canvas(self, direction, speed=1):
        sgn = lambda x: x / abs(x) if x != 0 else 0
        delta = Point(speed * sgn(direction.x), speed * sgn(direction.y))

        self.svg_lt_pos = Point(self.svg_lt_pos.x + delta.x, self.svg_lt_pos.y + delta.y)
        self.canvas.move('all', delta.x, delta.y)

    def mouse_wheel(self, event):
        if event.delta > 0:
            self.scale_up()
        else:
            self.scale_down()

    def on_canvas_click(self, event):
        self.drag_data = Point(event.x, event.y)

    def on_canvas_drag(self, event):
        x = event.x
        y = event.y

        delta_x = x - self.drag_data.x
        delta_y = y - self.drag_data.y
        self.svg_lt_pos = Point(self.svg_lt_pos.x + delta_x, self.svg_lt_pos.y + delta_y)
        self.canvas.move('all', delta_x, delta_y)
        self.drag_data = Point(x, y)

    def on_canvas_doubleclick(self, _):
        self.canvas.moveto('all', 0, 0)
        self.drag_data = Point(0, 0)


if __name__ == '__main__':
    root = tk.Tk()
    root.title('SVG Comparator')
    root.geometry(f'{root.winfo_screenwidth() // 2}x{root.winfo_screenheight() // 2}')
    editor = SVGComparator(root)
    root.mainloop()
