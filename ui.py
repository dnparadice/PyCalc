import tkinter as tk
import tkinter.filedialog as filedialog
from tkinter import ttk
from tkinter.ttk import Style
from calc import Calculator
from copy import copy
from struct import pack
import pickle

try:
    from logger import Logger
    logger = Logger(log_to_console=True)
    log = logger.print_to_console
except ImportError:
    log = print


class CalculatorUiSettings:
    def __init__(self):
        """ the default settings for the calculator """
        self.save_state_on_exit = True
        self.float_format_string = '0.6f'
        self.integer_format_string = ','
        self.plot_options_string = '-o'
        self.last_user_function_edit_name = None

        # window size and appearance
        self.stack_rows = 7
        self.locals_rows = 10

        self.locals_width_key = 10
        self.locals_width_value = 260

        self.stack_index_width = 5
        self.stack_value_width = 200
        self.stack_type_width = 50
        self.message_width = 57

        self.background_color = 'default'  # set to 'default' or <color>, default matches the system theme

        self.stack_font = ('Arial', 12)
        self.locals_font = ('Arial', 12)
        self.message_font = ('Arial', 12)
        self.button_font = ('Arial', 12)


class CalculatorUiState:
    def __init__(self):
        self.stack = []
        self.locals = dict()
        self.settings = CalculatorUiSettings()
        self.functions = dict()


class MainWindow:

    def __init__(self, settings: CalculatorUiSettings = None):
        """ creates the main window for the calculator
        @param settings: CalculatorUiSettings, the settings for the calculator UI, passing a value besides None here
        overrides the 'load settings on launch' behavior and uses the passed settings """

        # determine if the system is win, max, or linux because tkinter.ttk needs some help with consistent styling
        # and text size between OS flavors
        # get os name with the os module
        # import os
        # os_name = os.name
        # if os_name == 'nt':
        #     # windows
        #     Style().configure("TButton", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TEntry", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TLabel", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("Treeview", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TFrame", padding=6, relief="flat", font=('Arial', 12))
        # elif os_name == 'posix':
        #     # mac or linux
        #     Style().configure("TButton", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TEntry", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TLabel", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("Treeview", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TFrame", padding=6, relief="flat", font=('Arial', 12))
        # else:
        #     # unknown
        #     Style().configure("TButton", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TEntry", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TLabel", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("Treeview", padding=6, relief="flat", font=('Arial', 12))
        #     Style().configure("TFrame", padding=6, relief="flat", font=('Arial', 12))


        self._autosave_path = 'last_state_autosave.pycalc'
        self._c = Calculator()
        self._root = tk.Tk()
        self._root.title("PyCalc")
        self._settings = CalculatorUiSettings()  # for linting just instantiate this here overwrite if necessary

        # handle the settings
        if settings is None:
            self._load_settings_on_launch()
        else:
            self._settings = settings

        # handle the UI colors
        if self._settings.background_color == 'default':
            self._background_color = self._root.cget('bg')
        else:
            self._background_color = self._settings.background_color

        # apply the color to the root window
        self._root.config(bg=self._background_color)

        # setup the root frames
        self._top_frame = tk.Frame(self._root, background=self._background_color, padx=5, pady=5)
        self._top_frame.pack(fill='x', expand=True)
        self._left_frame = tk.Frame(self._root,  width=100, background=self._background_color, padx=5, pady=5)
        self._left_frame.pack(side='left')
        self._right_frame = tk.Frame(self._root, width=100, background=self._background_color, padx=5, pady=5)
        self._right_frame.pack(side='right')

        """   -------------------------------------  STACK ---------------------------------------  """

        # create a frame for the stack display
        self._frame_stack = tk.Frame(self._top_frame, background=self._background_color, padx=5, pady=5)
        self._frame_stack.pack(fill='x', expand=True) # fill='x', expand=True

        # add a table with 10 rows and 4 columns named 'index', 'value', 'hex', 'bin' to display the stack
        self._stack_table = ttk.Treeview(self._frame_stack, columns=( 'value', 'type',))

        # set table number of visible rows to 10
        self._stack_table['height'] = self._settings.stack_rows

        self._stack_table.heading('#0', text='Index')
        self._stack_table.heading('value', text='Value')
        self._stack_table.heading('type', text='Type')
        self._stack_table.column('#0', width=self._settings.stack_index_width)
        self._stack_table.column('value', width=self._settings.stack_value_width)
        self._stack_table.column('type', width=self._settings.stack_type_width)
        self._stack_table.pack(fill='x', expand=True)

        # add a graphic line below the stack table
        ttk.Separator(self._frame_stack, orient='horizontal').pack()

        """   -------------------------------------  Locals ---------------------------------------  """

        # create a frame for the locals display
        self._frame_locals = tk.Frame(self._top_frame, background=self._background_color, padx=5, pady=5)
        self._frame_locals.pack(fill='x', expand=True)

        # add a table with 10 rows and 2 columns named 'key', 'value', to display the locals
        self._locals_table = ttk.Treeview(self._frame_locals, columns=('value',))

        # set the font for the locals table

        # add gray background to the locals table
        self._locals_table['style'] = 'Treeview'
        self._locals_table.tag_configure('Treeview', background='pink')

        # set table number of visible rows to 10
        self._locals_table['height'] = self._settings.locals_rows

        self._locals_table.heading('#0', text='Key',)
        self._locals_table.heading('value', text='Value')
        self._locals_table.column('#0', width=self._settings.locals_width_key)
        self._locals_table.column('value', width=self._settings.locals_width_value)
        self._locals_table.pack(fill='x', expand=True)

        # add a graphic line below the locals table
        ttk.Separator(self._frame_locals, orient='horizontal').pack(fill='x')

        """   -------------------------------------  BUTTONS ---------------------------------------  """

        # create a frame for the math buttons
        self._numeric_buttons = tk.Frame(self._right_frame, background=self._background_color, padx=5, pady=5)
        self._numeric_buttons.pack()

        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '+/-']

        # arrange the buttons on a grid in a standard calculator layout
        for i, button in enumerate(numbers):
            ttk.Button(self._numeric_buttons,
                       text=button,
                       command=lambda btn=button: self.button_press(btn),
                       width=2,
                       ).grid(row=i//3, column=i%3,)

        # create a frame for the calc buttons
        self._calc_buttons = tk.Frame(self._right_frame, background=self._background_color, padx=5, pady=5)
        self._calc_buttons.pack()

        calc_buttons = ['delete', 'clear', 'X<->Y', '1/X', 'enter', ]

        # arrange the buttons on a grid in a standard calculator layout
        for i, button in enumerate(calc_buttons):
            ttk.Button(self._calc_buttons,
                       text=button,
                       command=lambda btn=button: self.button_press(btn),
                       ).pack(fill='x')

        # create a frame for operation buttons
        self._operation_buttons = tk.Frame(self._left_frame, background=self._background_color, padx=5, pady=5)
        # place to the right of the numeric buttons
        self._operation_buttons.pack()

        operations = {'sqrt': 'sqrt', 'sin': 'sin', 'cos': 'cos', 'tan': 'tan', 'log': 'log10', 'ln': 'ln', }

        # arrange the buttons on a grid in a standard calculator layout
        indexs = range(len(operations))
        names = operations.keys()
        buttons = operations.values()
        for i, name, button in zip(indexs, names, buttons):
            ttk.Button(self._operation_buttons,
                       text=name,
                       width=3,
                       command=lambda btn=button: self.button_press(btn),
                       ).grid(row=i//2, column=i%2)

        # create a frame for the special buttons
        self._special_buttons = tk.Frame(self._left_frame, background=self._background_color, padx=5, pady=5)
        # place to the right of the numeric buttons
        self._special_buttons.pack()

        # create a button for 'stack to list'
        ttk.Button(self._special_buttons,
                     text='stack to list',
                     command=lambda: self.button_press('stack_to_list'),
                     ).pack(fill='x')

        # create a button for 'iterable to stack'
        ttk.Button(self._special_buttons,
                        text='iterable to stack',
                        command=lambda: self.button_press('iterable_to_stack'),
                        ).pack(fill='x')

        # create a button for 'stack to array'
        ttk.Button(self._special_buttons,
                        text='stack to array',
                        command=lambda: self.button_press('stack_to_array'),
                        ).pack(fill='x')

        # create a button for rolling the stack
        ttk.Button(self._special_buttons,
                        text='roll up',
                        command=lambda: self.button_press('roll_up'),
                        ).pack(fill='x')

        # create a button for rolling the stack down
        ttk.Button(self._special_buttons,
                        text='roll down',
                        command=lambda: self.button_press('roll_down'),
                        ).pack(fill='x')

        # create a button for showing a plot
        ttk.Button(self._special_buttons,
                        text='plot',
                        command=lambda: self.show_plot(),
                        ).pack(fill='x')

        """ -------------------------------------  MESSAGE FIELD --------------------------------------- """

        # add a field at the bottom for text messages
        self._message_field = tk.Text(self._top_frame, state='normal', height=2, font=self._settings.message_font)
        # set width with settings
        self._message_field.config(width=self._settings.message_width)

        self._message_field.pack(fill='x')

        """  -------------------------------------  User Menu ---------------------------------------"""

        # create menu bar with a file and options menu
        self._menu_bar = tk.Menu(self._root)
        self._root.config(menu=self._menu_bar)
        self._file_menu = tk.Menu(self._menu_bar)
        self._menu_bar.add_cascade(label='File', menu=self._file_menu)
        self._edit_menu = tk.Menu(self._menu_bar)
        self._menu_bar.add_cascade(label='Edit', menu=self._edit_menu)
        self._view_menu = tk.Menu(self._menu_bar)
        self._menu_bar.add_cascade(label='View', menu=self._view_menu)
        self._options_menu = tk.Menu(self._menu_bar)
        self._menu_bar.add_cascade(label='Options', menu=self._options_menu)

        # FILE MENU ........................

        # add a quit option to the file menu
        self._file_menu.add_command(label='Quit', command=self._root.quit)

        # add a 'load state' option to the file menu
        self._file_menu.add_command(label='Load state', command=self.menu_load_state)

        # add a 'save state' option to the file menu
        self._file_menu.add_command(label='Save state', command=self.menu_save_state)

        # add a 'clear all variables' option to the file menu
        self._file_menu.add_command(label='Clear all variables', command=self.menu_clear_all_variables)

        # EDIT MENU ........................

        # add a 'undo' option to the edit menu
        self._edit_menu.add_command(label='Undo (ctrl+z)', command=self.undo_last_action)

        # VIEW MENU ........................

        # add a 'show user functions' option to the view menu that opens a popup window
        self._view_menu.add_command(label='Show user functions', command=self.popup_show_user_functions)

        # OPTIONS MENU ........................

        # add a check option to the menu for 'save state on exit'
        self._options_menu.add_checkbutton(label='Save state on exit', onvalue=True, offvalue=False)

        # add a separator
        self._options_menu.add_separator()

        # add an option to "edit the float format string" that calls the method edit_float_format_string
        self._options_menu.add_command(label='Edit float format string', command=self.popup_edit_float_format_string)

        # add an option to "edit the integer format string" that calls the method edit_integer_format_string
        self._options_menu.add_command(label='Edit integer format string', command=self.popup_edit_integer_format_string)

        # add an option to "edit the plot options string" that calls the method edit_plot_options_string
        self._options_menu.add_command(label='Edit plot options string', command=self.popup_edit_plot_options_string)

        # add a line separator
        self._options_menu.add_separator()

        # add an option to open the add function popup window that calls the method popup_add_function
        self._options_menu.add_command(label='Add function', command=self.popup_add_function)

        # add an option to 'remove user function' that calls the method remove_user_function
        self._options_menu.add_command(label='Remove function', command=self.popup_remove_user_function)

        # add an option to 'clear all user functions' that calls the method clear_all_user_functions
        self._options_menu.add_command(label='Clear all functions', command=self.popup_confirm_clear_all_user_functions)

        # MENU BINDINGS ........................

        # <none>

        """  -------------------------------------  KEY BINDINGS ---------------------------------------  """

        # bind enter key to  the enter method
        self._root.bind('<Return>', lambda event: self.enter_press())

        # bind the letter keys to the button press methods
        lower_case_letters = [chr(i) for i in range(97, 123)]
        upper_case_letters = [chr(i) for i in range(65, 91)]
        special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '-', '=', '[', ']',
                         '{', '}', '|', '\\', ';', ':', "'", '"', ',', '<', '.', '>', '/', '?', '`', '~']
        numeric_chars = [str(i) for i in range(10)]
        all_chars = lower_case_letters + upper_case_letters + special_chars + numeric_chars
        for char in all_chars:
            try:
                self._root.bind(char, lambda event, ch=char: self.button_press(ch))
            except Exception as ex:
                log(f"Error binding key: {char} to button press method: {ex}")

        # bind the delete button to delete last char method
        self._root.bind('<BackSpace>', lambda event: self.delete_last_char())
        self._root.bind('<Delete>', lambda event: self.delete_last_char())

        # bind the space bar to a space keypress
        self._root.bind('<space>', lambda event: self.button_press(' '))

        # add binding for sift delete to clear stack at X
        self._root.bind('<Shift-BackSpace>', lambda event: self.clear_x())

        # add binding to clear the entire stack, protect with jitsu key combo
        self._root.bind('<Command-Shift-BackSpace>', lambda event: self.clear_stack())

        # add binding for paste from os clipboard
        self._root.bind('<<Paste>>', lambda event: self.paste(self._root.clipboard_get()))

        # add a binding for undo
        self._root.bind('<Control-z>', lambda event: self.undo_last_action())

        # add a binding for save state
        self._root.bind('<Control-s>', lambda event: self.menu_save_state())

        # bind the program exit to the exit method
        self._root.protocol("WM_DELETE_WINDOW", self.user_exit)

        """  --------------------------------------- Do some housekeeping ---------------------------------------  """

        # when the program launches, if the previous state was pulled in the UI needs to update to show the state
        self._update_stack_display()
        self._update_locals_display()
        self._update_message_display()

        """ ------------------------------------- END __init__() ------------------------------------------------- """

    def popup_confirm_clear_all_user_functions(self):
        """ opens a popup window to confirm the user wants to clear all user functions """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Confirm Clear All Functions')

        # create a label to ask the user if they are sure
        label = ttk.Label(window, text='Are you sure you want to clear all user functions?')
        label.pack()

        def clear_all_user_functions():
            self._c.clear_user_functions()
            window.destroy()

        # create a button to confirm the clear all user functions
        ttk.Button(window, text='OK', command=clear_all_user_functions).pack()

        # create a button to cancel the clear all user functions
        ttk.Button(window, text='Cancel', command=window.destroy).pack()
        
    def popup_remove_user_function(self):
        """ popup that has a list of user functions and a button to remove the selected function """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Remove User Function')

        # create a list box to show the user functions
        list_box = tk.Listbox(window, height=10, width=50)
        for key in self._c.return_user_functions().keys():
            list_box.insert('end', key)
        list_box.pack()

        def remove_user_function():
            selected = list_box.curselection()
            if len(selected) == 0:
                return
            key = list_box.get(selected)
            self._c.clear_user_functions(key)
            window.destroy()

        # create a button to remove the selected function
        ttk.Button(window, text='Remove', command=remove_user_function).pack()

        # create a button to cancel the remove function
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def popup_add_function(self, function_string=None, parent_object=None):
        """ opens a popup window to add a function to the calculator """
        # create a new window
        if parent_object is None:
            parent = self._root
        else:
            parent = parent_object
        window = tk.Toplevel(parent)
        window.title('Add Function')

        # create a text entry field
        entry = tk.Text(window, height=5, width=50)
        if function_string is None:
            default_text = 'def sqr_x(x):\n    return x**2'
            txt = self._c.return_user_functions().get(self._settings.last_user_function_edit_name, default_text)
            entry.insert('1.0', txt)
        else:
            entry.insert('1.0', function_string)
        entry.focus()
        entry.pack()

        def apply_function():
            function_string = entry.get('1.0', 'end')
            try:
                self._c.add_user_function(function_string)
            except Exception as ex:
                message = f"Error adding function: {ex}"
                self._update_message_display(message)
            else:
                self._settings.last_user_function_edit_name = function_string.split('(')[0].split(' ')[1]
                window.destroy()

        # create a button to save the changes
        ttk.Button(window, text='OK', command=apply_function).pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def popup_show_user_functions(self):
        """ opens a popup window to show the user defined functions """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('User Functions')

        # create a text entry field
        entry = tk.Text(window, height=42, width=50)
        func_dict = self._c.return_user_functions_for_display()
        for key, value in func_dict.items():
            entry.insert('end', f"Name: '{key}':\n{value}____________________________________________\n")
        entry.pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def _load_settings_on_launch(self):
        """ looks for the settings file 'last_state_autosave' in the local directory and loads it if the user has
         selected to save state on exit """
        try:
            file = open(self._autosave_path, 'rb')
        except FileNotFoundError:
            return  # on a new system or if user never saves this is the expected behavior
        except Exception as ex:
            log(f"Error loading settings on launch: {ex}")
            return
        file_in_b = file.read()
        file.close()
        try:
            calc_state = pickle.loads(file_in_b)    # type: CalculatorUiState
            log(f"loaded settings from file: {self._autosave_path}")

            # only apply settings if the user has selected to save state on exit
            if self._settings.save_state_on_exit is True:
                self._load_calc_state(calc_state)
                log(f"applied settings from file: {self._autosave_path}")
        except Exception as ex:
            self._update_message_display(f"Error loading settings on launch: {ex}")

    def user_exit(self):
        """ exits the program, saves the state if the settings are set to save state on exit """
        if self._settings.save_state_on_exit:
            self.menu_save_state(save_path=self._autosave_path)
            log(f"clean exit")
        self._root.quit()

    def undo_last_action(self):
        self._c.undo_last_action()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    def show_plot(self):
        self._c.show_plot(self._settings.plot_options_string)
        self._update_message_display()
        self._update_stack_display()
        self._update_locals_display()

    def paste(self, value):
        """ handles pasting from the clipboard """
        if isinstance(value, str):
            if '\n' in value: # go ahead and split the string into lines
                lines = value.split('\n')
                tags = {'def', 'class'}
                for tag in tags:
                    if tag in lines[0]:
                        for line in lines:
                            self.button_press(str(line))
                        self.enter_press()
                        break
                else:  # tag not found
                    self.button_press(str(lines))
                    self.enter_press()

            else:
                self.button_press(str(value))

        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    def popup_edit_float_format_string(self):
        """ opens a popup window to edit the float format string, has the buttons 'ok' and 'cancel' """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Edit Float Format String')

        # create a text entry field
        entry = ttk.Entry(window)
        entry.insert(0, self._settings.float_format_string)
        entry.focus()
        entry.pack()

        def apply_float_format_string():
            self._settings.float_format_string = entry.get()
            try:
                self._update_stack_display()
            except Exception as ex:
                message = f"Cant use format string: {self._settings.float_format_string} with error: {ex}"
                self._update_message_display(message)
            else:
                window.destroy()

        # create a button to save the changes
        ttk.Button(window, text='OK', command=apply_float_format_string).pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def popup_edit_plot_options_string(self):
        """ opens a popup window to edit the plot options string, has the buttons 'ok' and 'cancel' """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Edit Plot Options String')

        # create a text entry field
        entry = ttk.Entry(window)
        entry.insert(0, self._settings.plot_options_string)
        entry.focus()
        entry.pack()

        def apply_plot_options_string():
            self._settings.plot_options_string = entry.get()
            try:
                self._update_stack_display()
            except Exception as ex:
                message = f"Cant use plot options string: {self._settings.plot_options_string} with error: {ex}"
                self._update_message_display(message)
            else:
                window.destroy()

        # create a button to save the changes
        ttk.Button(window, text='OK', command=apply_plot_options_string).pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def popup_edit_integer_format_string(self):
        """ opens a popup window to edit the integer format string, has the buttons 'ok' and 'cancel' """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Edit Integer Format String')

        # create a text entry field
        entry = ttk.Entry(window)
        entry.insert(0, self._settings.integer_format_string)
        # make the focus be on the entry field
        entry.focus()
        entry.pack()

        def apply_integer_format_string():
            self._settings.integer_format_string = entry.get()
            try:
                self._update_stack_display()
            except Exception as ex:
                message = f"Cant use format string: {self._settings.integer_format_string} with error: {ex}"
                self._update_message_display(message)
            else:
                window.destroy()

        # create a button to save the changes
        ttk.Button(window, text='OK', command=apply_integer_format_string).pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def _apply_ui_settings(self, settings: CalculatorUiSettings):
        """ applies the settings to the ui """
        # todo : this needs work, when called on launch the objects dont exist yet, need to change the order of operations
        msg = f"Apply Settings on a live window is not implemented yet"
        log(msg)

    def menu_save_state(self, save_path=None):
        """ saves the locals stack and settings to a file of the users choice
         @param save_path: str, the path to save the state to, if None a file dialog will be opened
         """
        # open a file dialog to save the state
        file_extension = ".pycalc"
        if save_path is None:
            file = filedialog.asksaveasfile(mode='wb', defaultextension=file_extension)
            if file is None:
                return
        else:
            if not save_path.endswith(file_extension):
                save_path += file_extension
            file = open(save_path, 'wb')
        calc_state = CalculatorUiState()
        calc_state.stack = self._c.return_stack_for_display()
        calc_state.locals = self._c.return_locals()
        calc_state.settings = copy(self._settings)
        calc_state.functions = self._c.return_user_functions()
        pkl_dump = pickle.dumps(calc_state)
        file.write(pkl_dump)
        file.close()
        log(f"saved state to file: {save_path}")

    def menu_load_state(self):
        """ loads the settings and state from a file of the users choice """
        # open a file dialog to load the state
        try:
            file = filedialog.askopenfile(mode='rb', defaultextension=".pycalc")
            if file is None:
                return
            bytes = file.read()
            file.close()
            calc_state = pickle.loads(bytes)    # type: CalculatorUiState
            self._load_calc_state(calc_state)
            self._update_locals_display()
            self._update_stack_display()
            self._update_message_display()
        except Exception as ex:
            self._update_message_display(f"Error loading state: {ex}")

    def _load_calc_state(self, calc_state: CalculatorUiState):
        if calc_state.settings is not None:
            self._c.load_locals(calc_state.locals, True)
            log(f"loaded locals: {calc_state.locals}")
        if calc_state.stack is not None:
            for item in reversed(calc_state.stack):
                self._c.user_entry(item)
            log(f"loaded stack: {calc_state.stack}")
        if calc_state.settings is not None:
            # need to handle new items were added to the settings class
            incoming = calc_state.settings
            latest = self._settings
            dif = set(vars(incoming)) ^ set(vars(latest))
            for key in dif:
                setattr(incoming, key, getattr(latest, key))

            self._settings = incoming
            self._apply_ui_settings(self._settings)
            log(f"loaded settings: {calc_state.settings}")
        try:
            if calc_state.functions is not None:
                for key, value in calc_state.functions.items():
                    self._c.add_user_function(value)
        except Exception as ex:
            pass # older versions of the calc state class did not have functions

        # note: you cant update the UI here because this method is called before all UI objects are created

    def menu_clear_all_variables(self):
        self._c.clear_all_variables()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    def clear_stack(self):
        self._c.clear_stack()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    def clear_x(self):
        self._c.clear_stack_level(0)
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    def delete_last_char(self):
        self._c.delete_last_char()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    def enter_press(self):
        msg = self._c.enter_press()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()
        # change focus to the stack table
        self._stack_table.focus_set()

    # define a method for button pushes that take a string as an argument and calls self._c.user_entry
    def button_press(self, input: str):
        self._c.user_entry(input)
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

    # define a method for updating the stak table
    def _update_stack_display(self):
        # clear the ui table
        self._stack_table.delete(*self._stack_table.get_children())

        for stack_index in range(self._settings.stack_rows).__reversed__():

            stack_entry = self._c.return_stack_for_display(stack_index)
            entry_type = type(stack_entry)

            # having number, hex and binary output simultaneously was fun but not very useful, keep for "developer" mode
            # try:
            #     hex_val = hex(int(stack_entry))
            # except Exception as ex:
            #     try:
            #         hex_val = pack('d', float(stack_entry)).hex()
            #     except Exception as ex:
            #         hex_val = None
            # try:
            #     bin_val = bin(int(stack_entry))
            # except Exception as ex:
            #     try:
            #         bin_val = bin(int(pack('d', float(stack_entry)).hex()))
            #     except Exception as ex:
            #         bin_val = None

            # apply user formatting to numeric types
            if isinstance(stack_entry, float):
                stack_entry_string = f"{stack_entry:{self._settings.float_format_string}}"

            elif isinstance(stack_entry, int):
                stack_entry_string = f"{stack_entry:{self._settings.integer_format_string}}"

            # handle the case where the stack entry is None
            elif stack_entry is None:
                stack_entry_string = ''
                entry_type = ''
                # hex_val = ''
                # bin_val = ''

            else:
                desired_width = self._settings.stack_value_width
                stack_entry_string = str(stack_entry)
                if len(stack_entry_string) > desired_width:
                    stack_entry_string = stack_entry_string[:desired_width] + '...'
                    print(f"truncated stack entry: '{stack_entry_string}' length: {len(stack_entry_string)}")

            # push the stack values to the table
            self._stack_table.insert('',
                                     'end',
                                     text=f"{stack_index}",
                                     values=(stack_entry_string, entry_type))

    def _update_message_display(self, direct_message=None):
        """ updates the message field with the message from the calculator, you
        can pass a message to this method to display a message directly in the UI context

        @param direct_message: str , a message to display in the message field, passing a message
        will override getting the message from the calculator, this is usefull for displaying
        UI context messages to the user
        """
        self._message_field.config(state='normal')
        self._message_field.delete('1.0', 'end')

        if direct_message is not None:
            self._message_field.insert(direct_message)
        else:
            msg = self._c.return_message()
            if msg is not None:
                self._message_field.insert('1.0', msg)

        self._message_field.config(state='normal')

    def _update_locals_display(self):
        # clear the ui table
        self._locals_table.delete(*self._locals_table.get_children())

        for key, value in self._c.return_locals().items():
            formatted_value = str(value)
            # log(f"update locals:: key: {key}, value: {formatted_value}")
            self._locals_table.insert('',
                                         'end',
                                         text=key,
                                         value=(formatted_value,),
                                     )
    def launch_ui(self):
        """ launches the main window by calling the Tk mainloop method """
        self._root.mainloop()







