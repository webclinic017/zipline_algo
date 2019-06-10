from PyQt5.QtCore import QUrl
from jinja2 import Environment, FileSystemLoader
import os
from utils.log_utils import setup_logging, get_results_path


try:
    from PyQt5.QtWebKitWidgets import QWebView
except:
    from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
from PyQt5.QtPrintSupport import QPrinter


logger = setup_logging("exporter_logging")
results_path = get_results_path()


class PdfGenerator(object):

    def __init__(self, tabs, analysis_data, app):
        self.analysis_data = analysis_data
        self.pdf_file_name = 'backtest_report.pdf'
        self.html_file_name = 'backtest_report.html'
        self.tabs = tabs
        self.template_path = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_path))
        self.app = app

    def generate(self):
        try:
            data = {}
            for key, tab in self.tabs.items():
                try:
                    if key in ('Holdings', 'Transactions', 'Performance'):
                        continue
                    tab.update_plot(self.analysis_data)
                    data[key] = tab.generate_report()
                except Exception as ex:
                    logger.error('Error: ' + str(ex))

            # render template with data
            params = {'template_file': "report.html"}
            for key, d in data.items():
                for tab_key, tab_data in d.items():
                    params[key + '_' + tab_key] = tab_data

            html = self.render_template(
                params
            )

            html_file = open(os.path.join(results_path, self.html_file_name), 'w')
            html_file.write(html)
            html_file.close()
            # QtPy webview to print pdf from html
            web = QWebView()
            url = QUrl.fromLocalFile(results_path)
            web.setHtml(html, baseUrl=url)
            self.app.processEvents()
            printer = QPrinter()
            printer.setPageSize(QPrinter.A4)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(os.path.join(results_path, self.pdf_file_name))
            printer.setColorMode(QPrinter.Color)
            web.print_(printer)
        except Exception as ex:
            logger.error('Error: ' + str(ex))

    def render_template(self, params):
        template = self.jinja_env.get_template(params['template_file'])
        return template.render(params)
