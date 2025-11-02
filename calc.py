
import numpy as np
import math as math
import matplotlib.pyplot as plt
from copy import copy
import inspect
import builtins
import sys
import plots

try:
    from logger import Logger
    logger = Logger(log_to_console=True)
    log = logger.print_to_console
except ImportError:
    log = print

# log the python imported lib versions
log(f"Python version: {sys.version}")
log(f"numpy version: {np.__version__}")



class Calculator:
    """ A class that implements the backend of an RPN style calculator with the ability to perform RPN style operations
    on numbers AND python objects. The primary interface is the 'user_entry(input: any)' method which can handle most
    input you throw at it.

    Being an RPN calculator it uses a stak which is a list of objects. The objects can represent these things:
        1) numbers: any string/number that can be parsable as a numeric class via Python int() or float() calls
        2) a python object: like [1, 2, 3] or {a: 1, b: 2}, this extends to any python object
        3) a python method reference: like np.array or datetime.datetime.now

        Warning: Because of the use of the eval() and exec() calls you have the same risk of executing code that
            can potentially do bad things to your computer and/or data as a developer. This application does
            not connect to a network so it does not have the same safety risks that are typically brought up
            for using eval() on servers and backends. The risk is primarily on the user to know enough about developing
            to not delete/overwrite/move their own files by accident. If you want to be extra safe,
            you can turn off the "execute arbitrary code" feature in the settings. At this point
            the calculator will just behave like a calculator and not a python interpreter.

        outside the stack the python interpreter will store the local variables and functions that are defined

        A note on terminology, as a long time RPN I refer to the stak positions as X, Y, Z, and T (thanks HP)
        so in the code when it says grab X it means grab stack[0] and Y means stack[1] and so on. Additionally it
        refers to what the user would see on the stack before an operation. So in the context of a method,
        when you are popping things off the stack Y is Y even if it moves to stack[0] during the operation."""

    def __init__(self):
        """ initializes the calculator object with the default values for the stack, locals, and exec_globals """
        # print the version of python
        print(f"Python version: {sys.version}")
        self._stack = []
        self._last_stack_operation = None
        self._stack_history_length = 100 # units are in number of saved stacks, not a memory size
        self._stack_history = [] # a list of stacks, use the update_stack_history() method to prevent mem runaway
        self._message = None
        self._locals = dict()
        self._exec_globals = dict()
        self._math = math
        self._button_functions = dict() # a dict of all the pre-defined calculator 'button' functions, like sqrt, sin, .
        self._imported_libs = set() # a set of all imported libraries
        self._imported_functions = set() # a set of all imported functions
        self._user_functions = dict() # a dict of all user defined functions like {'name': '<function def text>'}
        self._all_functions = set() # a set of all possible functions that can be called including buttons and imports
        self._setting_invert_lists = True  # when using stack to list/array this flips the direction of the list

        # use the awesome math lib to grab some pre-defined math methods ....  mathods?
        math_lib_functions = dir(math)
        math_lib_functions.remove('e') # this is a constant not a function, also it prevents you using e in a string
        math_lib_functions.remove('pi') # this is a constant not a function
        math_lib_functions.remove('tau') # this is a constant not a function
        math_lib_functions.remove('inf') # this is a constant not a function
        math_lib_functions.remove('nan')
        math_lib_functions.remove('log') # we want to handle this so we can explicitly have ln and log

        # We want to handle mathlib functions explicitly so there is no unexpected behavior. Split the math library
        # into four categories that can be handled based on the signature of the function:
        # 1) one argument functions,
        # 2) two argument functions,
        # 3) iterable functions, and
        # 4) constants

        # List of all math functions that take exactly one argument
        one_arg_math_funcs = ['acos', 'acosh', 'asin', 'asinh', 'atan', 'atanh', 'ceil', 'cos', 'cosh', 'degrees',
                              'erf', 'erfc', 'exp', 'expm1', 'fabs', 'floor', 'gamma', 'lgamma', 'log1p', 'log2',
                              'log10', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'trunc', 'isnan', 'isinf',
                              'isfinite', 'frexp', 'ulp', 'factorial', 'modf',]

        # List of all math functions that take exactly two arguments
        two_arg_math_funcs = ['atan2', 'copysign', 'fmod', 'gcd', 'hypot', 'ldexp', 'pow', 'remainder', 'nextafter',
                              'isclose']

        # List of all math functions that only take an iterable as an argument
        iterable_math_funcs = ['prod', 'comb', 'perm', 'gcd', 'isqrt', 'dist', 'lcm', 'fsum']

        # list of all math constants
        math_constants = ['e', 'pi', 'tau', 'inf', 'nan']

        # as a check, make sure we have accounted for all the methods in the math libray
        all_math = {item for item in math_lib_functions if not item.startswith('_')}
        calc_math = set(one_arg_math_funcs + two_arg_math_funcs + iterable_math_funcs + math_constants)
        difference = all_math - calc_math
        if len(difference) > 0:  # if there is difference, print them out so we can see what we missed
            log(f"Error: new function found in math library: \n")
            for item in difference:
                try:
                    sig = inspect.signature(getattr(math, item))
                    print(f'{item} = {sig},types: {[sig.parameters[p].annotation for p in sig.parameters]},\n ' \
                          f'doc: {getattr(math, item).__doc__}')
                except Exception as ex:
                    print(f'ERROR::: cant get signature for "{item}" with ex: {ex}')
            print('------------------------------------------------------------------\n')

        # link the math functions to the appropriate calculator methods
        one_args = {item: lambda i=item: self.one_arg_function_press(i) for item in one_arg_math_funcs}
        two_args = {item: lambda i=item: self.two_arg_function_press(i) for item in two_arg_math_funcs}
        iterable_args = {item: lambda i=item: self.iterable_function_press(i) for item in iterable_math_funcs}

        # create a dictionary of built-in functions and operations that can be called directly by the user
        built_in_functions = {      # math operations
                                    '+': lambda: self.stack_operation('+'),
                                    '-': lambda: self.stack_operation('-'),
                                    '*': lambda: self.stack_operation('*'),
                                    '/': lambda: self.stack_operation('/'),
                                    '**': lambda: self.stack_operation('**'),
                                    '!': lambda: self.stack_function_press('factorial'),
                                    'x^2': lambda: self.raise_pow_2(),
                                    'x^y': lambda: self.raise_pow_x(),
                                    'e^x': lambda: self.raise_pow_e(),

                                    # constants
                                    'pi': lambda: self._constant_press('3.14159265'),
                                    'euler': lambda: self._constant_press('2.71828182'),
                                    'phi': lambda: self._constant_press('1.61803398'),
                                    'jackpot': lambda: self._constant_press('777'),

                                    # stack operations
                                    'swap': lambda: self.swap_x_y(),
                                    'drop': lambda: self.clear_stack_level(0),
                                    'dup': lambda: self.stack_put(self._stack[0], shift_up=True),
                                    'rot': lambda: self.roll_down(),
                                    'swap_x_y': lambda: self.swap_x_y(),
                                    'x<->y': lambda: self.swap_x_y(),
                                    'negate': lambda: self.negate_x(),
                                    '+/-': lambda: self.negate_x(),
                                    '1/x': lambda: self.reciprocal_x(),
                                    'recip': lambda: self.reciprocal_x(),
                                    'iterable_to_stack': lambda: self.iterable_to_stack(),
                                    'stack_to_list': lambda: self.stack_to_list(),
                                    'stack_to_array': lambda: self.stack_to_array(),
                                    'roll_up': lambda: self.roll_up(),
                                    'roll_down': lambda: self.roll_down(),
                                    'enter': lambda: self.enter_press(),
                                    'clear': lambda: self.clear_stack_level(),
                                    'delete': lambda: self.delete_last_char(),
                                    'undo': lambda: self.undo_last_action(pop_last_history=True),

                                    # wrappers for the math library that expose more natural language functions like ln
                                    'ln': lambda: self.natural_log(),
                                    'ncr': lambda: self.n_choose_r(),
                                    'npr': lambda: self.n_permutations_r(),

                                    # plot functions
                                    'show_plot': lambda: self.show_plot(),
                                }

        self._button_functions = built_in_functions | one_args | two_args | iterable_args
        self._all_functions = set(self._button_functions.keys()) | self._user_functions.keys()

        # add the math functions to the exec_globals so they can be used in eval and exec
        self._exec_globals.update(math.__dict__)
        py_builtins = builtins.__dict__
        # py_operators = {str(op).replace('__', ''): getattr(operator, op) for op in dir(operator)}
        self._exec_globals.update(py_builtins)
        # self._exec_globals.update(py_operators)

        # finally, load up numpy, and matplotlib because they are distributed with python and supercharge the calculator
        self.user_entry('import math as math')
        self.user_entry('enter')

        self.user_entry('import numpy as np')  # you can import any installed library into the calculator like this
        self.user_entry('enter')

        self.user_entry('import matplotlib.pyplot as plt')
        self.user_entry('enter')

    def undo_last_action(self, pop_last_history=False):
        """ undoes the last action by restoring the stack to the previous state
        @param pop_last_history: if True, the last history entry is popped off the history stack. This is used in the
                                 case that you type 'undo' and then press enter. because the enter press will
                                 always add an item to the undo history, you need to pop it off so you dont get stuck
                                not being able to actually undo anything
        """
        self._message = None
        if pop_last_history:
            _removed_A = self._stack_history.pop(-1)  # removes the 'undo'
            _removed_B = self._stack_history.pop(-1)  # removes the 'enter'
        if len(self._stack_history) > 0:
            self._stack = self._stack_history.pop(-1)
            self._message = f"Undo: restored stack to previous state. History Length: '{len(self._stack_history)}'"
            log(self._message)
            log(f"STACK: {self._stack}")
        else:
            self._message = f"Error: no history to undo"
            log(self._message)

    """ -------------------------------- Math Wrapper Functions -------------------------------- """

    def raise_pow_2(self):
        """ raises the value in X to the power of 2 """
        self._message = None
        if len(self._stack) > 0:
            self._update_stack_history()
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                result = x ** 2
                self.stack_put(result)
                self._message = f"Function: x^2({x}) = {result}"
            except Exception as ex:
                self.stack_put(x)
                self._message = f"Error: cant raise x to the power of 2: '{x}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'x^2'"
            log(self._message)

    def raise_pow_x(self):
        """ raises y to the power of x"""
        self._message = None
        if len(self._stack) > 1:
            self._update_stack_history()
            x = self._stack.pop(0)
            y = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                y = self._convert_to_best_numeric(y)
                result = y ** x
                self.stack_put(result)
                self._message = f"Function: x^y({x}, {y}) = {result}"
            except Exception as ex:
                self.stack_put(y)
                self.stack_put(x)
                self._message = f"Error: cant raise y to the power of x: '{y}' and '{x}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'x^y'"
            log(self._message)

    def raise_pow_e(self):
        """ raises e to the power of x """
        self._message = None
        if len(self._stack) > 0:
            self._update_stack_history()
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                result = math.exp(x)
                self.stack_put(result)
                self._message = f"Function: e^x({x}) = {result}"
            except Exception as ex:
                self.stack_put(x)
                self._message = f"Error: cant raise e to the power of x: '{x}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'e^x'"
            log(self._message)

    def natural_log(self):
        """ takes the natural log of the value in X """
        self._message = None
        if len(self._stack) > 0:
            self._update_stack_history()
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                result = math.log(x)
                self.stack_put(result)
                self._message = f"Function: ln({x}) = {result}"
            except Exception as ex:
                self.stack_put(x)
                self._message = f"Error: cannot perform function: 'ln' on non-number: '{x}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'ln'"
            log(self._message)

    def n_choose_r(self):
        """ calculates the number of ways to choose r items from a set of n items where r=x and n=y """
        self._message = None
        if len(self._stack) > 1:
            self._update_stack_history()
            r = self._stack.pop(0)
            n = self._stack.pop(0)
            try:
                n = self._convert_to_best_numeric(n)
                r = self._convert_to_best_numeric(r)
                result = math.comb(n, r)
                self.stack_put(result)
                self._message = f"Function: nCr({n}, {r}) = {result}"
            except Exception as ex:
                self.stack_put(n)
                self.stack_put(r)
                self._message = f"Error: cant perform function: 'nCr' on non-number: '{n}' and '{r}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'nCr'"
            log(self._message)

    def n_permutations_r(self):
        """ calculates the number of ways to choose r items from a set of n items where order matters, where r=x and n=y
        """
        self._message = None
        if len(self._stack) > 1:
            self._update_stack_history()
            r = self._stack.pop(0)
            n = self._stack.pop(0)
            try:
                n = self._convert_to_best_numeric(n)
                r = self._convert_to_best_numeric(r)
                result = math.perm(n, r)
                self.stack_put(result)
                self._message = f"Function: nPr({n}, {r}) = {result}"
            except Exception as ex:
                self.stack_put(n)
                self.stack_put(r)
                self._message = f"Error: cant perform function: 'nPr' on non-number: '{n}' and '{r}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'nPr'"
            log(self._message)

    def negate_x(self):
        """ negates the value in x """
        self._message = None
        if len(self._stack) > 0:
            self._update_stack_history()
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                result = -x
                self.stack_put(result)
                self._message = f"Negate: -({x}) = {result}"
            except Exception as ex:
                self.stack_put(x)
                self._message = f"Error: cant negate: '{x}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'negate'"
            log(self._message)

    def reciprocal_x(self):
        """ takes the reciprocal of the value in X """
        self._message = None
        if len(self._stack) > 0:
            self._update_stack_history()
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                result = 1 / x
                self.stack_put(result)
                self._message = f"Reciprocal: 1/{x} = {result}"
            except Exception as ex:
                self.stack_put(x)
                self._message = f"Error: cant take reciprocal of: '{x}' with error: '{ex}'"
                log(self._message)
                return
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'reciprocal'"
            log(self._message)

    """  -------------------------------- Stack Operations -------------------------------- """

    def swap_x_y(self):
        """ swaps the values in X and Y """
        self._message = None
        if len(self._stack) > 1:
            self._update_stack_history()
            x = self._stack.pop(0)
            y = self._stack.pop(0)
            self.stack_put(x)
            self.stack_put(y)
            self._message = f"Swap: {x} and {y}"
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: 'swap'"
            log(self._message)

    """ -------------------------------------- Plotting ----------------------------------- """

    def show_plot(self, plot_args=None):
        """ is a wrapper on plt.plot() and plt.show(), if no plot to show it will log an error """
        self._message = None
        if len(self._stack) > 0:
            x = self._stack[0] # dont pop X, leave it on the stack for error and success
            try:
                iter(x)
                if isinstance(x[0], plt.Artist):
                    pass  # plt.show() is called below
                else:
                    if plot_args is not None:
                        plt.plot(x, plot_args)
                    else:
                        plt.plot(x)
            except Exception as ex:
                pass # this is to catch the iter(x) error
            try:  # just plot whatever is loaded
                plt.grid()  # todo: add more built in plot options
                plt.show()
                self._message = f"Plot shown"
            except Exception as ex:
                self._message = f"Error: show_plot() cant show plot with error: '{ex}'"
                log(self._message)

    def show_plots_dict(self, plots: dict):
        """ shows a plot of X vs Y, X and Y can be any iterable, like a list or numpy array:
         :param plots: [dict] of plot objects like {<trace name>: <plots.PlotContainer>, ...}"""
        self._message = None
        try:
            plot_lib = plt
            for name, p in plots.items():
                p.display_plot(plot_lib, name)

            plot_lib.legend()
            plot_lib.show()

        except Exception as ex:
            self._message = f"Error: show_plots_dict() cant show plot with error: '{ex}'"
            log(self._message)


    def user_entry(self, user_input: any):
        """ Parses the user input string and performs the appropriate action. This method is the primary interface
        for the calculator class. This method is polymorphic and can be called with any input, if it cant handle it,
        it will log an error and store the last error message to the messages field.

        Note: this method handles single character input as well as entire strings.

        @param user_input: the input from the user, can be a string, number, or python object
        """
        # log(f"User entry: {user_input}") # for debugging
        self._message = None

        # most common input is a string
        if isinstance(user_input, str):
            if len(self._stack) > 0:
                if isinstance(self._stack[0], list|tuple|set|np.ndarray|int|float):
                    # pushes these types to stack[1] and inserts string at stack[0]

                    if self._last_stack_operation == 'enter' and len(self._stack) > 1:
                        # in this case you might have a duplicate in X and Y so replace X instead of shifting up
                        if self._stack[0] == self._stack[1]:
                            if user_input in self._button_functions and user_input != 'e':  # watch out for Euler:
                                self._button_functions[user_input]()
                                return  # ----------------------------------------------------------------------------->
                            else:
                                self.stack_put(user_input, shift_up=False)
                                self._last_stack_operation = 'user_entry'
                                return  # ----------------------------------------------------------------------------->

                    if user_input in self._button_functions and user_input != 'e':  # watch out for Euler:
                        self._button_functions[user_input]()
                        return  # ------------------------------------------------------------------------------------->
                    else:
                        self.stack_put(user_input)
                        self._last_stack_operation = 'user_entry'
                        return  # ------------------------------------------------------------------------------------->

            # check X for '(' to see if user is entering a function like (1+1)
            if len(self._stack) > 0:
                x_ref = self._stack[0]
            else:
                x_ref = user_input
            tokens = {'(', '[', '{'}  # if the user opened a bracket, they are entering a function or list or dict
            for token in tokens:
                if token in str(x_ref):
                    break
            else:
                if user_input in self._button_functions and user_input != 'e': # watch out for Euler:
                    self._button_functions[user_input]()
                    return # ------------------------------------------------------------------------------------->

            # if not in the function dict, its a string entry
            # if the last stack entry was 'enter' then the user is entering a new string value
            shift_vals = {'enter', 'assignment', 'recall'}
            if self._last_stack_operation in shift_vals:
                self.stack_put(user_input, shift_up=False)

            else:
                if len(self._stack) == 0:
                    self.stack_put(user_input)
                else:
                    x_temp = self._stack[0]

                    # good case: you can append a string to a string
                    if isinstance(x_temp, str):
                        self.stack_put(x_temp + user_input, shift_up=False)

                    # put on a new line in the stack
                    else:
                        self.stack_put(user_input)

        # if not a string, then put it on the stack whatever it is and feel the power of dynamic typing
        else:
            # log(f"User Entry: not a string: {user_input}")
            self.stack_put(user_input)

        # do some housekeeping for the calc object
        self._last_stack_operation = 'user_entry'
        # self._print_stack()   # for debugging

    def one_arg_function_press(self, function):
        """ uses the math library to perform a function on the stack value and put the result back on the stack.
        These functions require one argument, so the stack must have at least one value on it in Y """
        self._message = None
        if len(self._stack) > 0:
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                result = getattr(self._math, function)(x)
                self.stack_put(result)
                self._message = f"Function: {function}({x}) = {result}"

            except Exception as ex:
                # check if object is iterable
                try:
                    _iterable = iter(x)
                    # need to write a methoid that handles iterables in a good way

                    if isinstance(x, list|tuple|set):
                        result = []

                        # apply the function for each item in the list
                        for item in x:
                            result.append(getattr(self._math, function)(item))

                        # set the result to the correct type
                        if isinstance(x, tuple):
                            result = tuple(result)
                        elif isinstance(x, set):
                            result = set(result)
                        else:
                            pass  # return a list

                    elif isinstance(x, np.ndarray):
                        try:
                            result = getattr(x, f'np.{function}')() # function like 'sin'
                            print(result)
                        except Exception as ex:
                            result = ex
                            print(ex)

                    # end method returns result

                    # result = getattr(self._math, function)(x)
                    self.stack_put(result)
                    self._message = f"Function: {function}({x}) = {result}"

                except TypeError as ex: # it's not iterable and it's not a number so put it back on the stack

                    self.stack_put(x)
                    self._message = f"Error: cannot perform function: '{function}' on non-number: '{x}' with error: '{ex}'"
                    log(self._message)
                    raise Exception(self._message)
        else:
            self._message = f"Error: not enough values on the stack to perform the operation: '{self._stack[0]}'"

    def two_arg_function_press(self, function):
        """ uses the math library to perform a function on the stack value and put the result back on the stack.
        These functions require two arguments, so the stack must have at least two values on it in Y and Z """
        self._message = None
        if len(self._stack) > 1:
            x = self._stack.pop(0)
            y = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
                y = self._convert_to_best_numeric(y)
            except ValueError:
                self.stack_put(y)
                self.stack_put(x)
                self._message = f"Error: cannot perform function: '{function}' on non-number: '{x}' and '{y}'"
                log(self._message)
                raise Exception(self._message)
            else:
                try:
                    result = getattr(math, function)(y, x)
                except Exception as ex:
                    self.stack_put(y)
                    self.stack_put(x)
                    self._message = f"Error: function: '{function}' failed with: '{ex}'"
                    log(self._message)
                    raise Exception(self._message)
                else:
                    self.stack_put(result)
                    self._message = f"Function: {function}({y}, {x}) = {result}"
        else:
            self._message = f"Error: not enough values on the stack to perform an operation: '{function}'"
            log(self._message)

    def iterable_function_press(self, function):
        """ uses the math library to perform a function on the stack value and put the result back on the stack"""
        self._message = None
        if len(self._stack) > 0:
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
            except ValueError:
                self.stack_put(x)
                self._message = f"Error: cannot perform function: '{function}' on non-number: '{x}'"
                log(self._message)
                raise Exception(self._message)
            else:
                try:
                    result = getattr(math, function)(x)
                except Exception as ex:
                    self.stack_put(x)
                    self._message = f"Error: function: '{function}' failed with: '{ex}'"
                    log(self._message)
                    raise Exception(self._message)
                else:
                    self.stack_put(result)
                    self._message = f"Function: {function}({x}) = {result}"
        else:
            self._message = f"Error: not enough values on the stack to perform an operation: '{function}'"
            log(self._message)

    def roll_up(self):
        """ rolls the stack by popping the last value and inserting it a X"""
        self._message = None
        if len(self._stack) > 1:
            x = self._stack.pop(-1)
            self.stack_put(x)
            self._message = f"Roll up: {x}"
        else:
            self._message = f"Error: not enough values on the stack to perform a roll up"
            log(self._message)

    def roll_down(self):
        """ rolls the stack by popping the value at X and inserting it at the end of the stack"""
        self._message = None
        if len(self._stack) > 1:
            x = self._stack.pop(0)
            stack_len = len(self._stack)
            self.stack_put(x, position=stack_len, shift_up=False)
            self._message = f"Roll down: {x}"
        else:
            self._message = f"Error: not enough values on the stack to perform a roll down"
            log(self._message)

    def stack_function_press(self, function):
        """ uses the math library to perform a function on the stack value and put the result back on the stack.
        @param function: the function to perform on the stack value
        @return: None, if success the result is on the stack, if failure the stack is restored to its previous state
        """
        self._message = None
        if len(self._stack) > 0:
            x = self._stack.pop(0)
            try:
                x = self._convert_to_best_numeric(x)
            except ValueError:
                # try passing the whatever the object is to the method
                try:
                    result = getattr(math, function)(x)
                except Exception as ex:
                    self.stack_put(x)
                    self._message = f"Error: cannot perform function: '{function}' on non-number: '{x}'"
                    log(self._message)
                    return # ------------------------------------------------------------------------------------------>
                else:
                    self.stack_put(result)
                    self._message = f"Function: {function}({x}) = {result}"

            else:
                if function in dir(math):
                    try:
                        result = getattr(math, function)(x)
                    except Exception as ex:

                        # it might require passed arguments (x, y)

                        # check if y is a number
                        try:
                            y = self._stack.pop(0)
                            y = self._convert_to_best_numeric(y)
                        except Exception as ey:
                            self._message = f"Error: function: '{function}' failed with: '{ex}' and '{ey}'"
                            self.stack_put(y)
                            self.stack_put(x)
                            log(self._message)
                            return # ---------------------------------------------------------------------------------->
                        else:

                            # now try calling <method>(x, y)
                            try:
                                result = getattr(math, function)(x, y)
                            except Exception as ez:
                                self._message = f"Error: function: '{function}' failed with: '{ex}' and '{ez}'"
                                self.stack_put(y)
                                self.stack_put(x)
                                log(self._message)
                                return # ------------------------------------------------------------------------------>
                            else:
                                self.stack_put(result)
                                self._message = f"Function: {function}({x}, {y}) = {result}"

                    else: # calling <method>(x) was successful
                        self.stack_put(result)
                        self._message = f"Function: {function}({x}) = {result}"

                else: # function is not in the math library
                    self._message = f"Error: function: '{function}' not in math library"
                    self.stack_put(x)
                    log(self._message)

        self._last_stack_operation = 'function'

    def stack_put(self, value, position=0, shift_up=True):
        """Put a value into the stack at a given position.
        @param value: The value to put into the stack.
        @param position: The position in the stack to put the value.
        @param shift_up: If True, shift the values above the position up.
        @return: None, if success the value is on the stack, if failure an error message is stored to the message field
        """
        # self._update_stack_history() # if changing the stack save the state first, um this captures every keypress
        if shift_up:
            self._stack = self._stack[:position] + [value] + self._stack[position:]
        else:
            if len(self._stack) == 0 and position ==0:
                self._stack.append(value)
            elif position < len(self._stack):
                self._stack[position] = value
            elif position == len(self._stack):
                self._stack.append(value)
            else:
                self._message = f"Error: cannot put value: '{value}' at position: '{position}' in stack"
                log(self._message)

    def enter_press(self):
        """ do something reasonable when the user presses enter. Returns on first success or fatal error """
        self._update_stack_history()
        self._message = None

        if len(self._stack) > 0:  # else do nothing

            # .........................................
            #   Handle recalling a local variable
            # .........................................
            # if the only thing in X is a local variable name, then recall the value of that variable to X
            x_ref = self._stack[0]
            if isinstance(x_ref, str): # its python so keys can be anything, but if it's a string, strip it
                x_ref = x_ref.strip()

                if x_ref in self._locals:
                    self._stack.pop(0) # clear the name from the stack
                    self.stack_put(self._locals[x_ref])
                    self._last_stack_operation = 'recall'
                    return # ------------------------------------------------------------------------------------------>

            # .........................................
            #   Handle variable assignment
            # .........................................
            # if an '=' char is found in X then it is most likely an assignment
            if self._last_stack_operation != 'assignment':  # you have to press enter after an assignment

                if isinstance(self._stack[0], str):
                    if '=' in self._stack[0]:
                        x_temp = self._stack.pop(0)
                        try:

                            assignment_list = x_temp.split('=')  # like ['a', '1']
                            # we want something like ['a', '1'], not  ['a', ''] for this case
                            if assignment_list[1] != '':
                                var_key = assignment_list[0].strip()
                                var_value = assignment_list[1].strip()

                                # if the var_value can be a number, then convert it, else it can be anything else
                                try:
                                    var_value = self._convert_to_best_numeric(var_value)
                                except Exception as ex:
                                    pass # this is the case that var_value is NOT a number, but that is ok

                            # if 'a=' is on the stack @X, and Y is anything (except empty),
                            # then assign Y to the name in X
                            elif len(self._stack) > 0:
                                # check the stack and assign Y to the name in X
                                # we popped X so now grab what is in position 0
                                var_key = assignment_list[0].strip()
                                var_value = self._stack.pop(0)

                            else:  # nothing in Y so just assign the name to None
                                var_key = assignment_list[0].strip()
                                var_value = None

                            illegal_namespace = set(self._locals) ^ set(self._exec_globals)

                            if var_key in illegal_namespace:
                                self._message = f"Error: cant assign variable to built in: '{var_key}'"
                                self.stack_put(var_value)
                                self.stack_put(var_key)
                                self._last_stack_operation = 'error'
                                log(self._message)
                                return # ------------------------------------------------------------------------------>
                            self._locals.update({var_key: var_value})
                            # exec adds a __builtins__ to the locals so keep a clean copy of locals and an _exec_globals
                            # for passing to exec, if you want you can modify globals here
                            for key, value in self._locals.items():
                                self._exec_globals.update({key: value})
                            self.stack_put(var_value)
                            self._message = f"Assignment: {var_key} = {var_value}"
                            self._last_stack_operation = 'assignment'
                            log(self._message)
                            return  # --------------------------------------------------------------------------------->

                        except Exception as ex:
                            self._message = f"Error: assignment '{x_temp}' failed with: {ex}"
                            self.stack_put(x_temp)
                            log(self._message)

            # .........................................
            # handle pushing X to Y
            # .........................................
            # if the only thing in X is a number, then duplicate the number in X into X so that X is in both X and Y
            try:
                x = self._stack.pop(0)
                number = self._convert_to_best_numeric(x)  # this will raise an exception if x is not a number
                self.stack_put(number, shift_up=True)
                self._duplicate_x_value_in_y_position()
                return # ---------------------------------------------------------------------------------------------->
            except Exception as ex:
                self._message = f"Error in enter_press: roll up: {ex}"
                self.stack_put(x)

            # .........................................
            #   Handle function calls
            # .........................................
            x_str = str(self._stack[0])
            if x_str in self._all_functions:
                # since the math library has poor support for signature inspect,
                # we have to handle the functions explicitly
                if x_str in self._button_functions:
                    # at this point X is like 'sin' or 'cos' so pop the name and call the button function
                    function = self._stack.pop(0) # the button functions expect the argument in X not the name
                    try:
                        self._button_functions[function]()
                        return  # ------------------------------------------------------------------------------------->
                    except Exception as ex:
                        self._message = f"Error in enter_press: function: '{function}' failed with: {ex}"
                        self.stack_put(function)

                # it failed to exe the button try the imported functions this is the case for something like 'sin'
                # it is a button but also in the imported methods for numpy

                # at this point X is like 'sin' or 'cos' so pop the name and call the math function
                function = self._stack.pop(0) # the math functions expect the argument in X not the name

                args=[]
                if x_str in self._user_functions:
                    try:
                        sig = inspect.signature(eval(function, self._exec_globals))  # like: <Signature (x, y, z=3)>

                        # not sure how to handle the signatures with kwargs in this context since we are pulling
                        # off the stack. What to do? Should we pull more values off the stack to fill the
                        # kwargs positionally?
                        # that sounds like a very bad idea, lets just ignore the kwargs, if the user needs to call with
                        # kwargs they must enter the entire function like: 'function(x, y, z=3)' into X
                        sig_str = str(sig)
                        sig_list = sig_str.split(',')
                        required_params = [p.replace('(', '') for p in sig_list if '=' not in p]
                        required_args_count = len(required_params)
                        if len(self._stack) < required_args_count:
                            self._message = (f"Error: not enough values on the stack to "
                                             f"perform the operation: '{function}'")
                            self.stack_put(function)
                            return  # -------------------------------------------------------------------------------->
                        args = [self._stack.pop(0) for arg in range(required_args_count)]
                        args = tuple(args)

                        result = eval(x_str, self._exec_globals, )(*args)
                        self._message = f"Evaluated: {x_str}{args} to {result}"
                        self.stack_put(result)
                        self._last_stack_operation = 'function'
                        return  # ----------------------------------------------------------------------------->
                    except Exception as ex:
                        pass  # try the next lib

                # Y = self._stack.pop(0)
                for lib in self._imported_libs:
                    keys = dir(eval(lib))
                    if x_str in keys:
                        try:
                            exc_str = f'{lib}.{x_str}'
                            sig = inspect.signature(eval(exc_str, self._exec_globals))  # like: <Signature (x, y, z=3)>
                            sig_str = str(sig)
                            sig_list = sig_str.split(',')
                            required_params = [p.replace('(', '') for p in sig_list if '=' not in p]
                            required_args_count = len(required_params)
                            if len(self._stack) < required_args_count:
                                self._message = (f"Error: not enough values on the stack to "
                                                 f"perform the operation: '{function}'")
                                self.stack_put(function)
                                return  # ----------------------------------------------------------------------------->
                            args = [self._stack.pop(0) for arg in range(required_args_count)]
                            args = tuple(args)
                            result = eval(exc_str, self._exec_globals, )(args)
                            self._message = f"Evaluated: {exc_str}{args} to {result}"
                            self.stack_put(result)
                            self._last_stack_operation = 'function'
                            return  # --------------------------------------------------------------------------------->
                        except Exception as ex:
                            pass # try the next lib
                # no dice, restore the stack
                for arg in args:
                    self.stack_put(arg)
                self.stack_put(function)

            # .........................................
            #   Handle eval and exec
            # .........................................
            # if you made it this far with no success, try x=eval(x) and failing that exe(x), this is the last try
            x_temp = self._stack.pop(0)

            # first try eval --------------------------
            try:
                result = eval(x_temp, self._exec_globals) # this works on input like 'np.arrange(10)'
                self._message = f"Evaluated: {x_temp} to {result}"
                result_type = type(result)
                result_type_str = str(result_type)

                good = {"<class 'type'>", "<class 'builtin_function_or_method'>", "<class 'function'>"}
                if result_type_str in good:
                    # in this case the user probably wants to apply the builtin functon to Y
                    Y = self._stack.pop(0)
                    try:
                        result = eval(x_temp, self._exec_globals)(Y)  # this works on input like 'np.arrange(Y)'
                        self._message = f"Evaluated: {x_temp}({Y}) to {result}"
                    except Exception as ex:
                        self._message = f"Error in enter_press: eval: '{x_temp}({Y})' with exceptions ex: {ex}"
                        self.stack_put(Y)

                self._last_stack_operation = 'eval'
                self.stack_put(result)

            # next try exec --------------------------
            except Exception as ex:

                if 'import' not in str(x_temp):
                    try:
                        exec(x_temp, self._exec_globals)  # this works on input like 'import os' with no return value
                        self._last_stack_operation = 'exec'
                        self._message = f"Executed: {x_temp}"
                    except Exception as ey:
                        self._message = f"Error in enter_press: exec: '{x_temp}' with exceptions ex: {ex}: ey: {ey}"
                        self.stack_put(x_temp)
                        # todo: set a flag to dup X on enter error, this is a string that cant be parsed ..
                        # but maybe the user wants to use it as a string
                        self._last_stack_operation = 'error'

                # ------- Handle Imports -------
                else: # import is in X, like 'import os', 'from os import path', or 'import numpy as np'
                    try:
                        # figure out what was imported and track all imported functions and libraries
                        imported_name = None
                        imported_lib = None
                        imported_list = x_temp.split(' ')
                        if len(imported_list) == 2:                 # like 'import os'
                            imported_lib = imported_list[1]
                        elif len(imported_list) == 4:
                            if imported_list[3].strip() == '*':  # like 'from os import *'
                                imported_lib = imported_list[1]
                            elif imported_list[2].strip() == 'as':    # like 'import numpy as np'
                                imported_lib = imported_list[3]
                            else:                                  # like 'from os import path' single import
                                imported_name = imported_list[3]

                        if imported_lib is not None:
                            exec(f'{x}', self._exec_globals)  # do the actual import
                            self._message = f"Imported lib: '{imported_lib}'"

                        if imported_name is not None:
                            if imported_name not in self._exec_globals:
                                exec(f'{x}', self._exec_globals)  # do the actual import
                                self._all_functions.add(imported_lib)
                                self._message = f"Imported name: '{imported_name}'"
                            else:
                                self._message = f"Warning: '{imported_name}' already in namespace, did not import."
                    except Exception as ex:
                        self._message = f"Error in enter_press: import: '{x_temp}' with exceptions ex: {ex}"
                        self.stack_put(x_temp)
                        self._last_stack_operation = 'error'

                    # # print all the imported functions
                    # print(f'--------------------------------------------------------------')
                    # print(f"Imported functions count: {len(self._all_functions)}")
                    # for func in self._all_functions:
                    #     print(func)
                    # print(f'--------------------------------------------------------------')


            log(self._message)

    def _duplicate_x_value_in_y_position(self):
        """ duplicates the value in X to Y """
        self._update_stack_history()
        try:
            x_ref = str(self._stack[0])
            if x_ref in self._button_functions:
                x_temp = self._stack.pop(0)
                self.user_entry(x_temp)
            else:
                self.stack_put(self._stack[0])
                self._last_stack_operation = 'enter'
                return  # --------------------------------------------------------------------------------------------->
        except Exception as ex:
            self._message = f"Error in enter_press: copy X to Y: {ex}"

    def stack_operation(self, operation='+'):
        """ performs the operation on the stack X and Y values and puts the result back on the stack
         @param operation: the operation to perform on the two values
         """
        self._update_stack_history()
        self._message = None
        error = None

        if len(self._stack) > 1:
            x_hold = self._stack.pop(0)
            y_hold = self._stack.pop(0)

            try:
                x = x_hold
                y = y_hold
                if isinstance(x_hold, str):
                    x = eval(x_hold, self._exec_globals)
                    if isinstance(x, str):
                        # sometimes when you eval a local var it returns a string, but it should probably be a number in
                        # this context
                        x = eval(x, self._exec_globals)
                if isinstance(y_hold, str):
                    y = eval(y_hold, self._exec_globals)
                    # see note above for X about this second eval
                    if isinstance(y, str):
                        y = eval(y, self._exec_globals)

            except Exception as ex:
                # self._message = f"Function: '+' exception '{ex}' for input x: '{x_hold}' and y: '{y_hold}'"
                # error = True
                # in this case the user might just want to add the string to X, lets try that
                if isinstance(x_hold, str):
                    x = x_hold + operation
                    self.stack_put(y_hold)
                    self.stack_put(x)
                    return # ------------------------------------------------------------------------------------------>

            else:
                try:
                    if operation == '+':
                        result = y + x
                    elif operation == '-':
                        result = y - x
                    elif operation == '*':
                        result = y * x
                    elif operation == '/':
                        if x != 0:
                            result = y / x
                        else:
                            result = float('inf')
                    elif operation == '**':
                        result = y ** x
                    else:
                        self._message = f"Warning in stack operation: unknown operation: '{operation}'"
                        result = None
                        error = True
                except Exception as ex:
                    self._message = f"Error in '{operation}': '{ex}' for input x: '{x}' and y: '{y}'"
                    error = True
                else:
                    self._message = f"Operation: {y} {operation} {x} = {result}"
                    self.stack_put(result)

        else:
            # in this case the user might just want to add the string to X, lets try that
            if len(self._stack) == 1 and isinstance(self._stack[0], str):
                x = self._stack.pop(0)
                x = x + operation
                self.stack_put(x)
                return
            else:
                error = True
                self._message = f"Error: not enough values on the stack to perform an operation: '{operation}')"

        if error is True: # well we tried, restore the stack
            self.stack_put(y_hold)
            self.stack_put(x_hold)
            raise Exception(self._message)

        log(self._message)

    def stack_to_list(self):
        """ converts all items on the stack into a list where X is at list position 0, Y is at list position 1, etc ...
         and puts the list back on the stack at X. Of note, this is python so the list can contain multiple types
        of objects like strings and numbers and other lists, whatever you want. """
        if len(self._stack) > 0:
            self._update_stack_history()
            x = self._stack.pop(0)
            try:
                number = self._convert_to_best_numeric(x)
                self.stack_put(number)
            except ValueError:
                self.stack_put(x)
            self._message = None
            stack_hold = self._stack    # surprise! it's already a list : )
            self.clear_stack()
            if self._setting_invert_lists is True:
                r_stack = list(reversed(stack_hold))
            else:
                r_stack = stack_hold
            self.stack_put(r_stack)
            self._message = f"Stack to list: {r_stack}"

    def stack_to_array(self):
        """ converts all items on the stack into a numpy array where X is at array position 0,
        Y is at array position 1, etc ... and puts the array back on the stack at X.
        Since this is an array, unlike a python list, all items must
        be of the same type, either all strings or all numbers.

        Note: the data type of X will be used first to set the dtype for the array, if that fails then float is used,
        if float fails the native data typs is used, for example if X is a list of strings, the array will be an
        array of lists of strings (like [['1', '2', '3'], ['4', '5', '6']]) """
        if len(self._stack) > 0:
            self._update_stack_history()
            self._message = None
            try:
                number = self._convert_to_best_numeric(self._stack[0])
            except ValueError as ex:
                pass  # whatever is at X, is not a number but that is ok

            stack_hold = self._stack
            r_stack = stack_hold
            if self._setting_invert_lists is True:
                r_stack = list(reversed(stack_hold))

            # look at X data type, we will try to use that as the dtype for the array
            dtype = type(self._stack[0])
            if dtype == str: # since this is a calculator, prefer numbers to strings for arrays
                try:
                    num = self._convert_to_best_numeric(self._stack[0])
                except ValueError:
                    dtype = str
                else:
                    dtype = type(num)
            try:
                array = np.array(reversed, dtype=dtype)
            except Exception as ex:

                try: # try an int
                    int_list = [int(x) for x in r_stack]
                    array = np.array(int_list, dtype=int)

                except Exception as ei:

                    try: # try a float
                        float_list = [float(x) for x in r_stack]
                        array = np.array(float_list, dtype=float)
                    except Exception as ef:

                        try: # try a string
                            string_list = [str(x) for x in r_stack]
                            array = np.array(string_list, dtype=str)
                        except Exception as es:
                            self._message = (f"Error in stack to array, cant convert data type: '{dtype}', to array. "
                                             f"check for homogeneity in the stack: '{[type(x) for x in r_stack]}'"
                                             f"errors: '{ex}', '{ei}', '{ef}', '{es}'")
                            # restore the stack
                            self._stack = stack_hold
                            log(self._message)
                            return # ---------------------------------------------------------------------------------->

            self.clear_stack()
            self.stack_put(array)
            self._message = f"Stack to array: {array}"

    def iterable_to_stack(self):
        """ tries to map an iterable object at X to the stack so [1, 2] would map to x = 1 and y = 2.
        If x is not an iterable object it will be duplicated in on the stack """
        # check if X is an iterable object
        self._update_stack_history()
        try:
            iter(self._stack[0])
        except Exception as ex:
            self._message = f"Error: X is not an iterable object: '{self._stack[0]}', exception: '{ex}'"
            self._duplicate_x_value_in_y_position()
        else:
            x_hold = self._stack.pop(0)
            if self._setting_invert_lists is False:
                x_hold = list(reversed(x_hold))
            for item in x_hold:
                self.stack_put(item)
            self._message = f"Iterable to stack: {x_hold}"

    def return_locals(self):
        """ returns the locals dictionary """
        return self._locals

    def delete_local(self, key):
        """ deletes a local variable by key """
        self._update_stack_history()
        self._message = None
        if key in self._locals:
            val = self._locals.pop(key)
            self._exec_globals.pop(key, None)
            self._message = f"Removed local variable: {key}={val}"
        else:
            self._message = f"Error: cant remove local item: '{key}'"
        log(self._message)

    def clear_stack(self,):
        """ clears the entire stack """
        self._update_stack_history()
        self._message = 'Clear Stack'
        log(self._message)
        self._stack = []

    def clear_user_functions(self, function_name=None):
        """ removes the user functions from the namespace and the user functions set, if function_name is None
        all functions will be removed"""
        if function_name is None:
            to_remove = copy(list(self._user_functions.keys()))
        else:
            to_remove = {function_name}
        for func in to_remove:
            try:
                self._user_functions.pop(func, None)
                self._exec_globals.pop(func, None)
                del func
            except Exception as ex:
                self._message = f"Error: cant remove function: '{func}' with error: '{ex}'"
                log(self._message)
                raise Exception(self._message) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def load_locals(self, new_locals: dict, clear_first=False):
        """ loads a new locals dictionary into the calculator object
        @param new_locals: the new locals dictionary to load
        @param clear_first: if True clear the existing locals dictionary before loading the new one
        """
        self._message = None
        log(f"Load Locals")
        if clear_first:
            self._locals = dict()
        self._locals.update(new_locals)
        self._exec_globals.update(new_locals)

    def delete_last_char(self):
        """ deletes the last char entry on the stack """
        self._message = None
        log(f"Delete Last Stack Entry Char")
        if self._last_stack_operation == 'enter':
            self._stack.pop(0)

        else:
            if len(self._stack) > 0:
                if isinstance(self._stack[0], str):
                    x_temp = self._stack.pop(0) # type: str
                    x_less = x_temp[:-1]
                    self.stack_put(x_less, shift_up=True)
                else:
                    self._message = f"Error: cannot delete last char from non-string: '{self._stack[0]}'"
                    log(self._message)

        self._last_stack_operation = None

    def clear_stack_level(self, idx=0) -> any:
        """ pops the value of the stack at idx, indexing the stack starts at 0.
         @param idx: the stack level (idx) to clear, if idx is out of range, the stack is not cleared """
        self._update_stack_history()
        self._message = None
        log(f"Clear Stack Level: {idx}")
        if idx < len(self._stack):
            return self._stack.pop(idx)
        else:
            self._message = f"Error: cannot clear stack level: '{idx}', it is out of range"
            log(self._message)
            return None

    def clear_all_variables(self):
        """ clears all the local variables """
        self._update_stack_history()
        self._message = None
        log(f"Clear All Variables")
        for key in self._locals.keys():
            self._exec_globals.pop(key, None)
        self._locals = dict()

    def return_stack_for_display(self, index=None):
        """ returns stack items for display
         @param index: if None return the whole stack, if an integer return the stack item at that index or None
         @return: a string copy of the stack or the stack item at the index"""
        if index is None:
            return copy(self._stack)
        else:
            if index < len(self._stack):
                return copy(self._stack[index])
            else:
                return None

    def return_user_functions_for_display(self):
        """ returns a set of all the user defined functions """
        return copy(self._user_functions)

    def return_buttons_for_display(self):
        """ returns a list all the buttons (functions, methods, operations, constants) known to the calculator """
        keys = list(self._button_functions.keys())
        return keys

    def return_user_functions(self) -> dict:
        """ returns a dict of all the user defined functions """
        return self._user_functions

    def return_all_functions(self) -> dict:
        """ returns a dict of all functions known to the calculator. This is dynamic and will include
        all imports and user defined functions """
        return copy(self._exec_globals)

    def return_message(self):
        """ returns the message string """
        return self._message

    def _update_stack_history(self):
        """ this method is used to update the stack history list to prevent memory runaway, copies the current stack
        to the stack history list and pops the oldest stack if the list is longer than 100 (default) items """
        if len(self._stack_history) > self._stack_history_length:
            removed = self._stack_history.pop(0)
            # log(f"Stack history limit of {self._stack_history_length} achieved.")
            # log(f"Removed oldest stack from stack history: {removed}")
        self._stack_history.append(self._stack.copy())

    def _constant_press(self, constant):
        """ puts a constant on the stack. This method is bound to the buttons dictionary for 'pi', 'euler', 'phi', etc
        @param constant: the constant to put on the stack"""
        self._update_stack_history()
        if len(self._stack) == 0:
            self._stack.append(constant)
        else:
            self.stack_put(constant)

    def _print_stack(self):
        """ prints the stack to the console, handy for debugging without the UI """
        len_stack = len(self._stack)
        log(f"stack --------------------------------- {len_stack} items |")
        for item, idx in zip(reversed(self._stack), range(len(self._stack))):
            if isinstance(item, str):
                log(f'{len_stack-idx - 1}: "{item}"')
            else:
                log(f'{len_stack-idx - 1}: {item}')

    @staticmethod
    def _convert_to_best_numeric(x) -> any:
        """ if X is a string, it will try to convert it to a numeric, if the string is '32' it will return an int if
        the string is '32.0' it will return a float. If X is an int or float it will return the same type
        @param x: the value to convert to a number
        @return: the number or raises a ValueError """
        if isinstance(x, str):
            try:
                val = float(x)
                if '.' in str(x) or val < 1:
                    # this is explicitly a float, like 34.0, it can be cast to an int but the user has added the .0
                    return val # -------------------------------------------------------------------------------------->
                else:
                    return int(val)
            except Exception as ex:
                raise ValueError(f"Cannot convert '{x}' to number with error: '{ex}'")
        elif isinstance(x, (int, float)):
            return x
        else:
            raise ValueError(f"Error: convert to best numeric, unknown type for x: '{x}'")

    def add_user_function(self, function_string: str):
        """ adds a user defined function to the calculator object
        @param function_string: the function string to add to the calculator object """
        self._message = None
        try:
            exec(function_string, self._exec_globals)
            # get the name of the function
            function_name = function_string.split(' ')[1].split('(')[0]
            self._user_functions.update({function_name: function_string})
            self._all_functions.add(function_name)
            self._message = f"Added user function: {function_string}"
        except Exception as ex:
            self._message = f"Error: adding user function: '{function_string}' with error: '{ex}'"
            log(self._message)
            raise Exception(self._message)

    def setting_invert_lists(self, invert_lists: bool):
        """ sets the invert lists flag, if True, when using 'stack to list or stack to array' the stack will be
        inverted in the list, so stack[0] will be list[-1] if this setting is True"""
        self._setting_invert_lists = invert_lists


