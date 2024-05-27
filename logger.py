import datetime

class Logger:
    """ very simple console logger that is a wrapper on "print" """
    def __init__(self, log_to_console: bool = False):
        self.log_to_console = log_to_console

    def print_to_console(self, log_string: str):
        if self.log_to_console:
            print(f"{datetime.datetime.now().strftime('%H:%M:%S.%f')} :: {log_string}")

