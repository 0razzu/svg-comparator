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


def complex_to_point(complex_point):
    return Point(complex_point.real, complex_point.imag)
