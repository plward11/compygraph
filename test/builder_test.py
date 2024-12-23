from src.builder import Builder, InvalidNodeArgument, UnsupportedPlotFileExtension

import contextlib
import io
import math
import unittest


class TestBuilder(unittest.TestCase):

    def test_empty_graph(self):
        builder = Builder()
        f = io.StringIO()
        with contextlib.redirect_stderr(f):
            self.assertFalse(builder.check_constraints())
            self.assertEqual(
                "No operations in graph. Cannot run graph without any operations defined.",
                f.getvalue().rstrip(),
            )
            self.assertIsNone(builder.get_graph_results())

            plot = builder.plot()

            self.assertEqual(len(plot.get_nodes()), 0)
            self.assertEqual(len(plot.get_edges()), 0)

    def test_no_operations(self):
        builder = Builder()
        x = builder.init()
        builder.fill_nodes({x: 1})

        f = io.StringIO()
        with contextlib.redirect_stderr(f):
            self.assertFalse(builder.check_constraints())
            self.assertEqual(
                "No operations in graph. Cannot run graph without any operations defined.",
                f.getvalue().rstrip(),
            )
            self.assertIsNone(builder.get_graph_results())

            plot = builder.plot()

            self.assertEqual(len(plot.get_nodes()), 0)
            self.assertEqual(len(plot.get_edges()), 0)

    def test_undefined_node(self):
        builder = Builder()
        x = builder.init(name="x")
        one = builder.constant(1)
        x_plus_one = builder.add(x, one)
        builder.fill_nodes({})

        f = io.StringIO()
        with contextlib.redirect_stderr(f):
            self.assertFalse(builder.check_constraints())
            self.assertEqual(
                "Node x is undefined. Must define node in order to check constraints.",
                f.getvalue().rstrip(),
            )

    def test_failed_constraint(self):
        builder = Builder()
        x = builder.init(name="x")
        one = builder.constant(1)
        x_plus_one = builder.add(x, one, name="x + 1")
        builder.fill_nodes({x: 1, x_plus_one: 3})

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.assertFalse(builder.check_constraints())
            self.assertEqual(
                "Node x + 1 = 3 has an expected value of 3, but this does not match the calculated value of 2",
                f.getvalue().rstrip(),
            )

    def test_failed_assertion(self):
        builder = Builder()
        x = builder.init(name="x")
        one = builder.constant(1)
        x_plus_one = builder.add(x, one, name="x + 1")
        builder.assert_equal(x_plus_one, 3, "assert 1 + 1 = 3")
        builder.fill_nodes({x: 1})

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.assertFalse(builder.check_constraints())
            self.assertEqual(
                "Node assert 1 + 1 = 3 has failed assertion that node x + 1 and node 3 are equal.",
                f.getvalue().rstrip(),
            )

    def test_filling_value_on_node_not_in_graph(self):
        builder_a = Builder()
        x = builder_a.init(name="x")
        one = builder_a.constant(1)
        x_plus_one = builder_a.add(x, one, name="x + 1")

        builder_b = Builder()
        y = builder_b.init(name="y")

        f = io.StringIO()
        with contextlib.redirect_stderr(f):
            self.assertFalse(builder_a.fill_nodes({x: 1, y: 2}))
            self.assertEqual(
                "Node y isn't in graph. Cannot set its value.", f.getvalue().rstrip()
            )

    def test_error_when_mixing_nodes_between_different_graphs(self):
        builder_a = Builder()
        x = builder_a.init(name="x")
        one = builder_a.constant(1)
        x_plus_one = builder_a.add(x, one)

        builder_b = Builder()
        two = builder_b.constant(2)

        with self.assertRaises(InvalidNodeArgument) as error:
            x_plus_two = builder_b.add(x, two, op_name="x + 2")

        self.assertEqual(
            "Node x isn't in graph. Unable to add the x + 2 operation.",
            str(error.exception),
        )

    def test_unsupported_file_extension_exception(self):
        builder = Builder()
        x = builder.init()
        one = builder.constant(1)
        x_plus_one = builder.add(x, one)
        builder.fill_nodes({x: 1})

        with self.assertRaises(UnsupportedPlotFileExtension) as error:
            builder.plot(filename="my_chart.foo")

        self.assertEqual(
            "Unknown file format for saving graph: .foo", str(error.exception)
        )

    def test_simple_graph(self):
        builder = Builder()
        x = builder.init()
        one = builder.constant(1)
        x_plus_one = builder.add(x, one)
        builder.fill_nodes({x: 1})
        self.assertTrue(builder.check_constraints())
        self.assertEqual(builder.get_graph_results()[x.id], 1)
        self.assertEqual(builder.get_graph_results()[x_plus_one.id], 2)

        plot = builder.plot()

        self.assertEqual(len(plot.get_nodes()), 4)
        self.assertEqual(len(plot.get_edges()), 3)

    def test_node_mul_node_with_automatic_constant_node_creation(self):
        builder = Builder()
        x = builder.init()
        x_squared = builder.mul(x, x)
        x_squared_plus_five = builder.add(x_squared, 5)
        y = builder.add(x_squared_plus_five, x)
        builder.fill_nodes({x: 2, y: 11})
        self.assertTrue(builder.check_constraints())
        self.assertEqual(builder.get_graph_results()[x.id], 2)
        self.assertEqual(builder.get_graph_results()[y.id], 11)

        plot = builder.plot()

        self.assertEqual(len(plot.get_nodes()), 8)
        self.assertEqual(len(plot.get_edges()), 8)

    def test_node_with_hint(self):
        def divide_by_eight(a):
            return a / 8

        builder = Builder()
        a = builder.init()
        b = builder.add(a, 1)
        c = builder.hint(divide_by_eight, [b])
        c_times_8 = builder.mul(c, 8)
        builder.assert_equal(b, c_times_8)

        builder.fill_nodes({a: 2})
        self.assertTrue(builder.check_constraints())
        self.assertEqual(builder.get_graph_results()[a.id], 2)
        self.assertEqual(builder.get_graph_results()[c.id], 0.375)
        self.assertEqual(builder.get_graph_results()[c_times_8.id], 3)

        plot = builder.plot()

        self.assertEqual(len(plot.get_nodes()), 11)
        self.assertEqual(len(plot.get_edges()), 11)

    def test_node_with_irrational_hint_computation(self):
        def my_sqrt(a):
            return math.sqrt(a)

        builder = Builder()
        x = builder.init()
        x_plus_seven = builder.add(x, 7)

        sqrt_x_plus_7 = builder.hint(my_sqrt, [x_plus_seven])
        computed_sq = builder.mul(sqrt_x_plus_7, sqrt_x_plus_7)
        builder.assert_equal(computed_sq, x_plus_seven)

        builder.fill_nodes({x: 2})
        self.assertTrue(builder.check_constraints())
        self.assertEqual(builder.get_graph_results()[sqrt_x_plus_7.id], 3)
        self.assertEqual(builder.get_graph_results()[computed_sq.id], 9)

        plot = builder.plot()

        self.assertEqual(len(plot.get_nodes()), 10)
        self.assertEqual(len(plot.get_edges()), 10)

    def test_node_with_hint_with_multiple_input_nodes(self):
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
        self.assertTrue(builder.check_constraints())
        self.assertEqual(builder.get_graph_results()[x_pow_y_plus_z.id], 15)
        self.assertEqual(builder.get_graph_results()[x_pow_y_plus_z_plus_seven.id], 22)

        plot = builder.plot()

        self.assertEqual(len(plot.get_nodes()), 14)
        self.assertEqual(len(plot.get_edges()), 13)

    def test_node_with_floats(self):
        def my_pow(a, b):
            return a**b

        builder = Builder()
        x = builder.init(name="x")
        y = builder.init(name="y")
        x_pow_y = builder.hint(my_pow, [x, y], name="x^y")
        x_pow_y_plus_one = builder.add(x_pow_y, 1, name="x^y + 1")
        builder.assert_equal(0.25, x_pow_y, name="0.25 = x^y")
        builder.assert_equal(1.25, x_pow_y_plus_one, name="1.25 = x^y + 1")

        builder.fill_nodes({x: 0.5, y: 2})
        self.assertTrue(builder.check_constraints())
        self.assertEqual(builder.get_graph_results()[x_pow_y.id], 0.25)
        self.assertEqual(builder.get_graph_results()[x_pow_y_plus_one.id], 1.25)

        plot = builder.plot()

        self.assertEqual(len(plot.get_nodes()), 13)
        self.assertEqual(len(plot.get_edges()), 12)


if __name__ == "__main__":
    unittest.main()
