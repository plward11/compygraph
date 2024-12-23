# Compygraph

## Background

Compygraph is convenience wrapper around [graphkit](https://github.com/yahoo/graphkit/tree/master), which is a small and simple library for computational graphs. Compygraph provides a simple interface for defining nodes and adding operations to a computation graph. You can then run the computational graph, examine its outputs, and also view a rendering of the graph.

To see compygraph in action, run the examples in example.py.

This library is not thread safe. For a proper production use case of computational graphs with parallelization support, see [Dask](https://docs.dask.org/en/stable/).

## Setup

virtualenv is highly recommended. You can install virtualenv with pipx in an isolation Python environment or with pip in the gloval Python interpreter - see https://virtualenv.pypa.io/en/latest/installation.html for more information.

Steps to setting up compygraph:

1. Clone this repo and cd into it
1. Run `virtualenv venv`
1. Run `source venv/bin/activate`
1. Run `pip install requirements.txt`

## Tests

To run tests, run

`python3 -m unittest test/builder_test.py`

## Example

To run an example, you can run

`python3 example.py`

A few small examples will run, each of which will output graphs in the current directory.

For instance, this code snippet:

```
builder = Builder()  # Initialize the graph builder.
x = builder.init()  # Initialize an input node that must be defined by the client.
one = builder.constant(1)  # Initialize a constant node with a value of 1.
x_plus_one = builder.add(x, one)  # Create a simple addition operation: x + 1
builder.assert_equal(x_plus_one, 2)  # Assert that x + 1 = 2
builder.fill_nodes({x: 1})  # Define the x node as 1
builder.check_constraints()  # Check all constraints and assertions in the graph. Will check if x + 1 = 2, where x = 1

plot = builder.plot(filename="x_plus_one.png")  # Render the chart to "x_plus_one.png"
```

will create a simple graph and render it to an image named "x_plus_one.png". See the below example:

[img src="example_charts/x_plus_one.png"]()

To see saved example graphs, you can check out the example_graphs/ directory.