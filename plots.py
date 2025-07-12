import matplotlib.pyplot as plt
import numpy as np

class PlotContainer:
    def __init__(self, data: list | np.ndarray,
                    name="Plot",
                    color="blue",
                    line_style="-",
                    marker="o",
                    linewidth=2,
                    markersize=6,
                    alpha=1.0,
                    grid=True,
                    xlabel="Points",
                    ylabel="Value"
                 ):
        """ Initializes the plot container with data and an optional name. """
        self.y_data = np.array(data)
        self.name = name
        self.color = color
        self.line_style = line_style
        self.marker = marker
        self.linewidth = linewidth
        self.markersize = markersize
        self.alpha = alpha
        self.grid = grid
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.data = self.y_data

    def display_plot(self, plot_obj: plt, name):
        Y = self.y_data
        X = np.arange(len(Y))
        plot_obj.plot(X, Y,
                 color=self.color,
                 linestyle=self.line_style,
                 marker=self.marker,
                 linewidth=self.linewidth,
                 markersize=self.markersize,
                 alpha=self.alpha,
                 label=name)
        plot_obj.xlabel(self.xlabel)
        plot_obj.ylabel(self.ylabel)
        plot_obj.title(self.name)
        if self.grid:
            plt.grid(True)

class XyPlotContainer(PlotContainer):
    def __init__(self,
                 x_data: list | np.ndarray,
                 y_data: list | np.ndarray,
                 name="X-Y Plot",
                 color="blue",
                 line_style="-",
                 marker="o",
                 linewidth=2,
                 markersize=6,
                 alpha=1.0,
                 grid=True,
                 xlabel="X-axis",
                 ylabel="Y-axis",
                 ):
        """ Initializes the X-Y plot container with x and y data. """
        super().__init__(y_data, name, color, line_style, marker, linewidth, markersize, alpha, grid, xlabel, ylabel)
        self.x_data = np.array(x_data)

    def display_plot(self, plot_obj: plt, name):
        plot_obj.plot(self.x_data, self.y_data,
                 color=self.color,
                 linestyle=self.line_style,
                 marker=self.marker,
                 linewidth=self.linewidth,
                 markersize=self.markersize,
                 alpha=self.alpha,
                 label=name)
        plot_obj.xlabel(self.xlabel)
        plot_obj.ylabel(self.ylabel)
        plot_obj.title(self.name)
        if self.grid:
            plot_obj.grid(True)


