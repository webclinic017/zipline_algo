import empyrical
import matplotlib
from matplotlib import gridspec
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import AutoLocator, LogLocator, Formatter, PercentFormatter
import numpy as np
from utils.views.group_config_box import GroupConfigBoxWidget
from matplotlib.ticker import FixedLocator
import pandas as pd
from PyQt5 import QtWidgets, QtCore

drawdown_source_strategy_returns = 'Strategy Drawdown'
drawdown_source_benchmark_returns = 'Benchmark Drawdown'
strategy_long_plot_color = '#0288D1'
benchmark_plot_color = 'gray'


class DrawdownTab:
    resized = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.resized.connect(self.resizeFunction)

        self.plotter = Plotter(self)
        self.scrollArea = QtWidgets.QScrollArea(self)

        # self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)

        firstgroup_widget = QtWidgets.QWidget()
        firstgroup_layout = QtWidgets.QVBoxLayout(firstgroup_widget)
        self.firstgroup_gbox = GroupConfigBoxWidget(self.get_tab_name() + ' (' + self.plotter.drawdown_source + ')',
                                                    firstgroup_widget)
        firstgroup_vbox = QtWidgets.QVBoxLayout()

        firstgroup_vbox.addWidget(self.plotter)
        firstgroup_vbox.setSpacing(0)
        self.firstgroup_gbox.setLayout(firstgroup_vbox)
        firstgroup_layout.setContentsMargins(0, 0, 0, 0)
        firstgroup_layout.addWidget(self.firstgroup_gbox)

        secondgroup_widget = QtWidgets.QWidget()
        secondgroup_layout = QtWidgets.QVBoxLayout(secondgroup_widget)
        self.secondgroup_gbox = GroupConfigBoxWidget('Worst ' + self.plotter.drawdown_source + 's', secondgroup_widget,
                                                     False)
        secondgroup_vbox = QtWidgets.QVBoxLayout()

        self.distributionTable = DistributionTable()
        secondgroup_vbox.addWidget(self.distributionTable)
        secondgroup_vbox.setSpacing(0)
        self.secondgroup_gbox.setLayout(secondgroup_vbox)

        secondgroup_layout.setContentsMargins(0, 0, 0, 0)
        secondgroup_layout.addWidget(self.secondgroup_gbox)

        grid.addWidget(firstgroup_widget, 0, 0)
        grid.addWidget(secondgroup_widget, 1, 0)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        outer_layout.addWidget(self.scrollArea)

        self.setLayout(outer_layout)

        # prepare menus
        self.main_menu = QtWidgets.QMenu(self.get_tab_name(), self)

        self.drawdown_source_menu = QtWidgets.QMenu('Metric', self)
        self.drawdown_source_menu.addAction(drawdown_source_benchmark_returns,
                                            lambda: self.change_drawdown_source(drawdown_source_benchmark_returns))
        self.drawdown_source_menu.addAction(drawdown_source_strategy_returns,
                                            lambda: self.change_drawdown_source(drawdown_source_strategy_returns))
        self.main_menu.addMenu(self.drawdown_source_menu)

        self.threshold_menu = QtWidgets.QMenu('Threshold', self)
        self.threshold_menu.addAction('-5%', lambda: self.change_threshold(5))
        self.threshold_menu.addAction('-7%', lambda: self.change_threshold(7))
        self.threshold_menu.addAction('-10%', lambda: self.change_threshold(10))
        self.threshold_menu.addAction('-15%', lambda: self.change_threshold(15))
        self.threshold_menu.addAction('-20%', lambda: self.change_threshold(20))
        self.threshold_menu.addAction('-25%', lambda: self.change_threshold(25))
        self.main_menu.addMenu(self.threshold_menu)

        self.firstgroup_gbox.button.setMenu(self.main_menu)

        # Checkmark for default selections
        for item in self.threshold_menu.actions():
            if abs(int(item.text().replace('%', ''))) == self.plotter.min_drawdown:
                item.setCheckable(True)
                item.setChecked(True)
        for item in self.drawdown_source_menu.actions():
            if item.text() == self.plotter.drawdown_source:
                item.setCheckable(True)
                item.setChecked(True)

    def get_tab_name(self):
        return 'Drawdown'

    def get_tab_menu(self):
        return self.main_menu

    def get_tab_description(self):
        return 'Analyze drawdown periods.'

    def update_plot(self, analysis_data):
        self.plotter.plot(analysis_data)

    def change_threshold(self, min_drawdown):
        if min_drawdown != self.plotter.min_drawdown:
            for item in self.threshold_menu.actions():
                if abs(int(item.text().replace('%', ''))) == min_drawdown:
                    item.setCheckable(True)
                    item.setChecked(True)
                if abs(int(item.text().replace('%', ''))) == self.plotter.min_drawdown:
                    item.setChecked(False)
            self.plotter.min_drawdown = min_drawdown
            self.plotter.plot()

    def change_num_drawdowns(self, num_drawdown):
        if num_drawdown != self.plotter.num_drawdowns:
            for item in self.num_drawdowns_menu.actions():
                if int(item.text()) == num_drawdown:
                    item.setCheckable(True)
                    item.setChecked(True)
                if int(item.text()) == self.plotter.num_drawdowns:
                    item.setChecked(False)
            self.plotter.num_drawdowns = num_drawdown
            self.plotter.plot()

    def change_drawdown_source(self, drawdown_source):
        if drawdown_source != self.plotter.drawdown_source:
            for item in self.drawdown_source_menu.actions():
                if item.text() == drawdown_source:
                    item.setCheckable(True)
                    item.setChecked(True)
                if item.text() == self.plotter.drawdown_source:
                    item.setChecked(False)
            self.plotter.drawdown_source = drawdown_source
            self.plotter.plot()
            self.firstgroup_gbox.setTitleAndMoveButton(drawdown_source)
            self.secondgroup_gbox.setTitle('Worst ' + drawdown_source + 's')

    def resizeEvent(self, event):
        self.resized.emit()
        return super(DrawdownTab, self).resizeEvent(event)

    def resizeFunction(self):
        self.scrollAreaWidgetContents.setFixedWidth(self.scrollArea.size().width())


class DrawdownSubPlotter:
    def __init__(self):
        self.subplot_legend = None
        self.ax_legend = {}

    def plot(self, ax, chart_data, benchmark_symbol, set_fixedlocator=True):
        ax.set_ylabel('Drawdown', fontsize=8)
        self.ax_legend['Strategy'] = {'field': 'drawdown', 'pos': 0, 'format': '{:.2f}%'}
        self.ax_legend[benchmark_symbol] = {'field': 'benchmark_drawdown', 'pos': 1, 'format': '{:.2f}%'}
        ax.yaxis.tick_right()

        xdata = np.arange(len(chart_data.index))

        self.plotdata = pd.concat([(100 * chart_data.drawdown), (100 * chart_data.benchmark_drawdown)], axis=1)

        ax.plot(xdata, self.plotdata.drawdown, color=strategy_long_plot_color)
        ax.fill_between(xdata, self.plotdata.drawdown, 0, facecolor=strategy_long_plot_color, alpha='0.05')

        ax.plot(xdata, self.plotdata.benchmark_drawdown, color=benchmark_plot_color, linewidth=0.5)

        min_drawdown = min(self.plotdata.drawdown.min(), self.plotdata.benchmark_drawdown.min())
        # set tick labels
        if set_fixedlocator:
            ax.get_yaxis().set_major_locator(FixedLocator([min_drawdown, 0], nbins=3))
        # ax.set_ybound(self.plotdata.drawdown.min(), 0)
        ax.set_ylim(min_drawdown, 1)

        ax.get_yaxis().set_major_formatter(PercentFormatter(decimals=2))

        self.subplot_legend = ax.legend(sorted(self.ax_legend, key=lambda x: self.ax_legend[x]['pos']),
                                        loc='upper left', fontsize=6)
        ax.grid(True)


class Plotter(FigureCanvas):
    min_drawdown = 5
    num_drawdowns = 10
    drawdown_source = drawdown_source_strategy_returns
    y_scale = 'linear'

    def __init__(self, masterWindow):
        self.fig = Figure(figsize=(10, 4))
        gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], left=0.03, bottom=0.06, right=0.93, top=0.955, wspace=0,
                               hspace=0.05)

        # Equity curve
        self.returns_ax = self.fig.add_subplot(gs[0, 0:], xticks=[], yticks=[])
        self.returns_ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
        self.subplot_ax = self.fig.add_subplot(gs[1, 0:], sharex=self.returns_ax, yticks=[], xticks=[])

        FigureCanvas.__init__(self, self.fig)
        self.setParent(masterWindow)
        self.parent = masterWindow

        # connect to events
        self.cidpress = self.fig.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.fig.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidrelease = self.fig.canvas.mpl_connect(
            'figure_leave_event', self.on_leave)
        self.cidmotion = self.fig.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.vertical_line = None
        self.horizontal_line = None

        # color map to adjust colors
        self.drawdown_colormap = matplotlib.cm.get_cmap('YlOrRd')

        # set the default subplotters
        self.subplot_plotter = DrawdownSubPlotter()

        # annotate to display returns
        self.an1 = None
        self.analysis_data = None
        self.vertical_margin_pct = 0.70
        self.horizontal_margin_pct = 0.20
        self.formatter = None
        self.analysis_data = None

    def on_leave(self, event):
        self.on_release(event)

    def on_press(self, event):
        # return if no data
        if self.analysis_data is None or self.analysis_data.chart_data is None:
            return

        'on button press we will see if the mouse is over us'
        if event.inaxes != self.returns_ax:
            return

        # get the date from x-Axes
        curr_date = self.formatter(event.xdata)

        # create cross hair line
        self.horizontal_line = self.returns_ax.axhline(event.ydata, linestyle='--', linewidth=1, color='grey')
        self.vertical_line = self.returns_ax.axvline(event.xdata, linestyle='--', linewidth=1, color='grey')
        returns_data = self.get_returns_data(curr_date)
        self.subplot_plotter.set_vertical_line(self.subplot_ax, event.xdata)

        # create annotate to display returns
        if returns_data != "":
            self.an1 = self.returns_ax.annotate(returns_data[0],
                                                xy=(event.x, self.returns_ax.bbox.ymax), xycoords='figure pixels',
                                                xytext=(-32, 10), textcoords='offset points',
                                                ha="left", va="top", fontsize=8,
                                                bbox=dict(boxstyle="round", fc="white", color='grey')
                                                )

        # draw everything but the annotate and store the pixel buffer
        canvas = self.an1.figure.canvas
        self.update_legends(curr_date, returns_data)
        subplot1_legend_axes = self.subplot_plotter.subplot_legend.axes

        self.an1.set_animated(True)
        self.horizontal_line.set_animated(True)
        self.subplot_plotter.animated_vertical_line()
        self.vertical_line.set_animated(True)
        self.subplot_plotter.subplot_legend.set_animated(True)
        self.legend.set_animated(True)

        canvas.draw()
        self.an1_background = canvas.copy_from_bbox(self.fig.bbox)
        self.subplot1_legend_bg = canvas.copy_from_bbox(self.subplot_plotter.subplot_legend.get_bbox_to_anchor())
        self.legend_bg = canvas.copy_from_bbox(self.legend.get_bbox_to_anchor())

        # now redraw just the annotate
        self.fig.draw_artist(self.an1)
        self.fig.draw_artist(self.horizontal_line)
        self.fig.draw_artist(self.vertical_line)
        self.fig.draw_artist(self.legend)
        self.subplot_plotter.draw_vertical_line(self.fig)
        subplot1_legend_axes.draw_artist(self.subplot_plotter.subplot_legend)

        # and blit just the redrawn area
        canvas.blit(self.fig.bbox)
        canvas.blit(subplot1_legend_axes.bbox)

    def update_legends(self, curr_date, returns_data):
        strategy_legend_text = '{:<10} {:>4}'.format("Strategy", returns_data[1])
        self.legend.texts[0].set_text(strategy_legend_text)

        benchmark_legend_text = '{:<10} {:>4}'.format(self.analysis_data.info_data['benchmark_symbol'], returns_data[2])
        self.legend.texts[1].set_text(benchmark_legend_text)

        # update subplotter legend
        self.subplot_plotter.update_legend(curr_date)

    def get_current_data(self, curr_date, field):
        try:
            loc = self.analysis_data.chart_data.index.get_loc(curr_date, method='pad')
            rec = self.analysis_data.chart_data.iloc[loc]

            return rec[field]

        except KeyError:
            return None

    def on_motion(self, event):
        # return if annotate is not available
        if self.an1 is None:
            return

        'on button press we will see if the mouse is over us'
        if event.inaxes != self.returns_ax:
            return

        try:
            curr_date = self.formatter(event.xdata)
        except Exception as e:
            return

        returns_data = self.get_returns_data(curr_date)
        legend_text = '{:<10} {:>4}'.format("Strategy", returns_data[1])
        self.legend.texts[0].set_text(legend_text)
        self.an1.set_text(returns_data[0])
        self.horizontal_line.set_ydata(event.ydata)
        self.subplot_plotter.update_vertical_line(event.xdata)
        self.vertical_line.set_xdata(event.xdata)
        self.an1.xy = (event.x, self.returns_ax.bbox.ymax)
        self.an1._y = 10
        self.an1._x = -32
        self.update_legends(curr_date, returns_data)

        canvas = self.an1.figure.canvas
        subplot1_legend_axes = self.subplot_plotter.subplot_legend.axes

        # restore the background region
        canvas.restore_region(self.an1_background)
        canvas.restore_region(self.subplot1_legend_bg)
        canvas.restore_region(self.legend_bg)

        # redraw just the annotate
        self.fig.draw_artist(self.an1)
        self.fig.draw_artist(self.horizontal_line)
        self.fig.draw_artist(self.vertical_line)
        self.fig.draw_artist(self.legend)
        self.subplot_plotter.draw_vertical_line(self.fig)
        subplot1_legend_axes.draw_artist(self.subplot_plotter.subplot_legend)

        # blit just the redrawn area
        canvas.blit(self.fig.bbox)
        canvas.blit(subplot1_legend_axes.bbox)

    def on_release(self, event):
        # return if annotate is not available
        if self.an1 is None:
            return

        # on button press we will see if the mouse is over us
        # if event.inaxes != self.returns_ax:
        #    return

        canvas = self.an1.figure.canvas
        if self.horizontal_line in self.returns_ax.lines:
            self.returns_ax.lines.remove(self.horizontal_line)
        self.horizontal_line = None

        if self.vertical_line in self.returns_ax.lines:
            self.returns_ax.lines.remove(self.vertical_line)
        self.vertical_line = None

        if self.an1 in self.returns_ax.texts:
            self.returns_ax.texts.remove(self.an1)
        self.an1 = None

        self.subplot_plotter.reset_vertical_line(self.subplot_ax)

        self.subplot_ax.legend(sorted(self.subplot_plotter.ax_legend,
                                      key=lambda x: self.subplot_plotter.ax_legend[x]['pos']),
                               loc='upper left', fontsize=6)
        self.returns_ax.legend(['Strategy', self.analysis_data.info_data['benchmark_symbol']],
                               loc='upper left', fontsize=8)

        canvas.draw()

    def get_returns_data(self, curr_date):
        try:
            loc = self.portfolio_total_returns.index.get_loc(curr_date)
            date = self.portfolio_total_returns.index[loc].strftime("%a, %b %d, %Y")
            strategy_return = '{:.2f}%'.format(self.portfolio_total_returns.iloc[loc])
            benchmark_return = '{:.2f}%'.format(self.benchmark_total_returns.iloc[loc])

            return date, strategy_return, benchmark_return

        except KeyError:
            return "", "", ""

    def plot(self, analysis_data=None):
        if analysis_data is not None:
            self.analysis_data = analysis_data

        if self.analysis_data is None or self.analysis_data.chart_data is None:
            return

        self.an1 = None

        self.returns_ax.cla()
        self.subplot_ax.cla()

        # convert dates to numbers
        dates_num = mdates.date2num(self.analysis_data.chart_data.index)
        self.formatter = DateFormatter(dates_num)
        self.returns_ax.get_xaxis().set_major_formatter(self.formatter)
        self.subplot_ax.get_xaxis().set_major_formatter(self.formatter)

        self.portfolio_total_returns = empyrical.cum_returns(self.analysis_data.chart_data.returns) * 100
        self.benchmark_total_returns = empyrical.cum_returns(self.analysis_data.chart_data.benchmark_returns) * 100

        self.returns_ax.plot(np.arange(len(dates_num)),
                             self.portfolio_total_returns, color=strategy_long_plot_color)
        self.returns_ax.plot(np.arange(len(dates_num)),
                             self.benchmark_total_returns, color=benchmark_plot_color, linewidth=0.5)

        self.legend = self.returns_ax.legend(['Strategy', self.analysis_data.info_data['benchmark_symbol']],
                                             loc='upper left', fontsize=8)
        self.returns_ax.yaxis.tick_right()
        self.returns_ax.set_yscale(self.y_scale)
        if self.y_scale == 'log' or self.y_scale == 'semilog' or self.y_scale == 'logarithmic':
            self.returns_ax.get_yaxis().set_major_locator(LogLocator())
        else:
            self.returns_ax.get_yaxis().set_major_locator(AutoLocator())

        # if plot_style_fill:
        #     self.returns_ax.fill_between(np.arange(len(dates_num)), 0, self.portfolio_total_returns,
        #                                  facecolor=strategy_long_plot_color, alpha='0.05')
        self.returns_ax.grid(True)
        self.returns_ax.set_ylabel('Return', fontsize=10)
        self.returns_ax.get_yaxis().set_major_formatter(PercentFormatter(decimals=0))

        self.returns_ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)

        # plot the sub plots
        self.subplot_plotter.plot(self.subplot_ax, self.analysis_data.chart_data,
                                  self.analysis_data.info_data['benchmark_symbol'], set_fixedlocator=False)

        dd_df = gen_drawdown_table(self.analysis_data.chart_data.returns,
                                   self.analysis_data.chart_data.benchmark_returns,
                                   self.drawdown_source, top=self.num_drawdowns, min_drawdown=self.min_drawdown)
        # alphas = np.linspace(0.5, 0.1, dd_df['Peak date'].dropna().shape[0])

        norm = matplotlib.colors.Normalize(vmin=0, vmax=self.num_drawdowns)

        for dd_index, dd_row in dd_df.iterrows():
            if dd_row['Strategy Drawdown'] == 0:
                break

            start_date = dd_row['Peak date']
            if start_date is pd.NaT:
                break

            recovery_date = dd_row['Recovery date']
            if recovery_date is pd.NaT:
                recovery_date = self.analysis_data.chart_data.index.max()

            start_date_index = np.where(dates_num == mdates.date2num(start_date))
            recovery_date_index = np.where(dates_num == mdates.date2num(recovery_date))

            dd_color = self.drawdown_colormap(norm(self.num_drawdowns - dd_index))
            # self.returns_ax.axvspan(start_date_index[0], recovery_date_index[0],
            #                                                   color=drawdown_fill_color, alpha=alphas[dd_index])
            self.returns_ax.axvspan(start_date_index[0], recovery_date_index[0], color=dd_color, alpha=0.3)

        # update drawdowns table
        self.parent.distributionTable.update_data(dd_df)

        self.draw()

    def open_subplot(self, subplotter, n):
        self.subplot_plotter[n] = subplotter
        self.plot()

    def toggle_plot_scale(self):
        if self.y_scale == 'linear':
            self.y_scale = 'symlog'
        elif self.y_scale == 'symlog' or self.y_scale == 'log' or self.y_scale == 'logarithmic':
            self.y_scale = 'linear'
        else:
            self.y_scale = 'linear'
        self.plot()


class DateFormatter(Formatter):
    def __init__(self, dates, fmt='%Y-%m-%d'):
        self.dates = dates
        self.fmt = fmt

    def __call__(self, x, pos=0):
        """Return the label for time x at position pos"""
        ind = int(np.round(x))
        if ind >= len(self.dates) or ind < 0:
            return ''

        return mdates.num2date(self.dates[ind]).strftime(self.fmt)


class DistributionTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(QtWidgets.QTableWidget, self).__init__()
        self.column_headers = ['Strategy Drawdown', 'Benchmark Drawdown', 'Peak Date', 'Valley Date', 'Recovery Date',
                               'Duration', 'Correlation', 'Strategy Std Dev', 'Benchmark Std Dev']
        self.setSortingEnabled(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setRowCount(5)
        self.setColumnCount(len(self.column_headers))

        # set horizontal header
        for col in range(0, len(self.column_headers)):
            self.setHorizontalHeaderItem(col, QtWidgets.QTableWidgetItem(self.column_headers[col]))
            self.setColumnWidth(col, 190)

        # QtWidgets.QHeaderView
        # header = self.horizontalHeader()
        # header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

    def update_data(self, drawdown_df):
        drawdown_df['Strategy Drawdown'] = pd.to_numeric(drawdown_df['Strategy Drawdown'], errors='ignore')
        drawdown_df['Benchmark Drawdown'] = pd.to_numeric(drawdown_df['Benchmark Drawdown'], errors='ignore')

        max_row_count = 5
        row_count = min(drawdown_df['Strategy Drawdown'].count(), max_row_count)
        if max_row_count == 5:
            drawdown_df = drawdown_df.nlargest(max_row_count, 'Strategy Drawdown')
        else:
            drawdown_df = drawdown_df.sort('Strategy Drawdown')

        # Restricting drawdown values to 4 decimals
        pct_fmt = "{:.4f}%"
        fmt = "{:.4f}"
        # Converting empty Recovery dates to empty strings to avoid NaT errors
        drawdown_df['Recovery date'] = [d.strftime('%Y-%m-%d')
                                        if not pd.isnull(d) else '' for d in drawdown_df['Recovery date']]
        self.clearContents()
        for row_id, drawdown in zip(range(0, row_count), drawdown_df.iterrows()):
            self.setItem(row_id, 0, QtWidgets.QTableWidgetItem(pct_fmt.format(drawdown[1]['Strategy Drawdown'])))
            self.setItem(row_id, 1, QtWidgets.QTableWidgetItem(pct_fmt.format(drawdown[1]['Benchmark Drawdown'])))
            self.setItem(row_id, 2, QtWidgets.QTableWidgetItem(drawdown[1]['Peak date'].strftime('%Y-%m-%d')))
            self.setItem(row_id, 3, QtWidgets.QTableWidgetItem(drawdown[1]['Valley date'].strftime('%Y-%m-%d')))
            self.setItem(row_id, 4, QtWidgets.QTableWidgetItem(drawdown[1]['Recovery date']))
            self.setItem(row_id, 5, QtWidgets.QTableWidgetItem(str(drawdown[1]['Duration'])) if not np.isnan(
                drawdown[1]['Duration']) else '')

            correlation = fmt.format(drawdown[1]['Correlation']) if drawdown[1]['Correlation'] != '' else ''
            self.setItem(row_id, 6, QtWidgets.QTableWidgetItem(correlation))
            strategy_std = fmt.format(drawdown[1]['Strategy Std Dev']) if drawdown[1]['Strategy Std Dev'] != '' else ''
            self.setItem(row_id, 7, QtWidgets.QTableWidgetItem(strategy_std))
            benchmark_std = fmt.format(drawdown[1]['Benchmark Std Dev']) if drawdown[1][
                                                                                'Benchmark Std Dev'] != '' else ''
            self.setItem(row_id, 8, QtWidgets.QTableWidgetItem(benchmark_std))


def get_top_drawdowns(returns, min_drawdown=0, top=5):
    """
    Finds top drawdowns, sorted by drawdown amount.
    Parameters
    ----------
    returns : pd.Series
        Daily returns of the strategy, noncumulative.
         - See full explanation in tears.create_full_tear_sheet.
    top : int, optional
        The amount of top drawdowns to find (default 10).
    Returns
    -------
    drawdowns : list
        List of drawdown peaks, valleys, and recoveries. See get_max_drawdown.
    """
    min_drawdown = abs(min_drawdown)
    returns = returns.copy()
    df_cum = empyrical.cum_returns(returns, 1)
    running_max = np.maximum.accumulate(df_cum)
    underwater = df_cum / running_max - 1

    drawdowns = []
    dd_index = 1
    # for t in range(top):
    while dd_index < top:
        peak, valley, recovery = get_max_drawdown_underwater(underwater)
        dd = ((df_cum.loc[peak] - df_cum.loc[valley]) / df_cum.loc[peak]) * 100
        if dd < min_drawdown:
            break
        # Slice out draw-down period
        if not pd.isnull(recovery):
            underwater.drop(underwater[peak: recovery].index[1:-1],
                            inplace=True)
        else:
            # drawdown has not ended yet
            underwater = underwater.loc[:peak]

        drawdowns.append((peak, valley, recovery))
        if (len(returns) == 0) or (len(underwater) == 0):
            break
        if dd_index >= top:
            break
        dd_index += 1

    return drawdowns


def get_max_drawdown_underwater(underwater):
    """
    Determines peak, valley, and recovery dates given an 'underwater'
    DataFrame.
    An underwater DataFrame is a DataFrame that has precomputed
    rolling drawdown.
    Parameters
    ----------
    underwater : pd.Series
       Underwater returns (rolling drawdown) of a strategy.
    Returns
    -------
    peak : datetime
        The maximum drawdown's peak.
    valley : datetime
        The maximum drawdown's valley.
    recovery : datetime
        The maximum drawdown's recovery.
    """

    # end of the period
    # valley = np.argmin(underwater)  # this is deprecated (using idxmin instead)
    valley = underwater.idxmin(axis=0)
    # Find first 0
    peak = underwater[:valley][underwater[:valley] == 0].index[-1]
    # Find last 0
    try:
        recovery = underwater[valley:][underwater[valley:] == 0].index[0]
    except IndexError:
        recovery = np.nan  # drawdown not recovered
    return peak, valley, recovery


def gen_drawdown_table(strategy_returns, benchmark_returns, source, min_drawdown=0, top=10):
    """
    Places top drawdowns in a table.
    Parameters
    ----------
    returns : pd.Series
        Daily returns of the strategy, noncumulative.
         - See full explanation in tears.create_full_tear_sheet.
    top : int, optional
        The amount of top drawdowns to find (default 10).
    Returns
    -------
    df_drawdowns : pd.DataFrame
        Information about top drawdowns.
    """

    # mark the drawdowns in main-plot
    if source == drawdown_source_benchmark_returns:
        drawdown_periods = get_top_drawdowns(benchmark_returns, min_drawdown=abs(min_drawdown), top=top)
    else:
        drawdown_periods = get_top_drawdowns(strategy_returns, min_drawdown=abs(min_drawdown), top=top)

    strategy_df_cum = empyrical.cum_returns(strategy_returns, 1)
    benchmark_df_cum = empyrical.cum_returns(benchmark_returns, 1)
    df_drawdowns = pd.DataFrame(index=list(range(top)),
                                columns=['Strategy Drawdown',
                                         'Benchmark Drawdown',
                                         'Peak date',
                                         'Valley date',
                                         'Recovery date',
                                         'Duration',
                                         'Correlation',
                                         'Strategy Std Dev',
                                         'Benchmark Std Dev'])

    for i, (peak, valley, recovery) in enumerate(drawdown_periods):
        if pd.isnull(recovery):
            df_drawdowns.loc[i, 'Duration'] = np.nan
        else:
            df_drawdowns.loc[i, 'Duration'] = len(pd.date_range(peak,
                                                                recovery,
                                                                freq='B'))
        df_drawdowns.loc[i, 'Peak date'] = (peak.to_pydatetime()
                                            .strftime('%Y-%m-%d'))
        df_drawdowns.loc[i, 'Valley date'] = (valley.to_pydatetime()
                                              .strftime('%Y-%m-%d'))
        if isinstance(recovery, float):
            df_drawdowns.loc[i, 'Recovery date'] = recovery
        else:
            df_drawdowns.loc[i, 'Recovery date'] = (recovery.to_pydatetime()
                                                    .strftime('%Y-%m-%d'))
        df_drawdowns.loc[i, 'Strategy Drawdown'] = (
                                                           (strategy_df_cum.loc[peak] - strategy_df_cum.loc[valley]) /
                                                           strategy_df_cum.loc[peak]) * 100
        df_drawdowns.loc[i, 'Benchmark Drawdown'] = (
                                                            (benchmark_df_cum.loc[peak] - benchmark_df_cum.loc[
                                                                valley]) / benchmark_df_cum.loc[peak]) * 100
        if type(recovery) == pd.Timestamp:
            periodic_strategy_returns = strategy_returns.loc[peak:recovery]
            df_drawdowns.loc[i, 'Strategy Std Dev'] = periodic_strategy_returns.std() * 100
            periodic_benchmark_returns = benchmark_returns.loc[peak:recovery]
            df_drawdowns.loc[i, 'Benchmark Std Dev'] = periodic_benchmark_returns.std() * 100
            df_drawdowns.loc[i, 'Correlation'] = np.correlate(periodic_strategy_returns, periodic_benchmark_returns)[
                                                     0] * 100
        else:
            df_drawdowns.loc[i, 'Strategy Std Dev'] = ''
            df_drawdowns.loc[i, 'Benchmark Std Dev'] = ''
            df_drawdowns.loc[i, 'Correlation'] = ''

    df_drawdowns['Peak date'] = pd.to_datetime(df_drawdowns['Peak date'])
    df_drawdowns['Valley date'] = pd.to_datetime(df_drawdowns['Valley date'])
    df_drawdowns['Recovery date'] = pd.to_datetime(df_drawdowns['Recovery date'])

    return df_drawdowns
