import os
import tkinter as tk
from tkinter import filedialog, font, messagebox, colorchooser, ttk

from consts import *
from point import *
from svg import Svg


class SVGComparator:
    def __init__(self, root):
        self.root = root

        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg='white', borderwidth=0, highlightthickness=0)
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

        self.canvas_scroll_timer_id = None
        self.canvas_opacity_timer_ids = {}

        self.create_menu()
        self.bind_events()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Open SVGs', command=self.open_svgs)
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

    def open_svgs(self):
        trying = True
        already_opened = []

        while trying:
            filenames = filedialog.askopenfilenames(filetypes=[('SVG files', '*.svg')])
            trying = False
            if filenames:
                for filename in filenames:
                    if filename in self.svgs.keys():
                        already_opened.append((filename, self._svg_idx(self.svgs[filename].id)))
                        continue

                    svg = Svg(filename)
                    self.svgs[filename] = svg
                    self.ordered_svgs.append(svg)
                    self.selected_layers.add(svg)
                    self.update_canvas()
                    self.add_to_layers_list(svg)

                if len(already_opened) > 0:
                    trying = messagebox.askretrycancel(
                        title='Error',
                        message='These SVGs are already opened',
                        detail=f',{os.linesep}{os.linesep}'.join(
                            map(lambda p: f'{p[0]} (#{p[1] + 1})', already_opened)),
                    )
                    already_opened.clear()

    def add_to_layers_list(self, svg):
        idx = len(self.layers_list.winfo_children())

        layer_frame = tk.Frame(self.layers_list)
        _add_layers_canvas_tag(layer_frame)

        button_frame = tk.Frame(layer_frame)
        _add_layers_canvas_tag(button_frame)

        idx_label = tk.Label(button_frame, text=f'#{idx + 1}')
        _add_layers_canvas_tag(idx_label)
        idx_label.pack(side=tk.TOP)

        def set_checkbutton(checkbutton, selected):
            if selected:
                checkbutton.select()
            else:
                checkbutton.deselect()

        tick = tk.Checkbutton(button_frame, command=lambda: self.toggle_layer_selection(
            svg,
            lambda selected: set_checkbutton(tick, selected),
        ))
        if svg in self.selected_layers:
            tick.select()
        _add_layers_canvas_tag(tick)
        tick.pack(side=tk.TOP)

        def set_eye_button_text(button, visible):
            button.configure(text=('👁' if visible else '🚫'))

        eye_button = tk.Button(button_frame, command=lambda: self.toggle_layer_visibility(
            svg,
            lambda visible: set_eye_button_text(eye_button, visible),
        ))
        set_eye_button_text(eye_button, True)
        _add_layers_canvas_tag(eye_button)
        eye_button.pack(side=tk.TOP)

        if idx > 0:
            prev_down_button = self.layers_list.winfo_children()[idx - 1].down_button
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

        color_button = tk.Button(button_frame, text='🖌️', command=lambda: self.set_svg_color(svg))
        _add_layers_canvas_tag(color_button)
        color_button.pack(side=tk.TOP)

        close_button = tk.Button(button_frame, text='❌', command=lambda: self.close_svg(svg, idx))
        _add_layers_canvas_tag(close_button)
        close_button.pack(side=tk.TOP)

        button_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        description_frame = tk.Frame(layer_frame)
        _add_layers_canvas_tag(description_frame)

        opacity_frame = tk.Frame(layer_frame)
        _add_layers_canvas_tag(opacity_frame)

        opacity_label = tk.Label(opacity_frame, anchor=tk.N, width=3)
        _add_layers_canvas_tag(opacity_label)

        def update_opacity_label(val):
            opacity_label.configure(text=str(int(val * 100)))

        update_opacity_label(svg.opacity)

        opacity_scale = ttk.Scale(opacity_frame, orient=tk.VERTICAL,
                                  from_=0, to=1,
                                  value=svg.opacity,
                                  command=lambda val: self.set_svg_opacity(svg, float(val), update_opacity_label))
        _add_layers_canvas_tag(opacity_scale)

        opacity_scale.pack(side=tk.TOP, fill=tk.Y, expand=True)
        opacity_label.pack(side=tk.TOP, fill=tk.X, expand=False)

        opacity_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        def add_line(text, margin=False, **kwargs):
            text_frame = tk.Frame(description_frame)
            _add_layers_canvas_tag(text_frame)
            text_frame.pack(side=tk.TOP, fill=tk.X, expand=True)
            label = tk.Label(text_frame, text=text, **kwargs)
            _add_layers_canvas_tag(label)
            label.pack(side=tk.LEFT, pady=((0, 5) if margin else (0, 0)))

        filename_last_sep = svg.filename.rfind(os.sep)
        if filename_last_sep == -1:
            add_line(svg.filename, font=font.Font(weight='bold'))
        else:
            add_line(svg.filename[:filename_last_sep + 1], font=font.Font(weight='bold'))
            add_line(svg.filename[filename_last_sep + 1:], font=font.Font(weight='bold'))
        add_line(f'End points: {len(svg.end_points)}')
        add_line(f'Internal points: {len(svg.int_points)}', margin=True)
        add_line(f'Commands: {svg.cmd_quans["all"]}')
        add_line(f'Moves: {svg.cmd_quans["move"]}')
        add_line(f'Lines: {svg.cmd_quans["line"]}')
        add_line(f'Cubic beziers: {svg.cmd_quans["cubic"]}')
        add_line(f'Quadratic beziers: {svg.cmd_quans["quadratic"]}')
        add_line(f'Arcs: {svg.cmd_quans["arc"]}')

        description_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        layer_frame.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(0, 10))
        layer_frame.tick = tick
        layer_frame.up_button = up_button
        layer_frame.down_button = down_button
        layer_frame.filename = svg.filename

    def toggle_layer_visibility(self, svg, set_eye_button_text):
        svg.visible = not svg.visible
        set_eye_button_text(svg.visible)

        if svg.visible:
            self.update_canvas_starting(svg)
        else:
            self.canvas.delete(svg.id)

    def toggle_layer_selection(self, svg, set_tick):
        if svg in self.selected_layers:
            set_tick(False)
            self.selected_layers.remove(svg)
        else:
            set_tick(True)
            self.selected_layers.add(svg)

    def _swap_layers(self, idx1, idx2):
        self.ordered_svgs[idx1], self.ordered_svgs[idx2] = self.ordered_svgs[idx2], self.ordered_svgs[idx1]

        self.update_canvas_starting(self.ordered_svgs[idx1], update_fst_png=False)
        self.update_layers_list()

    def move_layer_up(self, idx):
        if idx == 0:
            return

        self._swap_layers(idx - 1, idx)

    def move_layer_down(self, idx):
        if idx == len(self.ordered_svgs) - 1:
            return

        self._swap_layers(idx, idx + 1)

    def set_svg_color(self, svg):
        svg.color = colorchooser.askcolor()[0]
        self.update_canvas_starting(svg)

    def set_svg_opacity(self, svg, val, update_opacity_label):
        svg.opacity = val
        update_opacity_label(val)

        if self.canvas_opacity_timer_ids.get(svg.id) is not None:
            self.root.after_cancel(self.canvas_opacity_timer_ids[svg.id])

        self.canvas_opacity_timer_ids[svg.id] = self.root.after(
            SVG_OPACITY_DELAY,
            lambda: self.update_canvas_starting(svg)
        )

    def close_svg(self, svg, idx):
        self.svgs.pop(svg.filename)
        self.ordered_svgs.pop(idx)
        self.selected_layers.discard(svg)
        self.canvas.delete(f'{svg.id}')
        if svg.id in self.canvas.images:
            self.canvas.images.pop(svg.id)

        if idx < len(self.ordered_svgs):
            self.update_canvas_starting(self.ordered_svgs[idx])
        self.update_layers_list()

    def update_canvas(self):
        for svg in self.ordered_svgs:
            self.draw_svg(svg)
            self.draw_points(svg)

    def update_canvas_starting(self, fst_svg, update_fst_png=True):
        self.draw_svg(fst_svg, update_png=update_fst_png)
        self.draw_points(fst_svg)

        found_causing = False
        for svg in self.ordered_svgs:
            if not found_causing:
                if svg.id == fst_svg.id:
                    found_causing = True
                continue
            self.draw_svg(svg, update_png=False)
            self.draw_points(svg)

    def update_canvas_with_delay(self):
        for svg in self.ordered_svgs:
            self.canvas.delete(f'{svg.id}.frame')
            self._draw_frame(svg)

        if self.canvas_scroll_timer_id is not None:
            self.root.after_cancel(self.canvas_scroll_timer_id)

        self.canvas_scroll_timer_id = self.root.after(
            SVG_SCALE_DELAY,
            self.update_canvas
        )

    def update_layers_list(self):
        for layer in self.layers_list.winfo_children():
            layer.destroy()
        for svg in self.ordered_svgs:
            self.add_to_layers_list(svg)

    def draw_svg(self, svg, update_png=True):
        if not svg.visible:
            return

        self.canvas.delete(f'{svg.id}.image')

        if update_png:
            if svg.id in self.canvas.images:
                self.canvas.images.pop(svg.id)

            image = tk.PhotoImage(data=svg.get_png(self.scale))
            self.canvas.images[svg.id] = image  # Keeping a reference to the image to prevent garbage collection

        self.canvas.create_image(svg.lt_pos.x, svg.lt_pos.y, anchor=tk.NW, image=self.canvas.images[svg.id],
                                 tags=(f'{svg.id}.image', svg.id, 'image'))

    def _draw_frame(self, svg):
        frame_tags = (f'{svg.id}.frame', svg.id, 'frame')
        lt_x, lt_y = svg.lt_pos.x, svg.lt_pos.y
        rb_x, rb_y = lt_x + self.scale * svg.width, lt_y + self.scale * svg.height

        idx = self._svg_idx(svg.id)
        text = self.canvas.create_text(lt_x, rb_y, anchor=tk.NW, text=f'#{idx + 1}', font=font.Font(size=18),
                                       fill=rgb_to_hex(svg.color), tags=frame_tags)

        self.canvas.create_rectangle(lt_x, lt_y, rb_x, rb_y,
                                     outline=rgb_to_hex(svg.color), tags=frame_tags)

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
        self.scale += 1
        self.update_canvas_with_delay()

    def scale_down(self):
        if self.scale > 1:
            self.scale -= 1
            self.update_canvas_with_delay()

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


def rgb_to_hex(rgb):
    return '#{:02X}{:02X}{:02X}'.format(rgb[0], rgb[1], rgb[2])


if __name__ == '__main__':
    root = tk.Tk()
    root.title('SVG Comparator')
    root.geometry(f'{root.winfo_screenwidth() // 2}x{root.winfo_screenheight() // 2}')
    editor = SVGComparator(root)
    root.mainloop()
