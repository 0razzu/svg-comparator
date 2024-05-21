from io import BytesIO
from uuid import uuid4

import cairosvg
from PIL import Image, ImageEnhance
from svgpathtools import svg2paths, svg2paths2, CubicBezier, QuadraticBezier

from point import complex_to_point, Point


class Svg:
    def __init__(self, filename):
        self.filename = filename
        self.id = uuid4().hex
        self.int_points = []
        self.end_points = []
        self.cmd_quans = {'all': 0, 'move': 0, 'line': 0, 'cubic': 0, 'quadratic': 0, 'arc': 0}
        self.width = 0
        self.height = 0
        self.lt_pos = Point(0, 0)
        self.visible = True
        self.png = {'scale': -1, 'bytes': BytesIO()}
        self.opacity = .5
        self.color = (0, 0, 0)

        self._load_points_and_meta()

    def get_png(self, scale):
        if self.png['scale'] != scale:
            png_bytes = BytesIO()
            png_bytes.write(cairosvg.svg2png(file_obj=open(self.filename, 'rb'),
                                             output_width=scale * self.width,
                                             output_height=scale * self.height))
            self.png['scale'] = scale
            self.png['bytes'] = png_bytes

        self.png['bytes'].seek(0)
        png_bytes = BytesIO(self.png['bytes'].read())

        res_png_bytes = BytesIO()
        with Image.open(png_bytes) as png:
            png_data = png.getdata()
            new_png_data = []
            for pixel in png_data:
                if pixel[3] > 0:
                    new_png_data.append((*self.color, int(pixel[3] * self.opacity)))
                else:
                    new_png_data.append(pixel)
            png.putdata(new_png_data)

            png.save(res_png_bytes, format='PNG')

        return res_png_bytes.getvalue()

    def _load_points_and_meta(self):
        svg, code, meta = svg2paths2(self.filename)

        for path in svg:
            for segment in path:
                start = complex_to_point(segment.start)
                end = complex_to_point(segment.end)

                if len(self.end_points) == 0 or self.end_points[-1] != start:
                    self.end_points.append(start)
                self.end_points.append(end)

                if type(segment) is CubicBezier:
                    control1 = complex_to_point(segment.control1)
                    control1.whose = [start]
                    control2 = complex_to_point(segment.control2)
                    control2.whose = [end]

                    self.int_points.append(control1)
                    self.int_points.append(control2)

                elif type(segment) is QuadraticBezier:
                    control = complex_to_point(segment.control)
                    control.whose = [start, end]

                    self.int_points.append(control)

        for line in code:
            cmds = line.get('d')

            if cmds is None:
                continue

            for cmd in cmds.split():
                if len(cmd) > 1 and not cmd[1].isdigit():
                    continue

                cmd_cut = cmd.lower()[0]
                if cmd_cut == 'm':
                    self.cmd_quans['move'] += 1
                    self.cmd_quans['all'] += 1
                elif cmd_cut == 'l' or cmd_cut == 'v' or cmd_cut == 'h':
                    self.cmd_quans['line'] += 1
                    self.cmd_quans['all'] += 1
                elif cmd_cut == 'c':
                    self.cmd_quans['cubic'] += 1
                    self.cmd_quans['all'] += 1
                elif cmd_cut == 'q':
                    self.cmd_quans['quadratic'] += 1
                    self.cmd_quans['all'] += 1
                elif cmd_cut == 'a':
                    self.cmd_quans['arc'] += 1
                    self.cmd_quans['all'] += 1

        xlt, ylt, xrb, yrb = map(int, meta['viewBox'].split())
        self.width, self.height = xrb - xlt, yrb - ylt
