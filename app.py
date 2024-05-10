import tkinter as tk
from tkinter import filedialog, font

from consts import *
from point import *
from svg import Svg


class SVGComparator:
    def __init__(self, root):
        self.root = root

        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg='white')
        self.canvas.images = {}  # Against GC
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.layers_frame = tk.Frame(root)
        self.layers_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.layers_canvas = tk.Canvas(self.layers_frame)
        self.layers_scrollbar = tk.Scrollbar(self.layers_frame, orient=tk.HORIZONTAL, command=self.layers_canvas.xview)

        self.layers_list = tk.Frame(self.layers_canvas)
        self.layers_list.bind(
            '<Configure>',
            lambda e: self.layers_canvas.configure(scrollregion=self.layers_canvas.bbox(tk.ALL))
        )
        self.layers_canvas.create_window((0, 0), window=self.layers_list, anchor=tk.NW)
        self.layers_canvas.configure(xscrollcommand=self.layers_scrollbar.set)

        self.layers_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.layers_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.scale = 10
        self.filename = None
        self.svgs = {}
        self.points_visible = True
        self.points_checkbutton_flag = tk.BooleanVar(value=self.points_visible)
        self.drag_data = Point(0, 0)
        self.selected_layers = set()

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
        self.root.bind('<Command-equal>', lambda _: self.scale_up())
        self.root.bind('<Command-minus>', lambda _: self.scale_down())
        self.root.bind('<Left>', lambda _: self.move_canvas(DIR_LEFT))
        self.root.bind('<Right>', lambda _: self.move_canvas(DIR_RIGHT))
        self.root.bind('<Up>', lambda _: self.move_canvas(DIR_UP))
        self.root.bind('<Down>', lambda _: self.move_canvas(DIR_DOWN))
        fast_move_speed = 10
        self.root.bind('<Shift-Left>', lambda _: self.move_canvas(DIR_LEFT, fast_move_speed))
        self.root.bind('<Shift-Right>', lambda _: self.move_canvas(DIR_RIGHT, fast_move_speed))
        self.root.bind('<Shift-Up>', lambda _: self.move_canvas(DIR_UP, fast_move_speed))
        self.root.bind('<Shift-Down>', lambda _: self.move_canvas(DIR_DOWN, fast_move_speed))
        self.root.bind('<space>', lambda _: self.toggle_point_visibility())
        self.canvas.bind('<MouseWheel>', self.on_canvas_scroll)
        self.canvas.bind('<ButtonPress-1>', self.on_canvas_click)
        self.canvas.bind('<Double-Button-1>', lambda _: self.move_canvas_to_origin())
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.layers_canvas.bind('<MouseWheel>', self.on_layers_canvas_scroll)

    def open_svg(self):
        filename = filedialog.askopenfilename(filetypes=[('SVG files', '*.svg')])
        if filename:
            svg = Svg(filename)
            self.svgs[filename] = svg
            self.update_canvas()
            self.add_layer(svg)
            self.selected_layers.add(svg)

    def add_layer(self, svg):
        frame = tk.Frame(self.layers_list)

        eye_button = tk.Button(frame, text='👁', command=lambda: self.toggle_layer_visibility(svg))
        eye_button.pack(side=tk.LEFT)

        tick = tk.Checkbutton(frame, command=lambda: self.toggle_layer_selection(svg))
        tick.select()
        tick.pack(side=tk.LEFT)

        description_frame = tk.Frame(frame)

        def add_line(text, **kwargs):
            text_frame = tk.Frame(description_frame)
            text_frame.pack(side=tk.TOP, fill=tk.X, expand=True)
            tk.Label(text_frame, text=text, **kwargs).pack(side=tk.LEFT)

        add_line(svg.filename, font=font.Font(weight='bold'))
        add_line(f'End points: {len(svg.end_points)}')
        add_line(f'Internal points: {len(svg.int_points)}')
        add_line(f'Commands: {svg.cmd_quans['all']}')
        add_line(f'Moves: {svg.cmd_quans['move']}')
        add_line(f'Lines: {svg.cmd_quans['line']}')
        add_line(f'Cubic beziers: {svg.cmd_quans['cubic']}')
        add_line(f'Quadratic beziers: {svg.cmd_quans['quadratic']}')
        add_line(f'Arcs: {svg.cmd_quans['arc']}')
        description_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        frame.pack(side=tk.TOP, fill=tk.X, expand=True)

    def toggle_layer_visibility(self, svg):
        for layer_frame in self.layers_list.winfo_children():
            if svg.id == self.svgs[
                layer_frame.winfo_children()[2].winfo_children()[0].winfo_children()[0].cget('text')
            ].id:
                eye_button = layer_frame.winfo_children()[0]
                if eye_button.cget('text') == '👁':
                    svg.visible = False
                    eye_button.config(text='🚫')
                    self.canvas.delete(svg.id)
                else:
                    svg.visible = True
                    eye_button.configure(text='👁')
                    self.draw_svg(svg)
                    self.draw_points(svg)
                break

    def toggle_layer_selection(self, svg):
        for layer_frame in self.layers_list.winfo_children():
            tick = layer_frame.winfo_children()[1]

            filename = layer_frame.winfo_children()[2].cget('text')
            if svg.id == self.svgs[filename].id:
                if svg in self.selected_layers:
                    tick.deselect()
                    self.selected_layers.remove(svg)
                else:
                    tick.select()
                    self.selected_layers.add(svg)

    def update_canvas(self):
        for svg in self.svgs.values():
            self.draw_svg(svg)
            self.draw_points(svg)

    def draw_svg(self, svg):
        if not svg.visible:
            return

        self.canvas.delete(f'{svg.id}.image')

        image = tk.PhotoImage(data=svg.get_png(self.scale))
        self.canvas.create_image(svg.lt_pos.x, svg.lt_pos.y, anchor=tk.NW, image=image,
                                 tags=(f'{svg.id}.image', svg.id, 'image'))
        self.canvas.images[svg.id] = image  # Keeping a reference to the image to prevent garbage collection

    def _draw_points(self, svg, points, color):
        if len(points) > 0:
            for point in points:
                pos = svg.lt_pos + point * self.scale
                self.canvas.create_oval(pos.x - 3, pos.y - 3, pos.x + 3, pos.y + 3,
                                        fill=color, outline=COLOR_LINE, tags=(f'{svg.id}.point', svg.id, 'point'))

    def draw_points(self, svg):
        if not svg.visible:
            return

        self.canvas.delete(f'{svg.id}.point', f'{svg.id}.connector')

        if self.points_visible:
            self._draw_points(svg, svg.int_points, COLOR_INT_POINT)

            lt_pos = svg.lt_pos
            for int_point in svg.int_points:
                for end_point in int_point.whose:
                    self.canvas.create_line(lt_pos.x + self.scale * int_point.x,
                                            lt_pos.y + self.scale * int_point.y,
                                            lt_pos.x + self.scale * end_point.x,
                                            lt_pos.y + self.scale * end_point.y,
                                            fill=COLOR_CONNECTOR, width=1, arrow=tk.FIRST,
                                            tags=(f'{svg.id}.connector', svg.id, 'connector'))

            self._draw_points(svg, svg.end_points, COLOR_END_POINT)

    def scale_up(self):
        self.scale *= 1.1
        self.update_canvas()

    def scale_down(self):
        self.scale /= 1.1
        self.update_canvas()

    def move_canvas(self, direction, speed=1):
        delta = speed * direction

        for svg in self.selected_layers:
            svg.lt_pos += delta
            self.canvas.move(svg.id, delta.x, delta.y)

    def on_canvas_scroll(self, event):
        if event.delta > 0:
            self.scale_up()
        else:
            self.scale_down()

    def toggle_point_visibility(self):
        self.points_visible = not self.points_visible
        self.points_checkbutton_flag.set(self.points_visible)
        for svg in self.svgs.values():
            self.draw_points(svg)

    def on_canvas_click(self, event):
        self.drag_data = Point(event.x, event.y)

    def on_canvas_drag(self, event):
        dest = Point(event.x, event.y)
        self.move_canvas(dest - self.drag_data)
        self.drag_data = dest

    def move_canvas_to_origin(self):
        self.drag_data = Point(0, 0)
        for svg in self.svgs.values():
            self.canvas.moveto(svg.id, 0, 0)
            svg.lt_pos = Point(0, 0)

    def on_layers_canvas_scroll(self, event):
        self.layers_canvas.xview_scroll(-event.delta, 'units')


if __name__ == '__main__':
    root = tk.Tk()
    root.title('SVG Comparator')
    root.geometry(f'{root.winfo_screenwidth() // 2}x{root.winfo_screenheight() // 2}')
    editor = SVGComparator(root)
    root.mainloop()
