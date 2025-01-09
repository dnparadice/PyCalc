import inspect
import tkinter as tk
import tkinter.filedialog as filedialog
from tkinter import ttk

from calc import Calculator
import engnum

from copy import copy

import pickle
from enum import Enum
from platform import system as platform_system

try:
    from logger import Logger
    logger = Logger(log_to_console=True)
    log = logger.print_to_console
except ImportError:
    log = print


class OsType(Enum):
    LINUX = 0
    MAC = 1
    WINDOWS = 2
    OTHER = 3


class UiFrame(tk.Frame):
    """ extends the TkFrame class to add a no nonsense flag for indicating if the widget is visible or not in this
    context

    Warning, the coverage for self.visible is not complete, it is only set in the pack, pack_forget, and destroy methods
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.visible = None  # set to True or False to indicate if the widget is visible or not

    def pack_forget(self):
        super().pack_forget()
        self.visible = False

    def destroy(self):
        super().destroy()
        self.visible = False

    def pack(self, **kwargs):
        super().pack(**kwargs)
        self.visible = True


class UiVisibleState(Enum):
    STANDARD = 0
    MINI = 1
    CUSTOM = 2


class CalculatorUiSettings:
    def __init__(self):
        """ the default settings for the calculator

        Note: changing the default settings here will only change the settings at launch if there is no
            last_state_autosave.pycalc file found. To force the settings to change on launch, delete the
            last_state_autosave.pycalc file before launching the calculator.
        """
        self.save_state_on_exit = True
        self.float_format_string = '0.6f'
        self.use_engineering_notation_format = False
        self.eng_format_num_length = 7
        self.integer_format_string = ','
        self.plot_options_string = '-o'
        self.last_user_function_edit_name = None

        # window size and appearance
        self.stack_rows = 2
        self.locals_rows = 10

        self.locals_width_key = 100
        self.locals_width_value = 160

        self.stack_index_width = 20
        self.stack_value_width = 200
        self.stack_type_width = 50
        self.message_width = 30

        self.background_color = 'default'  # set to 'default' or <color>, default matches the system theme

        self.stack_font = ('Arial', 24)
        self.locals_font = ('Arial', 12)
        self.message_font = ('Arial', 12)
        self.button_font = ('Arial', 12)

        self.ui_visible_state = UiVisibleState.STANDARD
        self.show_message_field = False
        self.show_locals_table = False
        self.show_buttons = False


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

        # check the OS type, tkinter has different behavior on different OS's
        sys = platform_system()
        if sys == 'Linux':
            self._os_type = OsType.LINUX
        elif sys == 'Darwin':
            self._os_type = OsType.MAC
        elif sys == 'Windows':
            self._os_type = OsType.WINDOWS
        else: # includes null, '', and Java
            self._os_type = OsType.OTHER

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
        self._top_frame = UiFrame(self._root, background=self._background_color, padx=5, pady=5)
        self._top_frame.pack(fill='x', expand=True)

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

        # EDIT MENU ........................

        # add a 'undo' option to the edit menu
        self._edit_menu.add_command(label='Undo (ctrl+z)', command=self.undo_last_action)

        # add a 'clear stack' option to the edit menu
        self._edit_menu.add_command(label='Clear stack', command=self.clear_stack)

        # add a 'clear all variables' option to the file menu
        self._edit_menu.add_command(label='Clear all variables', command=self.menu_clear_all_variables)

        # VIEW MENU ........................

        # add a 'show user functions' option to the view menu that opens a popup window
        self._view_menu.add_command(label='Show user functions', command=self.popup_show_user_functions)

        # add a 'show all functions' option to the view menu that opens a popup window
        self._view_menu.add_command(label='Show all functions', command=self.popup_show_all_functions)

        # add a seperator line
        self._view_menu.add_separator()

        # add a 'show message field' option to the view menu
        self._tk_var_menu_view_show_message_field = tk.BooleanVar()
        self._view_menu.add_checkbutton(label='Show message field',
                                        onvalue=True,
                                        offvalue=False,
                                        variable=self._tk_var_menu_view_show_message_field,
                                        command=self._menu_view_show_message_field, )

        # add a 'show locals table' option to the view menu
        self._tk_var_menu_view_show_locals_table = tk.BooleanVar()
        self._view_menu.add_checkbutton(label='Show locals table',
                                        onvalue=True,
                                        offvalue=False,
                                        variable=self._tk_var_menu_view_show_locals_table,
                                        command=self._menu_view_show_locals_table, )

        # add a 'show buttons' option to the view menu
        self._tk_var_menu_view_show_buttons = tk.BooleanVar()
        self._view_menu.add_checkbutton(label='Show buttons',
                                        onvalue=True,
                                        offvalue=False,
                                        variable=self._tk_var_menu_view_show_buttons,
                                        command=self._menu_view_show_buttons, )

        # add a seperator
        self._view_menu.add_separator()

        # add a  'Standard View' option to the view menu
        self._view_menu.add_command(label='Standard View', command=self._apply_standard_view)

        # add a 'Mini View' option to the view menu
        self._view_menu.add_command(label='Mini View', command=self._apply_mini_view)

        # OPTIONS MENU ........................

        # add a check option to the menu for 'save state on exit'
        self._options_menu.add_checkbutton(label='Save state on exit', onvalue=True, offvalue=False)

        # add a separator
        self._options_menu.add_separator()

        # add an option to "edit the float format string" that calls the method edit_float_format_string
        self._options_menu.add_command(label='Edit numeric display format', command=self.popup_edit_numeric_display_format)

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

        self._options_menu.add_separator()

        # add option to open the 'function buttons' popup
        self._options_menu.add_command(label='Function buttons', command=self.popup_function_buttons)

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
        self._root.bind('<Command-z>', lambda event: self.undo_last_action())

        # add a binding for save state
        self._root.bind('<Control-s>', lambda event: self.menu_save_state())

        # bind the program exit to the exit method
        self._root.protocol("WM_DELETE_WINDOW", self.user_exit)

        """  ----------------------------  Stack, Messages, Locals, Buttons ---------------------------------------  """

        stack_rows = self._settings.stack_rows
        self._update_visible_ui_object_stack(number_visible_rows=stack_rows)  # sets up the visible UI objects based on the settings

        vis = self._settings.show_message_field
        self._set_visibility_message_field(vis)

        vis = self._settings.show_locals_table
        self._set_visibility_locals_table(vis)

        vis = self._settings.show_buttons
        self._set_visibility_buttons(vis)

        """ ------------------------------------- END __init__() ------------------------------------------------- """

    def _update_visible_ui_object_stack(self, number_visible_rows=6):
        """ updates the visible UI objects based on the settings """
        """   -------------------------------------  STACK ---------------------------------------  """
        exists = hasattr(self, '_frame_stack') # the way this gets called we need to check before creating
        if not exists:
            # create a frame for the stack display
            self._frame_stack = UiFrame(self._top_frame, background=self._background_color, padx=5, pady=5)
            self._frame_stack.pack(fill='x', expand=True)  # fill='x', expand=True

            # add a table with 10 rows and 4 columns named 'index', 'value', 'hex', 'bin' to display the stack
            self._stack_table = ttk.Treeview(self._frame_stack, columns=('value', 'type', ))
            self._stack_table.heading('#0', text='Index')
            self._stack_table.heading('value', text='Value')
            self._stack_table.heading('type', text='Type')
            self._stack_table.pack(fill='x', expand=True)

            # add a graphic line below the stack table
            ttk.Separator(self._frame_stack, orient='horizontal').pack()

        # set table number of visible rows
        if number_visible_rows is not None:
            self._settings.stack_rows = number_visible_rows
        self._stack_table['height'] = self._settings.stack_rows
        self._stack_table.column('#0', width=self._settings.stack_index_width, anchor='w',)
        self._stack_table.column('value', width=self._settings.stack_value_width, anchor='e')
        self._stack_table.column('type', width=self._settings.stack_type_width, anchor=tk.CENTER)

        if self._os_type == OsType.WINDOWS:
            btn = '<Button-3>'
        elif self._os_type == OsType.LINUX or self._os_type == OsType.MAC:
            btn = '<Button-2>'
        else:
            log(f"Error setting right click menu for locals table, unknown OS type: {self._os_type}")
            btn = '<Button-2>'

        # add right click menu to stack
        self._stack_table.bind(btn, self._right_click_menu_stack_table)

        self._update_stack_display()

        log(f"Stack Table column width: {self._stack_table.column('value', 'width')}")

    """ ----------------------------  END __init__ and constructors ----------------------------------------------- """


    @ staticmethod
    def _get_menu_item_by_label( menu: tk.Menu, label: str):
        """ returns a menu item by passing the menu object and the label of the item
        @param menu: tk.Menu, the menu object to search
        @param label: str, the label of the menu item to search for"""
        for item in menu:
            if item.cget('label') == label:
                return item

    def _set_visibility_locals_table(self, state: bool, number_of_visible_rows=10):
        """ sets the visibility of the locals table based on the state """
        if state is True:
            self._settings.show_locals_table = True
            self._tk_var_menu_view_show_locals_table.set(True)
        else:
            self._settings.show_locals_table = False
            self._tk_var_menu_view_show_locals_table.set(False)

        """   -------------------------------------  Locals ---------------------------------------  """

        if self._settings.show_locals_table is True:
            self._view_menu.entryconfig('Show locals table', state='normal')
            # create a frame for the locals display
            self._frame_locals = UiFrame(self._top_frame, background=self._background_color, padx=5, pady=5)
            if self._settings.show_locals_table is True:
                self._frame_locals.pack(fill='x', expand=True)

            # add a table with 10 rows and 2 columns named 'key', 'value', to display the locals
            self._locals_table = ttk.Treeview(self._frame_locals, columns=('value',))

            # set the font for the locals table

            # add gray background to the locals table
            self._locals_table['style'] = 'Treeview'
            self._locals_table.tag_configure('Treeview', background='pink')

            # set table number of visible rows
            if number_of_visible_rows is not None:
                self._settings.locals_rows = number_of_visible_rows
            self._locals_table['height'] = self._settings.locals_rows

            self._locals_table.heading('#0', text='Key', )
            self._locals_table.heading('value', text='Value')
            self._locals_table.column('#0', width=self._settings.locals_width_key)
            self._locals_table.column('value', width=self._settings.locals_width_value)
            self._locals_table.pack(fill='x', expand=True)

            # add a graphic line below the locals table
            ttk.Separator(self._frame_locals, orient='horizontal').pack(fill='x')


            if self._os_type == OsType.WINDOWS:
                btn = '<Button-3>'
            elif self._os_type == OsType.LINUX or self._os_type == OsType.MAC:
                btn = '<Button-2>'
            else:
                log(f"Error setting right click menu for locals table, unknown OS type: {self._os_type}")
                btn = '<Button-2>'

            # add right click menu to locals
            self._locals_table.bind(btn, self._right_click_menu_locals_table)

            self._update_locals_display()

        else:
            exists = hasattr(self, '_frame_locals')
            if exists:
                self._frame_locals.destroy()

    def _right_click_menu_locals_table(self, event):
        """ creates a right click menu for the locals table """
        # create a right click menu
        right_click_menu = tk.Menu(self._root, tearoff=0)
        right_click_menu.add_command(label='Insert value to stack at X', command=self._insert_value_to_stack_at_x)
        right_click_menu.add_command(label='Edit value', command=self._edit_variable_value)

        # add a line seperator to the menu
        right_click_menu.add_separator()
        # add item: "remove selected item"
        right_click_menu.add_command(label='Remove selected item', command=self._remove_selected_item_from_locals_table)
        right_click_menu.post(event.x_root, event.y_root)

    def _right_click_menu_stack_table(self, event):
        """ creates a right click menu for the stack table """
        # create a right click menu
        right_click_menu = tk.Menu(self._root, tearoff=0)
        right_click_menu.add_command(label='Edit value', command=self._edit_stack_value)

        # add a line seperator to the menu
        right_click_menu.add_separator()
        # add item: "remove selected item"
        right_click_menu.add_command(label='Clear Stack', command=self.clear_stack)
        right_click_menu.post(event.x_root, event.y_root)

    def _insert_value_to_stack_at_x(self):
        """ inserts the value of the selected item in the locals table to the stack at X """
        selected = self._locals_table.selection()
        if len(selected) == 0:
            return
        key = self._locals_table.item(selected)['text']
        value = self._locals_table.item(selected)['values'][0]
        self._c.user_entry(value)
        self._update_stack_display()
        self._update_message_display(f"Inserted value at x: {key}={value}")

    def _edit_variable_value(self):
        """ opens a popup window to edit the value of the selected item in the locals table """
        selected = self._locals_table.selection()
        if len(selected) == 0:
            return
        key = self._locals_table.item(selected)['text']
        value = self._locals_table.item(selected)['values'][0]
        self.popup_edit_variable_value(key, value)

    def popup_edit_variable_value(self, key, value):
        """ opens a popup window to edit the value of the selected item in the locals table """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Edit Variable Value')

        # create a label to ask the user to edit the value
        label = ttk.Label(window, text=f'Edit the value for: {key}')
        label.pack()

        # create a text entry field
        entry = ttk.Entry(window)
        entry.insert(0, value)
        # expand with window
        entry.pack(expand=True, fill='x')

        def apply_value():
            new_value = entry.get()
            self._c.user_entry(f"{key}={new_value}")
            self._c.enter_press()
            self._update_message_display()
            self._update_locals_display()
            self._update_stack_display()

            window.destroy()

        # create a button to save the changes
        ttk.Button(window, text='OK', command=apply_value).pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def _remove_selected_item_from_locals_table(self):
        """ removes the selected item from the locals table """
        selected = self._locals_table.selection()
        if len(selected) == 0:
            return
        key = self._locals_table.item(selected)['text']
        value = self._locals_table.item(selected)['values'][0]
        self._c.delete_local(key)
        self._update_locals_display()
        self._update_message_display()

    def _edit_stack_value(self):
        """ opens a popup window to edit the value of the selected item in the stack table """
        selected = self._stack_table.selection()
        if len(selected) == 0:
            return
        key = self._stack_table.item(selected)['text']
        value = self._stack_table.item(selected)['values'][0]
        self.popup_edit_stack_value(key, value)

    def popup_edit_stack_value(self, key, value):
        """ opens a popup window to edit the value of the selected item in the stack table """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Edit Stack Value')

        # create a label to ask the user to edit the value
        label = ttk.Label(window, text=f'Edit the value for: {key}')
        label.pack()

        # create a text entry field
        entry = ttk.Entry(window)
        entry.insert(0, value)
        entry.pack(expand=True, fill='x')

        def apply_value():
            new_value = entry.get()
            # self._c.user_entry(f"{key}={new_value}")
            self._c.clear_stack_level()
            self._c.user_entry(new_value)
            # self._c.enter_press()
            self._update_message_display()
            self._update_locals_display()
            self._update_stack_display()

            window.destroy()

        # bind an enter keypress ro the apply value method
        entry.bind('<Return>', lambda event: apply_value())

        # create a button to save the changes
        ttk.Button(window, text='OK', command=apply_value).pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack()

    def _set_visibility_buttons(self, state: bool):
        """ sets the visibility of the buttons based on the state """

        # ttk buttons ane not the same across OS, need to adjust the width of the buttons
        if self._os_type == OsType.WINDOWS:
            button_width_mod = 4
        elif self._os_type == OsType.LINUX:
            button_width_mod = 2
        elif self._os_type == OsType.MAC:
            button_width_mod = 0  # the original was written on a MAC so the mods are for Windows and Linux
        else:
            button_width_mod = 0

        if state is True:
            self._settings.show_buttons = True
            self._tk_var_menu_view_show_buttons.set(True)
        else:
            self._settings.show_buttons = False
            self._tk_var_menu_view_show_buttons.set(False)

        if self._settings.show_buttons is True:
            bg_color = self._background_color
            self._bottom_button_frame = UiFrame(self._root, background=bg_color, padx=5, pady=5)
            self._bottom_button_frame.pack(fill='x', expand=True)
            self._left_frame = UiFrame(self._bottom_button_frame, width=100, background=bg_color, padx=5, pady=5)
            self._left_frame.pack(side='left')
            self._right_frame = UiFrame(self._bottom_button_frame, width=100, background=bg_color, padx=5, pady=5)
            self._right_frame.pack(side='right')
        else:
            pass # do this at the end of the method too to destroy the buttons

        # Numeric buttons --------------------------------

        # ttk buttons ane not the same across OS, need to adjust the width of the buttons
        if self._os_type == OsType.WINDOWS:
            button_width_mod = 5
        elif self._os_type == OsType.LINUX:
            button_width_mod = 2
        elif self._os_type == OsType.MAC:
            button_width_mod = 0  # the original was written on a MAC so the mods are for Windows and Linux
        else:
            button_width_mod = 0

        if self._settings.show_buttons is True:
            # create a frame for the math buttons
            self._numeric_buttons = UiFrame(self._right_frame, background=self._background_color, padx=5, pady=5)
            numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '+/-']


            # arrange the buttons on a grid in a standard calculator layout
            for i, button in enumerate(numbers):
                ttk.Button(self._numeric_buttons,
                           text=button,
                           command=lambda btn=button: self.button_press(btn),
                           width=2+button_width_mod,
                           ).grid(row=i // 3, column=i % 3,)

            self._numeric_buttons.pack()

        else:
            exists = hasattr(self, '_numeric_buttons')
            if exists:
                self._numeric_buttons.destroy()

        # Calculation Buttons ---------------------------

        if self._settings.show_buttons is True:
            # create a frame for the calc buttons
            self._calc_buttons = UiFrame(self._right_frame, background=self._background_color, padx=5, pady=5)
            calc_buttons = ['delete', 'clear', 'x<->y', '1/x', 'enter', ]
            more_buttons = ['x^2', 'x^y', 'e^x', 'pi', 'euler']

            # arrange the buttons on a grid with the calc buttons on the right and the more buttons on the left
            for i, button in enumerate(more_buttons):
                ttk.Button(self._calc_buttons,
                           text=button,
                           command=lambda btn=button: self.button_press(btn),
                           width=5+button_width_mod,
                           ).grid(row=i, column=0)
            for i, button in enumerate(calc_buttons):
                ttk.Button(self._calc_buttons,
                           text=button,
                           command=lambda btn=button: self.button_press(btn),
                           width=5+button_width_mod,
                           ).grid(row=i, column=1)
            self._calc_buttons.pack()
        else:
            exists = hasattr(self, '_calc_buttons')
            if exists:
                self._calc_buttons.destroy()

        # Operation Buttons ---------------------------

        if self._settings.show_buttons is True:
            # create a frame for operation buttons
            self._operation_buttons = UiFrame(self._left_frame, background=self._background_color, padx=5, pady=5)
            operations = {'sqrt': 'sqrt', 'sin': 'sin', 'cos': 'cos', 'tan': 'tan', 'log': 'log10', 'ln': 'ln', }

            # arrange the buttons on a grid in a standard calculator layout
            indexs = range(len(operations))
            names = operations.keys()
            buttons = operations.values()
            for i, name, button in zip(indexs, names, buttons):
                ttk.Button(self._operation_buttons,
                           text=name,
                           width=3+button_width_mod,
                           command=lambda btn=button: self.button_press(btn),
                           ).grid(row=i // 2, column=i % 2)

            self._operation_buttons.pack()
        else:
            exists = hasattr(self, '_operation_buttons')
            if exists:
                self._operation_buttons.destroy()

        # Special Buttons ---------------------------

        if self._settings.show_buttons is True:
            # create a frame for the special buttons
            self._special_buttons = UiFrame(self._left_frame, background=self._background_color, padx=5, pady=5)
            # place to the right of the numeric buttons

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

            self._special_buttons.pack()
        else:
            exists = hasattr(self, '_special_buttons')
            if exists:
                self._special_buttons.destroy()

        if self._settings.show_buttons is False:
            exists = hasattr(self, '_left_frame')
            if exists:
                self._left_frame.destroy()

            exists = hasattr(self, '_right_frame')
            if exists:
                self._right_frame.destroy()

            exists = hasattr(self, '_bottom_button_frame')
            if exists:
                self._bottom_button_frame.destroy()

    def _set_visibility_message_field(self, state: bool):
        """ sets the visibility of the message field based on the state """
        if state is True:
            # add a field at the bottom for text messages
            self._message_field = tk.Text(self._top_frame, state='normal', height=2, font=self._settings.message_font)
            # set width with settings
            self._message_field.config(width=self._settings.message_width)
            self._message_field.pack(expand=True, fill='x', padx=3)
            self._settings.show_message_field = True
            self._tk_var_menu_view_show_message_field.set(True)
            self._update_message_display()
        else:
            exists = hasattr(self, '_message_field')
            if exists:
                self._message_field.destroy()
            self._settings.show_message_field = False
            self._tk_var_menu_view_show_message_field.set(False)

    def _menu_view_show_message_field(self):
        """ toggles the visibility of the message field """
        self._settings.ui_visible_state = UiVisibleState.CUSTOM
        if self._settings.show_message_field is True:
            self._set_visibility_message_field(False)
        else:
            self._set_visibility_message_field(True)

    def _menu_view_show_locals_table(self):
        """ toggles the visibility of the locals table """
        self._settings.ui_visible_state = UiVisibleState.CUSTOM
        if self._settings.show_locals_table is True:
            self._set_visibility_locals_table(False)
        else:
            self._set_visibility_locals_table(True)

    def _menu_view_show_buttons(self):
        """ toggles the visibility of the buttons """
        self._settings.ui_visible_state = UiVisibleState.CUSTOM
        if self._settings.show_buttons is True:
            self._set_visibility_buttons(False)
        else:
            self._set_visibility_buttons(True)

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
        entry = tk.Text(window, height=25, width=50)
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

    def popup_show_all_functions(self):
        """ opens a popup window to show the all functions available to the calculator """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('All Functions')

        # create a text entry field
        entry = tk.Text(window, height=50, width=75)
        func_dict = self._c.return_all_functions()
        sorted_dict = dict(sorted(func_dict.items()))
        for key, value in sorted_dict.items():
            if '__' not in key:
                try:
                    sig = inspect.signature(value)
                except Exception as ex:
                    sig = '()'
                entry.insert('end',
                             f"{key}{sig}:"
                                    f"\n{value.__doc__}"
                                    f"\n__________________________________________________________________________\n")

        # add scroll bars to the text field
        scroll = tk.Scrollbar(window)
        scroll.pack(side='right', fill='y')
        entry.config(yscrollcommand=scroll.set)
        scroll.config(command=entry.yview)
        entry.pack()

        # add a numeric filed at the bottom of the window that shows the number of functions
        ttk.Label(window, text=f"Number of functions: {len(func_dict)}").pack()

        # create a button to cancel the changes
        ttk.Button(window, text='Close', command=window.destroy).pack()

    def popup_function_buttons(self):
        """ opens a popup window to show the all user functions available to the calculator """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Function Buttons')

        # create a frame for the function buttons
        frame = UiFrame(window, background=self._background_color, padx=5, pady=5)
        frame.pack()

        # create a button for each function
        func_dict = self._c.return_user_functions()
        sorted_dict = dict(sorted(func_dict.items()))
        for key, value in sorted_dict.items():
            if '__' not in key:
                ttk.Button(frame,
                           text=f"{key}",
                           command=lambda btn=key: self._popup_function_button_press(btn),
                           ).pack(fill='x')

        # create a button to cancel the changes
        ttk.Button(window, text='Close', command=window.destroy).pack()

    def _popup_function_button_press(self, function: str):
        """ this method gets bound to the function buttons in the popup window """
        self._c.enter_press()
        self._c.user_entry(function)
        self._c.enter_press()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()

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

    def popup_edit_numeric_display_format(self):
        """ opens a popup window to edit the format of displayed numerics """
        # create a new window
        window = tk.Toplevel(self._root)
        window.title('Edit Float Format String')

        # set visibility vars for the entry field
        if self._settings.use_engineering_notation_format is True:
            state_var = 'disabled'
            read_only_background = 'gray'
        else:
            state_var = 'normal'
            read_only_background = 'white'

        # create a boole variable
        use_eng_notation_tk = tk.IntVar(value=0)
        use_eng_notation_tk = tk.BooleanVar(value=self._settings.use_engineering_notation_format)

        ttk.Label(window, text='Float Format String').pack(padx=10)

        # create a text entry field
        float_entry = ttk.Entry(window, )
        float_entry.insert(0, self._settings.float_format_string)
        float_entry.config(state=state_var, background=read_only_background)
        float_entry.focus()
        float_entry.pack(pady=10)

        # create a line seperator
        ttk.Separator(window, orient='horizontal', ).pack(fill='x', )

        ttk.Label(window, text='Integer Format String').pack(padx=10)

        # create a text entry field
        integer_entry = ttk.Entry(window, )
        integer_entry.insert(0, self._settings.integer_format_string)
        integer_entry.config(state=state_var, background=read_only_background)
        integer_entry.focus()
        integer_entry.pack(pady=10)

        def apply_format_string():
            self._settings.float_format_string = float_entry.get()
            self._settings.integer_format_string = integer_entry.get()
            self._settings.eng_format_num_length = int(eng_num_length.get())
            try:
                self._update_stack_display()
            except Exception as ex:
                message = f"Cant use format string: {self._settings.float_format_string} with error: {ex}"
                self._update_message_display(message)
            else:
                window.destroy()

        def apply_eng_notation():
            self._settings.use_engineering_notation_format = bool(use_eng_notation_tk.get())
            float_entry.delete(0, 'end')
            float_entry.insert(0, self._settings.float_format_string)
            float_entry.config(state='disabled', background='gray') if use_eng_notation_tk.get() else float_entry.config(state='normal', background='white')

            integer_entry.delete(0, 'end')
            integer_entry.insert(0, self._settings.integer_format_string)
            integer_entry.config(state='disabled', background='gray') if use_eng_notation_tk.get() else integer_entry.config(state='normal', background='white')

            eng_num_length.delete(0, 'end')
            eng_num_length.insert(0, str(self._settings.eng_format_num_length))
            eng_num_length.config(state='disabled', background='gray') if not use_eng_notation_tk.get() else eng_num_length.config(state='normal', background='white')

        # create a line seperator
        ttk.Separator(window, orient='horizontal').pack(fill='x', pady=10)

        # create a checkbox to toggle scientific notation
        c_button = ttk.Checkbutton(window, text='Use Engineering Notation', variable=use_eng_notation_tk, onvalue=True, offvalue=False,
                                   command=apply_eng_notation, name='eng_notation')
        c_button.pack()


        # add text below the checkbox that says: 'If use engineering notation is checked, the format string will be ignored'
        ttk.Label(window, text='If Use Engineering Notation is checked, \nthe format strings will be ignored').pack( padx=10)

        ttk.Label(window, text='Number of digits shown in Engineering Format').pack(padx=10)

        # create a numeric field
        eng_num_length = ttk.Entry(window, )
        eng_num_length.insert(0, str(self._settings.eng_format_num_length))
        eng_num_length.config(state='disabled', background='grey') if not self._settings.use_engineering_notation_format else eng_num_length.config(state='normal', background='white')
        eng_num_length.focus()
        eng_num_length.pack(pady=10)

        # create a line seperator
        ttk.Separator(window, orient='horizontal', ).pack(fill='x',)

        # create a button to save the changes, pack right
        ttk.Button(window, text='OK', command=apply_format_string).pack(side='right', pady=10, padx=10)

        # create a button to cancel the changes
        ttk.Button(window, text='Cancel', command=window.destroy).pack(side='left', pady=10, padx=10)

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
        """ deprecated method : functionality moved to Edit Numeric Display Format popup"""
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
        calc_state.functions = self._c.return_user_functions()
        calc_state.settings = copy(self._settings)

        calc_state.settings.stack_value_width = self._stack_table.column('value', 'width')
        calc_state.settings.stack_index_width = self._stack_table.column('#0', 'width')
        calc_state.settings.stack_type_width = self._stack_table.column('type', 'width')

        calc_state.settings.locals_width_key = self._locals_table.column('#0', 'width')
        calc_state.settings.locals_width_value = self._locals_table.column('value', 'width')

        #todo: need to figure out how to get the width to save it.
        calc_state.settings.message_width = 30

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

    def _apply_standard_view(self):

        if self._settings.ui_visible_state != UiVisibleState.STANDARD:
            # first destroy all by setting to false then re-build by setting to true, this resets the UI
            self._set_visibility_message_field(False)
            self._set_visibility_locals_table(False, number_of_visible_rows=6)
            self._set_visibility_buttons(False)

            self._update_visible_ui_object_stack(number_visible_rows=6)
            self._set_visibility_message_field(True)
            self._set_visibility_locals_table(True, number_of_visible_rows=6)
            self._set_visibility_buttons(True)

            self._settings.ui_visible_state = UiVisibleState.STANDARD

    def _apply_mini_view(self):

        if self._settings.ui_visible_state != UiVisibleState.MINI:
            self._update_visible_ui_object_stack(number_visible_rows=2)
            self._set_visibility_message_field(False)
            self._set_visibility_locals_table(False)
            self._set_visibility_buttons(False)
            self._settings.ui_visible_state = UiVisibleState.MINI

    # define a method for updating the stak table
    def _update_stack_display(self):
        # clear the ui table
        self._stack_table.delete(*self._stack_table.get_children())

        for stack_index in range(self._settings.stack_rows).__reversed__():

            stack_entry = self._c.return_stack_for_display(stack_index)
            entry_type = type(stack_entry).__name__

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
                if self._settings.use_engineering_notation_format is True:
                    stack_entry_string = engnum.format_eng(stack_entry, self._settings.eng_format_num_length)
                else:
                    stack_entry_string = f"{stack_entry:{self._settings.float_format_string}}"
            elif isinstance(stack_entry, int):
                if self._settings.use_engineering_notation_format is True:
                    stack_entry_string = engnum.format_eng(stack_entry, self._settings.eng_format_num_length)
                else:
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
                # truncate the displayed stack entry string if it is too long to fit in the table
                if len(stack_entry_string) > desired_width:
                    stack_entry_string = stack_entry_string[:desired_width] + '...'
                    # print(f"truncated stack entry: '{stack_entry_string}' length: {len(stack_entry_string)}")

            # push the stack values to the table
            self._stack_table.insert('',
                                     'end',
                                     text=f"{stack_index}",
                                     values=(stack_entry_string, entry_type))

    def _update_message_display(self, direct_message=None):
        """ updates the message field with the message from the calculator, you
        can pass a message to this method to display a message directly in the UI context

        @param direct_message: str , a message to display in the message field, passing a message
        will override getting the message from the calculator, this is useful for displaying
        UI context messages to the user
        """
        if self._settings.show_message_field is True:
            self._message_field.config(state='normal')
            self._message_field.delete('1.0', 'end')

            if direct_message is not None:
                self._message_field.insert('1.0', direct_message)
            else:
                msg = self._c.return_message()
                if msg is not None:
                    self._message_field.insert('1.0', msg)

            self._message_field.config(state='normal')

    def _update_locals_display(self):
        if self._settings.show_locals_table is True:
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




