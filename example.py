from src.builder import Builder


import math


def x_plus_one():
    builder = Builder()
    x = builder.init(name="x")
    one = builder.constant(1)
    x_plus_one = builder.add(x, one, name="1 + 1", op_name="x + 1")

    builder.fill_nodes({x: 1})
    if not builder.check_constraints():
        print("Example x_plus_one is failing!")

    plot = builder.plot(filename="x_plus_one.png")


def x_squared_plus_five_plus_x():
    builder = Builder()
    x = builder.init(name="x")
    x_squared = builder.mul(x, x, name="2^2", op_name="x^2")
    x_squared_plus_five = builder.add(x_squared, 5, name="2^2 + 5", op_name="x^2 + 5")
    y = builder.add(x_squared_plus_five, x, name="y", op_name="x^2 + x + 5")

    builder.fill_nodes({x: 2, y: 11})
    if not builder.check_constraints():
        print("Example x_squared_plus_five_plus_x is failing!")

    plot = builder.plot(filename="x_squared_plus_five_plus_x.png")


def a_plus_one_divide_by_eight():
    def divide_by_eight(a):
        return a / 8

    builder = Builder()
    a = builder.init(name="a")
    b = builder.add(a, 1, name="2 + 1", op_name="a + 1")
    c = builder.hint(divide_by_eight, [b], name="(2 + 1) / 8", op_name="(a + 1) / 8")
    c_times_8 = builder.mul(c, 8, name="c * 8")
    builder.assert_equal(b, c_times_8, name="b = c * 8")

    builder.fill_nodes({a: 2})
    if not builder.check_constraints():
        print("Example a_plus_one_divide_by_eight is failing!")

    plot = builder.plot(filename="a_plus_one_divide_by_eight.png")


def sqrt_computation():
    def my_sqrt(a):
        return math.sqrt(a)

    builder = Builder()
    x = builder.init(name="x")
    x_plus_seven = builder.add(x, 7, name="2 + 7")

    sqrt_x_plus_7 = builder.hint(my_sqrt, [x_plus_seven], name="sqrt(x + 7)")
    computed_sq = builder.mul(sqrt_x_plus_7, sqrt_x_plus_7, name="sqrt(x + 7) * sqrt(x + 7)")
    builder.assert_equal(computed_sq, x_plus_seven)

    builder.fill_nodes({x: 2})
    if not builder.check_constraints():
        print("Example sqrt_computation is failing!")

    plot = builder.plot(filename="sqrt_computation.png")


def x_pow_y_plus_z_plus_seven():
    def my_pow_plus(a, b, c):
        return a**b + c

    builder = Builder()
    x = builder.init(name="x")
    y = builder.init(name="y")
    z = builder.init(name="z")
    x_pow_y_plus_z = builder.hint(my_pow_plus, [x, y, z], name="x^y + z")
    x_pow_y_plus_z_plus_seven = builder.add(x_pow_y_plus_z, 7, name="x^y + z + 7")
    builder.assert_equal(15, x_pow_y_plus_z, name="15 = x^y + z")
    builder.assert_equal(22, x_pow_y_plus_z_plus_seven, name="15 = x^y + z + 7")

    builder.fill_nodes({x: 2, y: 3, z: 7})
    if not builder.check_constraints():
        print("Example x_pow_y_plus_z_plus_seven is failing!")

    plot = builder.plot(filename="x_pow_y_plus_z_plus_seven.png")


if __name__ == "__main__":
    x_plus_one()
    x_squared_plus_five_plus_x()
    a_plus_one_divide_by_eight()
    sqrt_computation()
    x_pow_y_plus_z_plus_seven()
