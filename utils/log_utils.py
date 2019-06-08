import logging
import logging.handlers
import os
import pandas as pd


def prepare_results_folder():
    path = "{}/results/{}".format(os.getcwd(), pd.datetime.now().strftime("%Y%m%d-%H%M%S"))
    if not os.path.isdir(path):
        os.makedirs(path)

    return path


results_path = prepare_results_folder()


def get_results_path():
    return results_path


def setup_logging(name, log_level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    formatter = logging.Formatter('%(asctimme)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    fileHandler = logging.handlers.RotatingFileHandler(os.path.join(results_path, name + ".log"),
                                                       maxBytes=4096000, backupCount=7)

    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    return logger

    # logging.basicConfig(level=log_level)
    # return logging.getLogger(name)
