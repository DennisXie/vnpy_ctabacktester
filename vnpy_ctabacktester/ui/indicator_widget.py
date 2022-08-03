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
            if hasattr(self, "name"):
                return "{} {}".format(self.name, self._y[ix])
            else:
                return str(self._y[ix])
        else:
            return ""

    def update_history(self, *args, **kwargs):
        pass

    def update_bar(self, *args, **kwargs):
        pass


class DataWrapper(object):

    def __init__(self):
        self.data = None

    def set(self, data: pd.DataFrame):
        self.data = data

    def get(self) -> pd.DataFrame:
        return self.data


class CurveItem(pg.PlotCurveItem, IndicatorItemMixin):

    def __init__(self, name: str, data: pd.DataFrame, color, x_column: str, y_column: str):
        self._x = list(data[x_column])
        self._y = list(data[y_column])
        self.name = name
        pen: QtGui.QPen = pg.mkPen(color, width=1.5, style=QtCore.Qt.SolidLine)
        super(CurveItem, self).__init__(self._x, self._y, pen=pen)


class IndicatorWidget(ChartWidget):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._indicator_wrapper: DataWrapper = DataWrapper()

    def _init_ui(self) -> None:
        super()._init_ui()
        self.setWindowTitle("Indicator widget")

    def update_indicator(self, data: pd.DataFrame):
        self._indicator_wrapper.set(DataWrapper)

    def add_item(
        self,
        item_class: Type[ChartItem, IndicatorItemMixin],
        item_name: str,
        plot_name: str,
        **kwargs
    ) -> None:
        if issubclass(item_class, ChartItem):
            super(IndicatorWidget, self).add_item(item_class, item_name, plot_name)
        elif issubclass(item_class, IndicatorItemMixin):
            item: IndicatorItemMixin = item_class(item_name, self._indicator_wrapper.get(), **kwargs)
            self._items[item_name] = item

            plot: pg.PlotItem = self._plots.get(plot_name)
            plot.addItem(item)

            self._item_plot_map[item] = plot
        else:
            pass
