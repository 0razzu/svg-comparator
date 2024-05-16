import tkinter as tk
from tkinter import filedialog, font, messagebox

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
        _create_grid(self.canvas)

        self.layers_frame = tk.Frame(root)
        _add_layers_canvas_tag(self.layers_frame)
        self.layers_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.layers_canvas = tk.Canvas(self.layers_frame)
        _add_layers_canvas_tag(self.layers_canvas)
        self.layers_vscrollbar = tk.Scrollbar(self.layers_frame, orient=tk.VERTICAL,
                                              command=self.layers_canvas.yview)
        self.layers_hscrollbar = tk.Scrollbar(self.layers_frame, orient=tk.HORIZONTAL,
                                              command=self.layers_canvas.xview)

        self.layers_list = tk.Frame(self.layers_canvas)
        _add_layers_canvas_tag(self.layers_list)
        self.layers_list.bind(
            '<Configure>',
            lambda e: self.layers_canvas.configure(scrollregion=self.layers_canvas.bbox(tk.ALL))
        )
        self.layers_canvas.create_window((0, 0), window=self.layers_list, anchor=tk.NW)
        self.layers_canvas.configure(yscrollcommand=self.layers_vscrollbar.set)
        self.layers_canvas.configure(xscrollcommand=self.layers_hscrollbar.set)

        self.layers_hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.layers_vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.layers_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.scale = 10
        self.svgs = {}
        self.ordered_svgs = []
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
        view_menu.add_command(label='Move to Origin', command=self.move_layers_to_origin)
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
        self.canvas.bind('<Double-Button-1>', lambda _: self.move_layers_to_origin())
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.layers_canvas.bind_class('LayersCanvas', '<MouseWheel>', self.on_layers_canvas_vscroll)
        self.layers_canvas.bind_class('LayersCanvas', '<Shift-MouseWheel>', self.on_layers_canvas_hscroll)

    def open_svg(self):
        trying = True

        while trying:
            filename = filedialog.askopenfilename(filetypes=[('SVG files', '*.svg')])
            trying = False
            if filename:
                if filename in self.svgs.keys():
                    svg_idx = self._svg_idx(self.svgs[filename].id)
                    trying = messagebox.askretrycancel(title='Error',
                                                       message=f'This SVG is already opened as #{svg_idx + 1}')
                    continue

                svg = Svg(filename)
                self.svgs[filename] = svg
                self.ordered_svgs.append(svg)
                self.selected_layers.add(svg)
                self.update_canvas()
                self.add_to_layers_list(svg)

    def add_to_layers_list(self, svg):
        idx = len(self.layers_list.winfo_children())

        layer_frame = tk.Frame(self.layers_list)
        _add_layers_canvas_tag(layer_frame)

        button_frame = tk.Frame(layer_frame)
        _add_layers_canvas_tag(button_frame)

        idx_label = tk.Label(button_frame, text=f'#{idx + 1}')
        _add_layers_canvas_tag(idx_label)
        idx_label.pack(side=tk.TOP)

        tick = tk.Checkbutton(button_frame, command=lambda: self.toggle_layer_selection(svg))
        _add_layers_canvas_tag(tick)
        if svg in self.selected_layers:
            tick.select()
        tick.pack(side=tk.TOP)

        eye_button = tk.Button(button_frame, text='👁' if svg.visible else '🚫',
                               command=lambda: self.toggle_layer_visibility(svg))
        _add_layers_canvas_tag(eye_button)
        eye_button.pack(side=tk.TOP)

        if idx > 0:
            prev_down_button = self.layers_list.winfo_children()[idx - 1].winfo_children()[0].winfo_children()[4]
            prev_down_button['state'] = tk.NORMAL
        up_button = tk.Button(button_frame, text='🔼', command=lambda: self.move_layer_up(idx))
        _add_layers_canvas_tag(up_button)
        if svg.id == self.ordered_svgs[0].id:
            up_button['state'] = tk.DISABLED
        up_button.pack(side=tk.TOP)
        down_button = tk.Button(button_frame, text='🔽', command=lambda: self.move_layer_down(idx))
        _add_layers_canvas_tag(down_button)
        down_button['state'] = tk.DISABLED
        down_button.pack(side=tk.TOP)

        button_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        description_frame = tk.Frame(layer_frame)
        _add_layers_canvas_tag(description_frame)

        def add_line(text, margin=False, **kwargs):
            text_frame = tk.Frame(description_frame)
            _add_layers_canvas_tag(text_frame)
            text_frame.pack(side=tk.TOP, fill=tk.X, expand=True)
            label = tk.Label(text_frame, text=text, **kwargs)
            _add_layers_canvas_tag(label)
            label.pack(side=tk.LEFT, pady=((0, 5) if margin else (0, 0)))

        add_line(svg.filename, font=font.Font(weight='bold'))
        add_line(f'End points: {len(svg.end_points)}')
        add_line(f'Internal points: {len(svg.int_points)}', margin=True)
        add_line(f'Commands: {svg.cmd_quans['all']}')
        add_line(f'Moves: {svg.cmd_quans['move']}')
        add_line(f'Lines: {svg.cmd_quans['line']}')
        add_line(f'Cubic beziers: {svg.cmd_quans['cubic']}')
        add_line(f'Quadratic beziers: {svg.cmd_quans['quadratic']}')
        add_line(f'Arcs: {svg.cmd_quans['arc']}')

        description_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(0, 10))

        layer_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

    def toggle_layer_visibility(self, svg):
        for layer_frame in self.layers_list.winfo_children():
            if svg.id == self.svgs[
                layer_frame.winfo_children()[1].winfo_children()[0].winfo_children()[0].cget('text')
            ].id:
                eye_button = layer_frame.winfo_children()[0].winfo_children()[2]
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
            tick = layer_frame.winfo_children()[0].winfo_children()[1]

            filename = layer_frame.winfo_children()[1].winfo_children()[0].winfo_children()[0].cget('text')
            if svg.id == self.svgs[filename].id:
                if svg in self.selected_layers:
                    tick.deselect()
                    self.selected_layers.remove(svg)
                else:
                    tick.select()
                    self.selected_layers.add(svg)

    def _swap_layers(self, idx1, idx2):
        self.ordered_svgs[idx1], self.ordered_svgs[idx2] = self.ordered_svgs[idx2], self.ordered_svgs[idx1]

        self.update_canvas()

        for layer in self.layers_list.winfo_children():
            layer.destroy()
        for svg in self.ordered_svgs:
            self.add_to_layers_list(svg)

    def move_layer_up(self, idx):
        if idx == 0:
            return

        self._swap_layers(idx - 1, idx)

    def move_layer_down(self, idx):
        if idx == len(self.ordered_svgs) - 1:
            return

        self._swap_layers(idx, idx + 1)

    def update_canvas(self):
        for svg in self.ordered_svgs:
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

    def _draw_frame(self, svg):
        frame_tags = (f'{svg.id}.frame', svg.id, 'frame')
        lt_x, lt_y = svg.lt_pos.x, svg.lt_pos.y
        rb_x, rb_y = lt_x + self.scale * svg.width, lt_y + self.scale * svg.height

        idx = self._svg_idx(svg.id)
        text = self.canvas.create_text(lt_x, rb_y, anchor=tk.NW, text=f'#{idx + 1}', font=font.Font(size=18),
                                       fill=COLOR_FRAME, tags=frame_tags)

        self.canvas.create_rectangle(lt_x, lt_y, rb_x, rb_y,
                                     outline=COLOR_FRAME, tags=frame_tags)

    def _draw_points(self, svg, points, color):
        if len(points) > 0:
            for point in points:
                pos = svg.lt_pos + point * self.scale
                self.canvas.create_oval(pos.x - 3, pos.y - 3, pos.x + 3, pos.y + 3,
                                        fill=color, outline=COLOR_OUTLINE, tags=(f'{svg.id}.point', svg.id, 'point'))

    def draw_points(self, svg):
        if not svg.visible:
            return

        self.canvas.delete(f'{svg.id}.frame', f'{svg.id}.point', f'{svg.id}.connector')

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

            self._draw_frame(svg)
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
        for svg in self.ordered_svgs:
            self.draw_points(svg)

    def on_canvas_click(self, event):
        self.drag_data = Point(event.x, event.y)

    def on_canvas_drag(self, event):
        dest = Point(event.x, event.y)
        self.move_canvas(dest - self.drag_data)
        self.drag_data = dest

    def move_layers_to_origin(self):
        self.drag_data = Point(0, 0)
        for svg in self.selected_layers:
            self.canvas.moveto(svg.id, 0, 0)
            svg.lt_pos = Point(0, 0)

    def on_layers_canvas_vscroll(self, event):
        self.layers_canvas.yview_scroll(-event.delta, 'units')

    def on_layers_canvas_hscroll(self, event):
        self.layers_canvas.xview_scroll(-event.delta, 'units')

    def _svg_idx(self, svg_id):
        return [*map(lambda s: s.id, self.ordered_svgs)].index(svg_id)


def _create_grid(canvas):
    width = canvas.winfo_screenwidth()
    height = canvas.winfo_screenheight()

    for x in range(0, width, 10):
        canvas.create_line(x, 0, x, height, fill=COLOR_GRID)

    for y in range(0, height, 10):
        canvas.create_line(0, y, width, y, fill=COLOR_GRID)


def add_tag(widget, tag):
    widget.bindtags((tag,) + widget.bindtags())


def _add_layers_canvas_tag(widget):
    add_tag(widget, 'LayersCanvas')


if __name__ == '__main__':
    root = tk.Tk()
    root.title('SVG Comparator')
    root.geometry(f'{root.winfo_screenwidth() // 2}x{root.winfo_screenheight() // 2}')
    editor = SVGComparator(root)
    root.mainloop()
