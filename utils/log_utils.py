import logging
import os
import pandas as pd


def prepare_results_folder():
    path = "{}/results/{}".format(os.getcwd(), pd.datetime.now().strftime("%Y%m%d-%H%M%S"))
    if not os.path.isdir(path):
        os.makedirs(path)

    return path


results_path = prepare_results_folder()


def setup_logging(name):
    return logging.getLogger(name)
