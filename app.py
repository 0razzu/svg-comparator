import math
import tkinter as tk
from collections import namedtuple
from tkinter import filedialog

from svgpathtools import svg2paths, CubicBezier, QuadraticBezier, Arc, Line

Point = namedtuple('Point', ['x', 'y'])

COLOR_LINE = 'black'
COLOR_CUBIC = 'blue'
COLOR_QUAD = 'green'
COLOR_ARC = 'magenta'
COLOR_INT_POINT = 'orange'
COLOR_END_POINT = 'red'


def _to_x_y(complex_point):
    return Point(complex_point.real, complex_point.imag)


class SVGComparator:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, bg='white', width=50, height=50)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.scale = 10
        self.svg = None
        self.int_points = []
        self.end_points = []
        self.create_menu()
        self.bind_events()
        self.drag_data = Point(0, 0)

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
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_doubleclick)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

    def open_svg(self):
        filename = filedialog.askopenfilename(filetypes=[('SVG files', '*.svg')])
        if filename:
            self.svg, _ = svg2paths(filename)
            self.int_points = []
            self.end_points = []
            self.canvas.delete('all')
            self.draw_svg()
            self.draw_points()

    def _scale(self, point):
        return self.scale * point.x, self.scale * point.y

    def draw_svg(self):
        if self.svg is None:
            return

        for path in self.svg:
            for segment in path:
                start = _to_x_y(segment.start)
                end = _to_x_y(segment.end)

                if len(self.end_points) == 0 or self.end_points[-1] != start:
                    self.end_points.append(start)
                self.end_points.append(end)

                if type(segment) is Line:
                    self.canvas.create_line(*self._scale(start), *self._scale(end),
                                            fill=COLOR_LINE, tags=('shape', 'path'))

                elif type(segment) is CubicBezier:
                    control1 = _to_x_y(segment.control1)
                    control2 = _to_x_y(segment.control2)

                    self.int_points.append(control1)
                    self.int_points.append(control2)

                    self.canvas.create_line(*self._scale(start),
                                            *self._scale(control1), *self._scale(control2),
                                            *self._scale(end), smooth=tk.TRUE,
                                            fill=COLOR_QUAD, tags=('shape', 'path'))

                elif type(segment) is QuadraticBezier:
                    control = _to_x_y(segment.control)

                    self.int_points.append(control)

                    self.canvas.create_line(*self._scale(start),
                                            *self._scale(control),
                                            *self._scale(end), smooth=tk.TRUE,
                                            fill=COLOR_CUBIC, tags=('shape', 'path'))

                elif type(segment) is Arc:
                    ...

    def _draw_points(self, points, color):
        if len(points) > 0:
            for point in points:
                self.canvas.create_oval(point.x * self.scale - 1, point.y * self.scale - 1,
                                        point.x * self.scale + 1, point.y * self.scale + 1,
                                        fill='', outline=color, tags=('point',))

    def draw_points(self):
        self._draw_points(self.end_points, COLOR_END_POINT)
        self._draw_points(self.int_points, COLOR_INT_POINT)

    def scale_up(self, event=None):
        self.scale *= 1.1
        self.canvas.scale('all', 0, 0, 1.1, 1.1)

    def scale_down(self, event=None):
        self.scale /= 1.1
        self.canvas.scale('all', 0, 0, 0.9, 0.9)

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
        self.canvas.move('all', delta_x, delta_y)
        self.drag_data = Point(x, y)

    def on_canvas_doubleclick(self, _):
        x, y = 0, 0

        self.canvas.moveto('all', x, y)
        self.drag_data = Point(0, 0)


if __name__ == '__main__':
    root = tk.Tk()
    root.title('SVG Comparator')
    editor = SVGComparator(root)
    root.mainloop()
