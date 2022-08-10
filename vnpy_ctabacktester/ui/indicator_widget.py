import pandas as pd
import pyqtgraph as pg

from abc import abstractmethod
from typing import List, Dict, Tuple, Type

from vnpy.trader.ui import QtGui, QtWidgets, QtCore
from vnpy.chart import ChartWidget
from vnpy.chart.item import ChartItem
from vnpy.chart.manager import BarManager


class IndicatorItemMixin(object):

    def get_y_range(self, min_ix: int = None, max_ix: int = None) -> Tuple[float, float]:
        if not hasattr(self, "_y"):
            return 0, 1

        if not min_ix:
            min_ix: int = 0
            max_ix: int = len(self._y) - 1
        else:
            max_ix = min(max_ix, len(self._y) - 1)

        if hasattr(self, "_ranges") and (min_ix, max_ix) in self._ranges:
            return self._ranges[(min_ix, max_ix)]

        y_list = list(self._y[min_ix: max_ix + 1])
        max_y = y_list[0]
        min_y = y_list[0]

        for y in y_list[1:]:
            max_y = max(max_y, y)
            min_y = min(min_y, y)

        if not hasattr(self, "_ranges"):
            self._ranges = {(min_ix, max_ix): (min_y, max_y)}
        else:
            self._ranges[(min_ix, max_ix)] = (min_y, max_y)

        return min_y, max_y

    def get_info_text(self, ix: int) -> str:
        if hasattr(self, "_y"):
            if hasattr(self, "_name"):
                if ix >= len(self._y):
                    ix = -1
                return "{} {}".format(self._name, self._y[ix])
            else:
                return str(self._y[ix])
        else:
            return ""

    def update_history(self, *args, **kwargs):
        pass

    def update_bar(self, *args, **kwargs):
        pass

    def clear_all(self):
        pass

    def get_name(self):
        return self._name


class DataWrapper(object):

    def __init__(self):
        self.data = None

    def set(self, data: pd.DataFrame):
        self.data = data

    def get(self) -> pd.DataFrame:
        return self.data


class CurveItem(pg.PlotCurveItem, IndicatorItemMixin):

    def __init__(self, name: str, color, x_column: list, y_column: list):
        self._x = x_column
        self._y = y_column
        self._name = name
        pen: QtGui.QPen = pg.mkPen(color, width=1.5, style=QtCore.Qt.SolidLine)
        super(CurveItem, self).__init__(self._x, self._y, pen=pen)


class BarItem(pg.BarGraphItem, IndicatorItemMixin):

    def __init__(self, name: str, color: tuple, x_column: list, y_column: list):
        self._x = x_column
        self._y = y_column
        self._name = name
        if isinstance(color, tuple):
            self._colors = [color[0] if y >= 0 else color[1] for y in y_column]
            self._pens = [color[0] if y >= 0 else color[1] for y in y_column]
            super().__init__(x=self._x, height=self._y, width=0.05, brushes=self._colors, pens=self._pens)
        else:
            self._color = color
            self._pen = color
            super().__init__(x=self._x, height=self._y, width=0.05, brush=color, pen=color)


# y = [1, 2, 4, 3, 1, -3, -5, -2, 1, 2]
# x1 = [i for i in range(len(y)) if y[i] >= 0]
# x2 = [i for i in range(len(y)) if y[i] < 0]
# y1 = [d for d in y if d >=0]
# y2 = [d for d in y if d < 0]
# bg1 = pg.BarGraphItem(x=x1, height=y1, width=0.05, brush="g")
# bg2 = pg.BarGraphItem(x=x2, height=y2, width=0.05, brush="r")
# win.addItem(bg1)
# win.addItem(bg2)


class IndicatorWidget(ChartWidget):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._indicator_wrapper: DataWrapper = DataWrapper()

    def _init_ui(self) -> None:
        super()._init_ui()
        self.setWindowTitle("Indicator widget")

    def update_indicator(self, data: pd.DataFrame):
        self._indicator_wrapper.set(data)

    def add_item(
        self,
        item_class: type,
        item_name: str,
        plot_name: str,
        **kwargs
    ) -> None:
        if issubclass(item_class, ChartItem):
            super(IndicatorWidget, self).add_item(item_class, item_name, plot_name)
        elif issubclass(item_class, IndicatorItemMixin):
            item: IndicatorItemMixin = item_class(item_name, **kwargs)
            self._items[item_name] = item

            plot: pg.PlotItem = self._plots.get(plot_name)
            plot.addItem(item)

            self._item_plot_map[item] = plot
        else:
            pass

    def _update_plot_limits(self) -> None:
        range_map = dict()
        for item, plot in self._item_plot_map.items():
            min_value, max_value = item.get_y_range()
            if plot not in range_map:
                range_map[plot] = (min_value, max_value)
            else:
                buf = range_map[plot]
                range_map[plot] = (min(buf[0], min_value), max(buf[1], max_value))
            plot.setLimits(
                xMin=-1,
                xMax=self._manager.get_count(),
                yMin=range_map[plot][0],
                yMax=range_map[plot][1]
            )

    def _update_y_range(self) -> None:
        """
        Update the y-axis range of plots.
        """
        view: pg.ViewBox = self._first_plot.getViewBox()
        view_range: list = view.viewRange()

        min_ix: int = max(0, int(view_range[0][0]))
        max_ix: int = min(self._manager.get_count(), int(view_range[0][1]))

        # Update limit for y-axis
        range_map = dict()
        for item, plot in self._item_plot_map.items():
            y_range: tuple = item.get_y_range(min_ix, max_ix)
            left = y_range[0] * 1.1 if y_range[0] < 0 else y_range[0] * 0.9
            right = y_range[1] * 1.1 if y_range[1] > 0 else y_range[1] * 0.9
            if plot not in range_map:
                range_map[plot] = (left, right)
            else:
                buf = range_map[plot]
                range_map[plot] = (min(buf[0], left), max(buf[1], right))

            plot.setRange(yRange=range_map[plot])

    def clear_all(self) -> None:
        removed_items = []
        for item, plot in self._item_plot_map.items():
            if isinstance(item, IndicatorItemMixin):
                plot.removeItem(item)
                removed_items.append(item)
        for item in removed_items:
            self._item_plot_map.pop(item)
            self._items.pop(item.get_name())
        super(IndicatorWidget, self).clear_all()
