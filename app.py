import tkinter as tk
from tkinter import filedialog

import cairosvg
from svgpathtools import svg2paths, svg2paths2, CubicBezier, QuadraticBezier


class Point:
    def __init__(self, x, y, whose=None):
        self.x = x
        self.y = y
        self.whose = whose

    def __add__(self, other):
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y, self.whose)
        else:
            return Point(self.x + other, self.y + other, self.whose)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y, self.whose)
        else:
            return Point(self.x - other, self.y - other, self.whose)

    def __rsub__(self, other):
        return self - other

    def __mul__(self, coef):
        return Point(self.x * coef, self.y * coef, self.whose)

    def __rmul__(self, coef):
        return Point(coef * self.x, coef * self.y, self.whose)


COLOR_LINE = 'black'
COLOR_CUBIC = 'blue'
COLOR_QUAD = 'green'
COLOR_ARC = 'magenta'
COLOR_INT_POINT = 'orange'
COLOR_END_POINT = 'red'
COLOR_CONNECTOR = 'violet'

DIR_LEFT = Point(-1, 0)
DIR_RIGHT = Point(1, 0)
DIR_UP = Point(0, -1)
DIR_DOWN = Point(0, 1)


def _complex_to_point(complex_point):
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
        self.points_visible = True
        self.points_checkbutton_flag = tk.BooleanVar(value=self.points_visible)
        self.drag_data = Point(0, 0)
        self.svg_lt_pos = Point(0, 0)
        self.create_menu()
        self.bind_events()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Open SVG', command=self.open_svg)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.root.quit)
        menubar.add_cascade(label='File', menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label='Scale Up', command=self.scale_up)
        view_menu.add_command(label='Scale Down', command=self.scale_down)
        view_menu.add_separator()
        view_menu.add_command(label='Move Left', command=lambda: self.move_canvas(DIR_LEFT))
        view_menu.add_command(label='Move Right', command=lambda: self.move_canvas(DIR_RIGHT))
        view_menu.add_command(label='Move Up', command=lambda: self.move_canvas(DIR_UP))
        view_menu.add_command(label='Move Down', command=lambda: self.move_canvas(DIR_DOWN))
        view_menu.add_command(label='Move to Origin', command=self.move_canvas_to_origin)
        view_menu.add_separator()
        view_menu.add_checkbutton(label='Show Control Points', variable=self.points_checkbutton_flag,
                                  command=self.toggle_point_visibility)
        menubar.add_cascade(label='View', menu=view_menu)

        self.root.config(menu=menubar)

    def bind_events(self):
        self.root.bind('<MouseWheel>', self.mouse_wheel)
        self.root.bind('<Command-equal>', lambda _: self.scale_up)
        self.root.bind('<Command-minus>', lambda _: self.scale_down)
        self.root.bind("<Left>", lambda _: self.move_canvas(DIR_LEFT))
        self.root.bind("<Right>", lambda _: self.move_canvas(DIR_RIGHT))
        self.root.bind("<Up>", lambda _: self.move_canvas(DIR_UP))
        self.root.bind("<Down>", lambda _: self.move_canvas(DIR_DOWN))
        fast_move_speed = 10
        self.root.bind("<Shift-Left>", lambda _: self.move_canvas(DIR_LEFT, fast_move_speed))
        self.root.bind("<Shift-Right>", lambda _: self.move_canvas(DIR_RIGHT, fast_move_speed))
        self.root.bind("<Shift-Up>", lambda _: self.move_canvas(DIR_UP, fast_move_speed))
        self.root.bind("<Shift-Down>", lambda _: self.move_canvas(DIR_DOWN, fast_move_speed))
        self.root.bind("<space>", lambda _: self.toggle_point_visibility())
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", lambda _: self.move_canvas_to_origin())
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

    def open_svg(self):
        self.filename = filedialog.askopenfilename(filetypes=[('SVG files', '*.svg')])
        if self.filename:
            self._collect_points()
            self.update_canvas()

    def _collect_points(self):
        self.int_points = []
        self.end_points = []
        svg, _ = svg2paths(self.filename)

        for path in svg:
            for segment in path:
                start = _complex_to_point(segment.start)
                end = _complex_to_point(segment.end)

                if len(self.end_points) == 0 or self.end_points[-1] != start:
                    self.end_points.append(start)
                self.end_points.append(end)

                if type(segment) is CubicBezier:
                    control1 = _complex_to_point(segment.control1)
                    control1.whose = [start]
                    control2 = _complex_to_point(segment.control2)
                    control2.whose = [end]

                    self.int_points.append(control1)
                    self.int_points.append(control2)

                elif type(segment) is QuadraticBezier:
                    control = _complex_to_point(segment.control)
                    control.whose = [start, end]

                    self.int_points.append(control)

    def update_canvas(self):
        self.draw_svg()
        self.draw_points()

    def draw_svg(self):
        if not self.filename:
            return

        self.canvas.delete('svg')

        _, _, meta = svg2paths2(self.filename)
        xlt, ylt, xrb, yrb = map(int, meta['viewBox'].split())
        width, height = xrb - xlt, yrb - ylt
        png = cairosvg.svg2png(file_obj=open(self.filename, "rb"),
                               output_width=self.scale * width,
                               output_height=self.scale * height)
        image = tk.PhotoImage(data=png)
        self.canvas.create_image(self.svg_lt_pos.x, self.svg_lt_pos.y, anchor=tk.NW, image=image, tags=('svg',))
        self.canvas.image = image  # Keeping a reference to the image to prevent garbage collection

    def _draw_points(self, points, color):
        if len(points) > 0:
            for point in points:
                pos = self.svg_lt_pos + point * self.scale
                self.canvas.create_oval(pos.x - 3, pos.y - 3, pos.x + 3, pos.y + 3,
                                        fill=color, outline=COLOR_LINE, tags=('point',))

    def draw_points(self):
        self.canvas.delete('point', 'connector')

        if self.points_visible:
            self._draw_points(self.int_points, COLOR_INT_POINT)

            for int_point in self.int_points:
                for end_point in int_point.whose:
                    self.canvas.create_line(self.svg_lt_pos.x + self.scale * int_point.x,
                                            self.svg_lt_pos.y + self.scale * int_point.y,
                                            self.svg_lt_pos.x + self.scale * end_point.x,
                                            self.svg_lt_pos.y + self.scale * end_point.y,
                                            fill=COLOR_CONNECTOR, width=1, arrow=tk.FIRST, tags=('connector',))

            self._draw_points(self.end_points, COLOR_END_POINT)

    def scale_up(self):
        self.scale *= 1.1
        self.update_canvas()

    def scale_down(self):
        self.scale /= 1.1
        self.update_canvas()

    def move_canvas(self, direction, speed=1):
        delta = speed * direction

        self.svg_lt_pos = self.svg_lt_pos + delta
        self.canvas.move('all', delta.x, delta.y)

    def mouse_wheel(self, event):
        if event.delta > 0:
            self.scale_up()
        else:
            self.scale_down()

    def toggle_point_visibility(self):
        self.points_visible = not self.points_visible
        self.points_checkbutton_flag.set(self.points_visible)
        self.draw_points()

    def on_canvas_click(self, event):
        self.drag_data = Point(event.x, event.y)

    def on_canvas_drag(self, event):
        dest = Point(event.x, event.y)
        self.move_canvas(dest - self.drag_data)
        self.drag_data = dest

    def move_canvas_to_origin(self):
        self.canvas.moveto('all', 0, 0)
        self.drag_data = Point(0, 0)
        self.svg_lt_pos = Point(0, 0)


if __name__ == '__main__':
    root = tk.Tk()
    root.title('SVG Comparator')
    root.geometry(f'{root.winfo_screenwidth() // 2}x{root.winfo_screenheight() // 2}')
    editor = SVGComparator(root)
    root.mainloop()
