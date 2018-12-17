from utils.views.group_config_box import GroupConfigBoxWidget
from ote.analyzer.views.plot_returns import Plotter
from PyQt5 import QtWidgets


APPROX_BDAYS_PER_MONTH = 21
strategy_long_plot_color = '#0288D1'
strategy_short_plot_color = '#FF8F00'
benchmark_plot_color = 'gray'  # '#BDBDBD'
rolling_period = [('1-Month', APPROX_BDAYS_PER_MONTH), ('3-Month', 3 * APPROX_BDAYS_PER_MONTH),
                  ('6-Month', 6 * APPROX_BDAYS_PER_MONTH), ('12-Month', 12 * APPROX_BDAYS_PER_MONTH)]

plot_style_fill = True
drawdown_plot_name = 'Drawdown'
exposure_plot_name = 'Exposure'
positions_plot_name = 'Positions'
alpha_plot_name = 'Alpha'
beta_plot_name = 'Beta'
sharpe_plot_name = 'Sharpe'
sortino_plot_name = 'Sortino'


class PerformanceTab:

    def __init__(self, parent):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.plotter = Plotter(self)

        self.custom_column_names = set()

        grid = QtWidgets.QGridLayout()
        firstgroup_widget = QtWidgets.QWidget()
        firstgroup_layout = QtWidgets.QVBoxLayout(firstgroup_widget)
        self.firstgroup_gbox = GroupConfigBoxWidget('Performance', firstgroup_widget)
        firstgroup_vbox = QtWidgets.QVBoxLayout()

        firstgroup_vbox.addWidget(self.plotter)
        firstgroup_vbox.setSpacing(0)
        self.firstgroup_gbox.setLayout(firstgroup_vbox)

        firstgroup_layout.setContentsMargins(0, 0, 0, 0)
        firstgroup_layout.addWidget(self.firstgroup_gbox)

        grid.addWidget(firstgroup_widget, 0, 0)

        self.setLayout(grid)

        # prepare menus
        self.main_menu = QtWidgets.QMenu(self.get_tab_name(), self)
        main_plot_menu = QtWidgets.QMenu('Main Plot', self)
        main_plot_menu.addAction('Toggle scale', self.plotter.toggle_plot_scale)

        # self.custom_data_menu = QtWidgets.QMenu('Custom Data', self)
        # main_plot_menu.addMenu(self.custom_data_menu)

        self.subplot_menus = [QtWidgets.QMenu('Subplot 1', self), QtWidgets.QMenu('Subplot 2', self)]
        self.main_menu.addMenu(main_plot_menu)
        self.main_menu.addMenu(self.subplot_menus[0])
        self.main_menu.addMenu(self.subplot_menus[1])

        # cache the selected subplot
        self.selected_subplots = [exposure_plot_name, drawdown_plot_name]

        self.add_subplot_menu(0, self.subplot_menus[0], default_subplot=self.selected_subplots[0])
        self.add_subplot_menu(1, self.subplot_menus[1], default_subplot=self.selected_subplots[1])

        self.firstgroup_gbox.button.setMenu(self.main_menu)

    def get_tab_name(self):
        return 'Performance'

    def get_tab_menu(self):
        return self.main_menu

    def get_tab_description(self):
        return 'View performance characteristics of strategy.'

    def update_plot(self, analysis_data):
        if analysis_data is not None and analysis_data.user_data is not None and analysis_data.user_data.shape[0] > 0:
            new_custom_column_names = set(analysis_data.user_data.columns) - self.custom_column_names
            for a_col in new_custom_column_names:
                if len(a_col) > 0:
                    self.subplot_menus[0].actions()[-1].menu()\
                        .addAction(a_col, lambda a_col=a_col: self.open_custom_data_subplot(0, a_col))
                    self.subplot_menus[1].actions()[-1].menu()\
                        .addAction(a_col, lambda a_col=a_col: self.open_custom_data_subplot(1, a_col))
                    self.custom_column_names.add(a_col)

        self.plotter.plot(analysis_data)

    def open_plot(self, n, name, r_period=None):
        if name == drawdown_plot_name:
            self.plotter.open_subplot(sb.DrawdownSubPlotter(), n)
        elif name == exposure_plot_name:
            self.plotter.open_subplot(sb.ExposureSubPlotter(), n)
        elif name == positions_plot_name:
            self.plotter.open_subplot(sb.PositionsSubPlotter(), n)
        elif name == alpha_plot_name:
            self.plotter.open_subplot(sb.AlphaSubPlotter(r_period), n)
        elif name == beta_plot_name:
            self.plotter.open_subplot(sb.BetaSubPlotter(r_period), n)
        elif name == sharpe_plot_name:
            self.plotter.open_subplot(sb.SharpeSubPlotter(r_period), n)
        elif name == sortino_plot_name:
            self.plotter.open_subplot(sb.SortinoSubPlotter(r_period), n)

        for item in self.subplot_menus[n].actions():
            # break the loop if the name is already selected in current subplot
            # e.g. select Alpha-1month when the current subplot is Alpha-3month
            if self.selected_subplots[n] == name:
                break

            if item.text() == name:
                item.setChecked(True)
            if item.text() == self.selected_subplots[n]:
                item.setChecked(False)
        self.selected_subplots[n] = name

    def add_subplot_menu(self, n, subplot, default_subplot):
        alpha_menu = QtWidgets.QMenu(alpha_plot_name, self)
        beta_menu = QtWidgets.QMenu(beta_plot_name, self)
        sharpe_menu = QtWidgets.QMenu(sharpe_plot_name, self)
        sortino_menu = QtWidgets.QMenu(sortino_plot_name, self)
        subplot.addMenu(alpha_menu)
        subplot.addMenu(beta_menu)

        subplot.addAction(drawdown_plot_name, lambda: self.open_plot(n, drawdown_plot_name))
        subplot.addAction(exposure_plot_name, lambda: self.open_plot(n, exposure_plot_name))
        subplot.addAction(positions_plot_name, lambda: self.open_plot(n, positions_plot_name))
        subplot.addMenu(sharpe_menu)
        subplot.addMenu(sortino_menu)

        alpha_menu.addAction(rolling_period[0][0], lambda: self.open_plot(n, alpha_plot_name, 0))
        alpha_menu.addAction(rolling_period[1][0], lambda: self.open_plot(n, alpha_plot_name, 1))
        alpha_menu.addAction(rolling_period[2][0], lambda: self.open_plot(n, alpha_plot_name, 2))
        alpha_menu.addAction(rolling_period[3][0], lambda: self.open_plot(n, alpha_plot_name, 3))
        beta_menu.addAction(rolling_period[0][0], lambda: self.open_plot(n, beta_plot_name, 0))
        beta_menu.addAction(rolling_period[1][0], lambda: self.open_plot(n, beta_plot_name, 1))
        beta_menu.addAction(rolling_period[2][0], lambda: self.open_plot(n, beta_plot_name, 2))
        beta_menu.addAction(rolling_period[3][0], lambda: self.open_plot(n, beta_plot_name, 3))
        sharpe_menu.addAction(rolling_period[0][0], lambda: self.open_plot(n, sharpe_plot_name, 0))
        sharpe_menu.addAction(rolling_period[1][0], lambda: self.open_plot(n, sharpe_plot_name, 1))
        sharpe_menu.addAction(rolling_period[2][0], lambda: self.open_plot(n, sharpe_plot_name, 2))
        sharpe_menu.addAction(rolling_period[3][0], lambda: self.open_plot(n, sharpe_plot_name, 3))
        sortino_menu.addAction(rolling_period[0][0], lambda: self.open_plot(n, sortino_plot_name, 0))
        sortino_menu.addAction(rolling_period[1][0], lambda: self.open_plot(n, sortino_plot_name, 1))
        sortino_menu.addAction(rolling_period[2][0], lambda: self.open_plot(n, sortino_plot_name, 2))
        sortino_menu.addAction(rolling_period[3][0], lambda: self.open_plot(n, sortino_plot_name, 3))

        for item in subplot.actions():
            if item.text() == default_subplot:
                item.setCheckable(True)
                item.setChecked(True)
            else:
                item.setCheckable(True)
                item.setChecked(False)
