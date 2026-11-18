import ast
import inspect
import subprocess
import sys
import tkinter as tk
from locale import currency
from tkinter import font as tkfont
import tkinter.filedialog as filedialog
import pathlib
from tkinter import ttk
from tkinter.ttk import Style
import numpy as np
import struct
import re

from calc import Calculator
import engnum
import hidpi
import plots

from copy import copy
from struct import pack
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
    """ extends the UiFrame class to add a no nonsense flag for indicating if the widget is visible or not in this
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

        # window size and appearance
        self.stack_rows = 5
        self.locals_rows = 6

        self.locals_width_key = 100
        self.locals_width_value = 160

        self.stack_index_width = 20
        self.stack_value_width = 200
        self.stack_type_width = 50
        self.message_width = 30
        self.message_height = 5

        self.background_color = 'default'  # set to 'default' or <color>, default matches the system theme

        # fonts are (family, size). The stack, locals and message fonts are kept equal and drive the data font,
        # button_font drives the buttons and table headings, and ui_font drives everything else (menus, labels,
        # entry fields, lists and popups). For ui_font the family 'Default' and the size None keep the system font.
        self.stack_font = ('Default', 15)
        self.locals_font = ('Default', 15)
        self.message_font = ('Default', 15)
        self.button_font = ('Default', 12)
        self.ui_font = ('Default', None)

        self.ui_visible_state = UiVisibleState.STANDARD
        self.show_message_field = True
        self.show_locals_table = True
        self.show_buttons = True
        self.load_on_launch = ['calclibs.eemath']  # list of python modules to load on launch


class CalculatorUiState:
    def __init__(self):
        self.stack = []
        self.locals = dict()
        self.settings = CalculatorUiSettings()
        self.functions = dict()


class MainWindow:

    def __init__(self, settings: CalculatorUiSettings = None, root=None):
        """ creates the main window for the calculator
        @param settings: CalculatorUiSettings, the settings for the calculator UI, passing a value besides None here
        overrides the 'load settings on launch' behavior and uses the passed settings """

        # check the OS type, tkinter has different behavior on different OS's
        os_name = platform_system()
        if os_name == 'Linux':
            self._os_type = OsType.LINUX
        elif os_name == 'Darwin':
            self._os_type = OsType.MAC
        elif os_name == 'Windows':
            self._os_type = OsType.WINDOWS
        else: # includes null, '', and Java
            self._os_type = OsType.OTHER

        self._autosave_path = 'last_state_autosave.pycalc'
        self._c = Calculator()
        if root is None:
            hidpi.enable()  # must run before the first window is created, main.py does this for its own root
            root = tk.Tk()
        self._root = root
        self._root.title("PyCalc")

        # sizes in this file are written in design pixels (pixels on a 96 DPI display), _px() converts them to the
        # pixels of this display. The three gaps are the only spacings used between elements in any window.
        self._ui_scale = self._get_ui_scale()
        self._gap_s = self._px(4)    # between elements that belong together, like a label and its field
        self._gap_m = self._px(8)    # between groups of elements
        self._gap_l = self._px(12)   # the margin around the content of a popup
        # PyInstaller places bundled data under _MEIPASS; source runs use media/.
        if getattr(sys, 'frozen', False):
            icon_path = pathlib.Path(sys._MEIPASS) / 'resources' / 'pycalc_icon_a.png'
        else:
            icon_path = pathlib.Path(__file__).resolve().parent / 'media' / 'pycalc_icon_a.png'
        try:
            self._icon_image = tk.PhotoImage(master=self._root, file=str(icon_path))
            self._root.iconphoto(True, self._icon_image)
        except (tk.TclError, OSError) as exc:
            log(f'Unable to load application icon {icon_path}: {exc}')
        self._settings = CalculatorUiSettings()  # for linting just instantiate this here overwrite if necessary

        # handle the settings
        if settings is None:
            self._load_settings_on_launch()
        else:
            self._settings = settings

        # pick the widget theme, then create the named fonts and apply the font settings, before any widget or menu
        # is created
        self._init_theme()
        self._init_fonts()

        # handle the UI colors
        if self._settings.background_color == 'default':
            self._background_color = self._root.cget('bg')
        else:
            self._background_color = self._settings.background_color

        # apply the color to the root window
        self._root.config(bg=self._background_color)

        # the main window is one column: the stack, the message field, the locals table and the buttons each have a
        # fixed row in it, so they share the same left and right edge and keep their order when one is hidden and
        # shown again. A section that is not visible leaves no gap.
        self._top_frame = UiFrame(self._root, background=self._background_color, padx=self._gap_m, pady=self._gap_m)
        self._top_frame.pack(fill='both', expand=True)
        self._top_frame.columnconfigure(0, weight=1)

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
        self._plot_menu = tk.Menu(self._menu_bar)
        self._menu_bar.add_cascade(label='Plot', menu=self._plot_menu)
        self._function_menu = tk.Menu(self._menu_bar)
        self._menu_bar.add_cascade(label='Functions', menu=self._function_menu)

        # FILE MENU ........................

        self._file_menu.add_command(label='Quit', command=self.user_exit)
        self._file_menu.add_command(label='Load state', command=self.menu_load_state)
        self._file_menu.add_command(label='Save state', command=self.menu_save_state)
        self._file_menu.add_checkbutton(label='Save state on exit', onvalue=True, offvalue=False)
        self._file_menu.add_separator()
        self._file_menu.add_command(label='Load Python Module', command=self.popup_load_python_module)

        # EDIT MENU ........................

        self._edit_menu.add_command(label='Copy (ctrl+c)', command=self.copy_stack_value)
        self._edit_menu.add_command(label='Paste (ctrl+v)', command=self._paste_wrapper_no_args)
        self._edit_menu.add_separator()
        self._edit_menu.add_command(label='Undo (ctrl+z)', command=self.undo_last_action)
        self._edit_menu.add_command(label='Clear stack', command=self.clear_stack)
        self._edit_menu.add_separator()
        self._edit_menu.add_command(label='Clear all variables', command=self.menu_clear_all_variables)

        # VIEW MENU ........................

        self._tk_var_menu_view_show_message_field = tk.BooleanVar()
        self._view_menu.add_checkbutton(label='Show message field',
                                        onvalue=True,
                                        offvalue=False,
                                        variable=self._tk_var_menu_view_show_message_field,
                                        command=self._menu_view_show_message_field, )

        self._tk_var_menu_view_show_locals_table = tk.BooleanVar()
        self._view_menu.add_checkbutton(label='Show locals table',
                                        onvalue=True,
                                        offvalue=False,
                                        variable=self._tk_var_menu_view_show_locals_table,
                                        command=self._menu_view_show_locals_table, )

        self._tk_var_menu_view_show_buttons = tk.BooleanVar()
        self._view_menu.add_checkbutton(label='Show buttons',
                                        onvalue=True,
                                        offvalue=False,
                                        variable=self._tk_var_menu_view_show_buttons,
                                        command=self._menu_view_show_buttons, )

        self._view_menu.add_separator()
        self._view_menu.add_command(label='Standard View', command=self._apply_standard_view)
        self._view_menu.add_command(label='Mini View', command=self._apply_mini_view)
        self._view_menu.add_separator()
        self._view_menu.add_command(label='Set number of visible rows', command=self.popup_set_stack_message_vars_height)
        self._view_menu.add_command(label='Set font parameters', command=self.popup_set_stack_font_parameters)
        self._view_menu.add_separator()
        self._view_menu.add_command(label='Edit numeric display format', command=self.popup_edit_numeric_display_format)

        # PLOT MENU ............................

        self._plot_menu.add_command(label='Plot', command=self.popup_x_plot)
        self._plot_menu.add_command(label='XY Plot', command=self.popup_xy_plot)
        self._plot_menu.add_command(label='XYZ Plot', command=self.popup_xyz_plot)
        self._plot_menu.add_separator()
        self._plot_menu.add_command(label='Create Arrays', command=self.popup_create_array)
        self._plot_menu.add_separator()
        self._plot_menu.add_command(label='Edit plot options string', command=self.popup_edit_plot_options_string)

        # Function MENU ............................

        self._function_menu.add_command(label='Edit user functions', command=self.popup_edit_user_function)
        self._function_menu.add_separator()
        self._function_menu.add_command(label='Show user function buttons', command=self.popup_function_buttons)
        self._function_menu.add_separator()
        self._function_menu.add_command(label='Clear all user functions', command=self.popup_confirm_clear_all_user_functions)
        self._function_menu.add_separator()
        self._function_menu.add_command(label='Show all functions', command=self.popup_show_all_functions)
        self._function_menu.add_separator()

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

        # bind double click on locals to insert value to stack at x
        self._root.bind('<Double-1>', lambda event: self._insert_value_to_stack_at_x())

        # bind the program exit to the exit method
        self._root.protocol("WM_DELETE_WINDOW", self.user_exit)

        if self._os_type == OsType.MAC:
            self._root.bind('<Command-c>', lambda event: self.copy_stack_value())
            self._root.bind('<Command-z>', lambda event: self.undo_last_action())
            self._root.bind('<Command-s>', lambda event: self.menu_save_state())
        else: # Windows and other
            self._root.bind('<Control-c>', lambda event: self.copy_stack_value())
            self._root.bind('<Control-z>', lambda event: self.undo_last_action())
            self._root.bind('<Control-s>', lambda event: self.menu_save_state())

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
            self._frame_stack = UiFrame(self._top_frame, background=self._background_color)
            self._frame_stack.grid(row=self._ROW_STACK, column=0, sticky='nsew')

            # add a table with (n) rows and 4 columns named 'index', 'value', 'hex', 'bin' to display the stack
            # self._stack_table = ttk.Treeview(self._frame_stack, columns=('value', 'type', ))
            self._stack_table = ttk.Treeview(self._frame_stack, columns=('type', 'value', ))
            self._stack_table.heading('#0', text='Index')
            self._stack_table.heading('type', text='Type')
            self._stack_table.heading('value', text='Stack Values')
            self._stack_table.pack(fill='both', expand=True)

            # add right click menu to stack
            self._bind_right_click(self._stack_table, self._right_click_menu_stack_table)

        # set table number of visible rows
        if number_visible_rows is not None:
            self._settings.stack_rows = number_visible_rows
        self._stack_table['height'] = self._settings.stack_rows
        self._stack_table.column('#0', width=self._px(self._settings.stack_index_width), anchor='w',)
        self._stack_table.column('value', width=self._px(self._settings.stack_value_width), anchor='e')
        self._stack_table.column('type', width=self._px(self._settings.stack_type_width), anchor=tk.CENTER)

        # note: the style of ALL Treeview objects (font and row height) is set in _apply_fonts()

        # re-size window to fit all visible elements
        self.re_draw_main_window_to_fit_all_elements()

        self._update_stack_display()

    def re_draw_main_window_to_fit_all_elements(self):
        """ re-draws the main window to fit all visible elements """
        self._update_resize_row()
        self._root.update_idletasks()
        self._root.geometry('')  # set to empty string to auto-size to fit all elements

    # -------------------------------------  Layout ---------------------------------------

    # the rows of the main window, see self._top_frame
    _ROW_STACK = 0
    _ROW_MESSAGE = 1
    _ROW_LOCALS = 2
    _ROW_BUTTONS = 3

    def _get_ui_scale(self) -> float:
        """ returns the factor from design pixels (pixels on a 96 DPI display) to the pixels of this display, like
        1.5 on a Windows display set to 150%. macOS scales the whole window itself, so the factor there is 1 """
        try:
            if self._root.tk.call('tk', 'windowingsystem') == 'aqua':
                return 1.0
            return max(1.0, self._root.winfo_fpixels('1i') / 96.0)
        except tk.TclError:
            return 1.0

    def _px(self, design_pixels) -> int:
        """ converts design pixels to the pixels of this display. Use for every padding, width and height that is
        not counted in characters or text lines, those follow the font on their own """
        return int(round(design_pixels * self._ui_scale))

    def _update_resize_row(self):
        """ makes one section of the main window take the extra height when the window is made taller: the locals
        table if it is visible, else the message field, else the stack. The buttons never stretch """
        if not hasattr(self, '_top_frame'):
            return
        if self._settings.show_locals_table is True:
            resize_row = self._ROW_LOCALS
        elif self._settings.show_message_field is True:
            resize_row = self._ROW_MESSAGE
        else:
            resize_row = self._ROW_STACK
        for row in (self._ROW_STACK, self._ROW_MESSAGE, self._ROW_LOCALS, self._ROW_BUTTONS):
            self._top_frame.rowconfigure(row, weight=1 if row == resize_row else 0)

    def _bind_right_click(self, widget, callback):
        """ binds the callback to the right mouse button, which has a different number on each system """
        if self._os_type == OsType.MAC:
            # the right button is 2 up to Tk 8.6 and 3 from Tk 8.7
            widget.bind('<Button-2>', callback)
            widget.bind('<Button-3>', callback)
        else:  # Windows and Linux, on Linux button 2 is the middle button
            widget.bind('<Button-3>', callback)

    def _init_theme(self):
        """ selects the widget theme. Windows and macOS have a native theme that is used as is, on Linux the default
        theme is the oldest looking one, so 'clam' is used when it is available """
        try:
            style = ttk.Style(self._root)
            if self._root.tk.call('tk', 'windowingsystem') == 'x11':
                if 'clam' in style.theme_names():
                    style.theme_use('clam')
            if self._os_type == OsType.WINDOWS:
                # the Windows theme leaves no room between the text and the edge of a button, add some for the
                # buttons of the popups. The calculator keys keep the tight fit, their size comes from the grid.
                style.configure('TButton', padding=(self._px(6), self._px(1)))
                style.configure('Key.TButton', padding=1)
        except tk.TclError as ex:
            log(f"Error selecting the widget theme: {ex}")

    def _border_color(self) -> str:
        """ returns the color of the line around a table in the current theme, used to give the message field the
        same border as the tables above and below it """
        colors = {OsType.WINDOWS: '#828790', OsType.MAC: '#c5c5c5', OsType.LINUX: '#9e9a91'}
        return colors.get(self._os_type, '#828790')

    def _flat_border(self, widget):
        """ gives a tk Text or Listbox the flat one line border of the themed tables and entry fields, in place of
        its own sunken border. Returns the widget. """
        color = self._border_color()
        widget.config(relief='flat', borderwidth=0, highlightthickness=1,
                      highlightbackground=color, highlightcolor=color)
        return widget

    # -------------------------------------  Fonts ---------------------------------------

    # Tk's own named fonts. Every widget that is not given a font uses one of these, so configuring them restyles
    # the menus, labels, entry fields, lists and popups, including the ones already on screen.
    _SYSTEM_FONT_NAMES = ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont', 'TkFixedFont',
                          'TkCaptionFont', 'TkSmallCaptionFont', 'TkIconFont', 'TkTooltipFont')

    def _init_fonts(self):
        """ creates the named fonts used by the UI and applies the font settings to them. Call once, before any
        widget is created.

        All fonts in the UI come from named fonts so that a font change is one call to _apply_fonts() and reaches
        every widget without re-building it:
            PyCalcDataFont   -- the stack, locals and array tables and the message field (settings.stack_font)
            PyCalcButtonFont -- the buttons and the table headings (settings.button_font)
            Tk's named fonts -- everything else (settings.ui_font)
        """
        existing = tkfont.names(self._root)

        # remember the system fonts before they are touched, 'Default' in the settings restores these
        self._system_fonts = dict()
        for name in self._SYSTEM_FONT_NAMES:
            if name in existing:
                actual = tkfont.nametofont(name, root=self._root).actual()
                self._system_fonts.update({name: (actual['family'], actual['size'])})

        self._data_font = self._get_named_font('PyCalcDataFont')
        self._button_font = self._get_named_font('PyCalcButtonFont')

        # a menu holds a copy of the system menu font unless it is told to use the named font
        self._root.option_add('*Menu.font', 'TkMenuFont')

        self._apply_fonts()

    def _get_named_font(self, name: str) -> tkfont.Font:
        """ returns the named font, creates it if it does not exist yet """
        if name in tkfont.names(self._root):
            return tkfont.nametofont(name, root=self._root)
        return tkfont.Font(root=self._root, name=name, exists=False)

    def _system_ui_font_size(self) -> int:
        """ returns the size of the system font used by the labels and entry fields """
        return self._system_fonts.get('TkDefaultFont', ('', 10))[1]

    @staticmethod
    def _font_setting(setting, default_size):
        """ returns (family, size) from a font setting like ('Courier New', 19), tolerant of a malformed setting """
        try:
            family = str(setting[0])
            size = setting[1]
            size = default_size if size is None else int(size)
        except (TypeError, IndexError, ValueError):
            family, size = 'Default', default_size
        return family, size

    def _apply_fonts(self):
        """ applies the font settings to the named fonts, this updates every font in the UI in place """
        family, size = self._font_setting(self._settings.stack_font, 15)
        self._data_font.configure(family=family, size=size, weight='normal', slant='roman')

        family, size = self._font_setting(self._settings.button_font, 12)
        self._button_font.configure(family=family, size=size, weight='normal', slant='roman')

        # older settings objects do not have ui_font
        ui_family, ui_size = self._font_setting(getattr(self._settings, 'ui_font', None), None)
        for name, (system_family, system_size) in self._system_fonts.items():
            # the fixed font is used for python code, it keeps its monospaced family and follows the size only
            keep_family = ui_family == 'Default' or name == 'TkFixedFont'
            tkfont.nametofont(name, root=self._root).configure(
                family=system_family if keep_family else ui_family,
                size=system_size if ui_size is None else ui_size)

        # these styles affect ALL Treeview objects and ALL calculator keys. 'Key.TButton' is the style of the keys
        # of the calculator, the buttons of the popups (OK, Cancel, ...) keep the plain 'TButton' style and with it
        # the font of the labels beside them
        style = ttk.Style(self._root)
        style.configure('Treeview', font=self._data_font)
        style.configure('Treeview', rowheight=self._data_font.metrics('linespace'))  # row height from the real font
        style.configure('Treeview.Heading', font=self._button_font)
        style.configure('Key.TButton', font=self._button_font, width=-2)  # no wider than the label needs

        # a table stretches its columns when the window grows and does not give the width back, return the columns
        # to their set widths so the window can shrink again when the font gets smaller
        self._reset_table_column_widths()

        # re-size window to fit all visible elements
        self.re_draw_main_window_to_fit_all_elements()

    def _reset_table_column_widths(self):
        """ sets the columns of the stack and locals tables to the widths in the settings """
        try:
            if hasattr(self, '_stack_table') and self._stack_table.winfo_exists():
                self._stack_table.column('#0', width=self._px(self._settings.stack_index_width))
                self._stack_table.column('value', width=self._px(self._settings.stack_value_width))
                self._stack_table.column('type', width=self._px(self._settings.stack_type_width))
            if hasattr(self, '_locals_table') and self._locals_table.winfo_exists():
                self._locals_table.column('#0', width=self._px(self._settings.locals_width_key))
                self._locals_table.column('value', width=self._px(self._settings.locals_width_value))
        except tk.TclError as ex:
            log(f"Error setting table column widths: {ex}")

    # -------------------------------------  Popup windows ---------------------------------------

    def _new_popup(self, title: str, dialog: bool = True):
        """ creates a popup window, every popup of the calculator is made here so they all look and behave the same.
        Returns (window, body), put all the widgets in body.

        :param title: the title of the window
        :param dialog: True for a small window that asks for a few values: it has a fixed size, stays above the main
            window and closes on the Escape key. False for a tool window that can be re-sized and maximized.

        The window fits its content, so it is never given a size. It is shown, placed over the main window, once the
        calling method has finished building it.
        """
        window = tk.Toplevel(self._root)
        window.withdraw()  # hidden until it is built and placed, see _show_popup()
        window.title(title)
        if dialog is True:
            window.transient(self._root)
            window.resizable(False, False)
            window.bind('<Escape>', lambda event: window.destroy())

        # a themed frame under all the widgets, so the background behind them is the theme's on every system
        body = ttk.Frame(window, padding=self._gap_l)
        body.pack(fill='both', expand=True)

        window.after_idle(lambda: self._show_popup(window))
        return window, body

    def _show_popup(self, window: tk.Toplevel):
        """ places a popup made by _new_popup() over the main window, inside the screen, and shows it """
        try:
            if not window.winfo_exists():
                return
            window.update_idletasks()
            width, height = window.winfo_reqwidth(), window.winfo_reqheight()
            x = self._root.winfo_rootx() + (self._root.winfo_width() - width) // 2
            y = self._root.winfo_rooty() + self._px(24)
            margin = self._px(48)  # room for the title bar and the task bar
            x = max(0, min(x, window.winfo_screenwidth() - width - self._gap_l))
            y = max(0, min(y, window.winfo_screenheight() - height - margin))
            window.geometry(f'+{x}+{y}')
            window.deiconify()
        except tk.TclError as ex:
            log(f"Error showing popup: {ex}")

    def _add_form_row(self, form, row: int, label: str, widget, sticky='ew'):
        """ adds one row to a form: the label on the left, its field on the right. All rows of a form share the two
        columns, so the labels line up and the fields line up.

        :param form: the frame that holds the form, the widget must have been created with this frame as its parent
        :param row: the row number in the form, 0 is the top row
        :param label: the text left of the field
        :param widget: the field
        :param sticky: 'ew' to make the field as wide as the widest field in the form, 'w' to keep its own width
        """
        form.columnconfigure(1, weight=1)
        gap_above = self._gap_s if row > 0 else 0
        ttk.Label(form, text=label).grid(row=row, column=0, sticky='w', padx=(0, self._gap_m), pady=(gap_above, 0))
        widget.grid(row=row, column=1, sticky=sticky, pady=(gap_above, 0))

    def _add_button_row(self, parent, ok=None, cancel=None, extra=(), ok_text='OK', cancel_text='Cancel'):
        """ adds the row of buttons at the bottom of a popup and returns its frame.

        :param parent: the frame to put the row in, it is packed at the bottom
        :param ok: the method for the button that applies the popup, None for no such button
        :param cancel: the method for the button that closes the popup, None for no such button
        :param extra: list of (text, method) for other buttons, they are placed on the left
        :param ok_text: the text on the ok button
        :param cancel_text: the text on the cancel button

        The ok and cancel buttons are on the right, in the order of the system: OK then Cancel on Windows, Cancel
        then OK on macOS and Linux.
        """
        row = ttk.Frame(parent)
        row.pack(side='bottom', fill='x', pady=(self._gap_l, 0))
        for text, command in extra:
            ttk.Button(row, text=text, command=command).pack(side='left', padx=(0, self._gap_s))

        buttons = []
        if ok is not None:
            buttons.append((ok_text, ok))
        if cancel is not None:
            buttons.append((cancel_text, cancel))
        if self._os_type != OsType.WINDOWS:
            buttons.reverse()
        for text, command in reversed(buttons):  # packed from the right edge inwards
            ttk.Button(row, text=text, command=command).pack(side='right', padx=(self._gap_s, 0))
        return row

    def _popup_message(self, title: str, message: str, extra=()):
        """ opens a small popup that shows a message and an OK button
        :param title: the title of the window
        :param message: the text to show
        :param extra: list of (text, method) for other buttons, the popup closes before the method runs
        """
        window, body = self._new_popup(title)
        ttk.Label(body, text=message, wraplength=self._px(480), justify='left').pack(anchor='w')

        def close_then(command):
            window.destroy()
            command()

        buttons = [(text, lambda cmd=command: close_then(cmd)) for text, command in extra]
        self._add_button_row(body, ok=window.destroy, extra=buttons)
        return window


    @ staticmethod
    def _get_menu_item_by_label( menu: tk.Menu, label: str):
        """ returns a menu item by passing the menu object and the label of the item
        @param menu: tk.Menu, the menu object to search
        @param label: str, the label of the menu item to search for"""
        for item in menu:
            if item.cget('label') == label:
                return item

    def _set_visibility_locals_table(self, state: bool, number_of_visible_rows=None):
        """ sets the visibility of the locals table based on the state
        :param state: bool, True to show the locals table, False to hide the locals table
        :param number_of_visible_rows: None, if None uses settings else uses number passed
        """
        if state is True:
            self._settings.show_locals_table = True
            self._tk_var_menu_view_show_locals_table.set(True)
        else:
            self._settings.show_locals_table = False
            self._tk_var_menu_view_show_locals_table.set(False)

        """   -------------------------------------  Locals ---------------------------------------  """

        # remove the existing table, it is re-built below when it is visible
        if hasattr(self, '_frame_locals'):
            self._frame_locals.destroy()

        if self._settings.show_locals_table is True:


            self._view_menu.entryconfig('Show locals table', state='normal')
            # create a frame for the locals display
            self._frame_locals = UiFrame(self._top_frame, background=self._background_color)
            self._frame_locals.grid(row=self._ROW_LOCALS, column=0, sticky='nsew', pady=(self._gap_m, 0))

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
            self._locals_table.heading('value', text='Variable Values')
            self._locals_table.column('#0', width=self._px(self._settings.locals_width_key))
            self._locals_table.column('value', width=self._px(self._settings.locals_width_value))
            self._locals_table.pack(fill='both', expand=True)

            # add right click menu to locals
            self._bind_right_click(self._locals_table, self._right_click_menu_locals_table)

            self._update_locals_display()

        # re-size window to fit all visible elements
        self.re_draw_main_window_to_fit_all_elements()

    def _right_click_menu_locals_table(self, event):
        """ creates a right click menu for the locals table """
        # create a right click menu
        right_click_menu = tk.Menu(self._root, tearoff=0)
        right_click_menu.add_command(label='Insert value to stack at X', command=self._insert_value_to_stack_at_x)
        right_click_menu.add_command(label='Edit value', command=self._edit_variable_value)
        right_click_menu.add_command(label='Copy value', command=self._copy_variable_value)

        # add a line seperator to the menu
        right_click_menu.add_separator()
        # add item: "remove selected item"
        right_click_menu.add_command(label='Remove selected variable', command=self._remove_selected_item_from_locals_table)

        right_click_menu.add_separator()
        right_click_menu.add_command(label='Set number of visible rows', command=self.popup_set_stack_message_vars_height)

        right_click_menu.add_separator()
        right_click_menu.add_command(label='Clear all variables', command=self.menu_clear_all_variables)

        right_click_menu.post(event.x_root, event.y_root)

    def _right_click_menu_stack_table(self, event):
        """ creates a right click menu for the stack table """
        # create a right click menu
        right_click_menu = tk.Menu(self._root, tearoff=0)
        right_click_menu.add_command(label='Get Info', command=self._get_stack_value_info)
        right_click_menu.add_command(label='Edit value', command=self._edit_stack_value)
        right_click_menu.add_command(label='Copy Value', command=self.copy_stack_value)

        # add a line seperator to the menu
        right_click_menu.add_separator()
        # add item: "remove selected item"
        right_click_menu.add_command(label='Clear Stack', command=self.clear_stack)
        right_click_menu.add_command(label='Clear Selected', command=self.stack_clear_selected)

        right_click_menu.add_separator()
        right_click_menu.add_command(label='Set number of visible rows', command=self.popup_set_stack_message_vars_height)

        right_click_menu.post(event.x_root, event.y_root)

    def _insert_value_to_stack_at_x(self):
        """ inserts the value of the selected item in the locals table to the stack at X """
        selected = self._locals_table.selection()
        if len(selected) == 0:
            return
        key = self._locals_table.item(selected)['text']

        # value = self._locals_table.item(selected)['values'][0]
        # this does not work because the value returned is a string so for a list you get [1 2 3] instead of [1, 2, 3] as expected
        # need to grab the actual value from the calculator locals using the key

        locals = self._c.return_locals() # type: dict
        value = locals.get(key, None)
        if value is None:
            self._update_message_display(f"Variable '{key}' not found in locals.")
            return
        self._c.user_entry(value)

        self._update_stack_display()
        self._update_message_display(f"Inserted value at x: {key}={value}")
        log(f"Inserted value at x: {key}={value}")

    def _copy_variable_value(self):
        """ copies the value of the selected item in the locals table to the clipboard """
        selected = self._locals_table.selection()
        if len(selected) == 0:
            return
        value = self._locals_table.item(selected)['values'][0]
        self._root.clipboard_clear()
        self._root.clipboard_append(value)
        self._root.update()

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
        window, body = self._new_popup('Edit Variable Value')

        # create a label to ask the user to edit the value
        ttk.Label(body, text=f'Edit the value for: {key}').pack(anchor='w')

        # create a text entry field
        entry = ttk.Entry(body, width=40)
        entry.insert(0, value)
        entry.pack(fill='x', pady=(self._gap_s, 0))

        def apply_value():
            new_value = entry.get()
            self._c.user_entry(f"{key}={new_value}")
            self._c.enter_press()
            self._update_message_display()
            self._update_locals_display()
            self._update_stack_display()

            window.destroy()

        # bind enter press to apply_value
        entry.bind('<Return>', lambda event: apply_value())

        # create the buttons to save or cancel the changes
        self._add_button_row(body, ok=apply_value, cancel=window.destroy)

        entry.focus()

    def _remove_selected_item_from_locals_table(self):
        """ removes the selected item from the locals table """
        selected = self._locals_table.selection()
        if len(selected) == 0:
            return
        for item in selected:
            key = self._locals_table.item(item)['text']
            value = self._locals_table.item(item)['values'][0]
            self._c.delete_local(key)
        self._update_locals_display()
        self._update_message_display()

    def _edit_stack_value(self):
        """ opens a popup window to edit the value of the selected item in the stack table """
        selected = self._stack_table.selection()
        if len(selected) == 0:
            return
        key = self._stack_table.item(selected)['text']
        value = self._stack_table.item(selected)['values'][1]
        self.popup_edit_stack_value(key, value)

    def popup_edit_stack_value(self, key, value):
        """ opens a popup window to edit the value of the selected item in the stack table """
        # create a new window
        window, body = self._new_popup('Edit Stack Value')

        # create a label to ask the user to edit the value
        ttk.Label(body, text=f'Edit the value for: {key}').pack(anchor='w')

        # create a text entry field
        entry = ttk.Entry(body, width=40)
        entry.insert(0, value)
        entry.pack(fill='x', pady=(self._gap_s, 0))

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

        # create the buttons to save or cancel the changes
        self._add_button_row(body, ok=apply_value, cancel=window.destroy)

        # set focus to entry
        entry.focus()


    def _set_visibility_buttons(self, state: bool):
        """ sets the visibility of the buttons based on the state """
        if state is True:
            self._settings.show_buttons = True
            self._tk_var_menu_view_show_buttons.set(True)
        else:
            self._settings.show_buttons = False
            self._tk_var_menu_view_show_buttons.set(False)

        # remove the existing buttons, destroying the frame destroys every button in it
        if hasattr(self, '_bottom_button_frame'):
            self._bottom_button_frame.destroy()

        if self._settings.show_buttons is True:
            self._build_buttons()

        # re-size window to fit all visible elements
        self.re_draw_main_window_to_fit_all_elements()

    def _build_buttons(self):
        """ builds the calculator keys in the bottom row of the main window

        The keys are in two halves, each half is two groups of keys above each other:

            left half               right half
            operations (2 wide)     numbers (3 wide)
            stack keys (1 wide)     calculation keys (2 wide)

        Both halves have 9 rows of keys, so they start and end on the same line. The keys of a group share the width
        of the group equally and the halves share the width of the window 2 to 3, which makes a single key the same
        width in both halves. No key is given a width: the theme of the system sets the size of a key, so there is
        nothing to adjust per operating system.
        """
        bg_color = self._background_color
        self._bottom_button_frame = UiFrame(self._top_frame, background=bg_color)
        self._bottom_button_frame.grid(row=self._ROW_BUTTONS, column=0, sticky='ew', pady=(self._gap_m, 0))

        # column 0 and 2 are the halves, column 1 is the gap between them
        self._bottom_button_frame.columnconfigure(0, weight=2, uniform='half')
        self._bottom_button_frame.columnconfigure(1, minsize=self._gap_m)
        self._bottom_button_frame.columnconfigure(2, weight=3, uniform='half')
        self._left_frame = UiFrame(self._bottom_button_frame, background=bg_color)
        self._left_frame.grid(row=0, column=0, sticky='new')
        self._right_frame = UiFrame(self._bottom_button_frame, background=bg_color)
        self._right_frame.grid(row=0, column=2, sticky='new')
        self._left_frame.columnconfigure(0, weight=1)
        self._right_frame.columnconfigure(0, weight=1)

        # Operation Buttons ---------------------------

        operations = {'√': 'sqrt', 'sin': 'sin', 'cos': 'cos', 'tan': 'tan', 'log': 'log10', 'ln': 'ln', }
        keys = [(name, lambda btn=button: self.button_press(btn)) for name, button in operations.items()]
        self._operation_buttons = self._add_key_group(self._left_frame, keys, columns=2, group_row=0)

        # Special Buttons ---------------------------

        special = {'stack to list': 'stack_to_list', 'iterable to stack': 'iterable_to_stack',
                   'stack to array': 'stack_to_array', 'roll up': 'roll_up', 'roll down': 'roll_down', }
        keys = [(name, lambda btn=button: self.button_press(btn)) for name, button in special.items()]
        keys.append(('plot', lambda: self.show_plot()))
        self._special_buttons = self._add_key_group(self._left_frame, keys, columns=1, group_row=1)

        # Numeric buttons --------------------------------

        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '±']
        keys = [(button, lambda btn=button: self.button_press(btn)) for button in numbers]
        self._numeric_buttons = self._add_key_group(self._right_frame, keys, columns=3, group_row=0)

        # Calculation Buttons ---------------------------

        # the more buttons are the left column and the calc buttons the right column
        more_buttons = ['x²', 'xʸ', 'eˣ', 'π', 'ℇ']
        calc_buttons = ['delete', 'clear', 'x⟷y', '1/x', 'enter', ]
        keys = []
        for more, calc in zip(more_buttons, calc_buttons):
            keys.append((more, lambda btn=more: self.button_press(btn)))
            keys.append((calc, lambda btn=calc: self.button_press(btn)))
        self._calc_buttons = self._add_key_group(self._right_frame, keys, columns=2, group_row=1)

    def _add_key_group(self, parent, keys, columns: int, group_row: int):
        """ adds a group of calculator keys to parent and returns the frame of the group

        :param parent: the frame of the half the group belongs to
        :param keys: list of (text, method), placed left to right, top to bottom
        :param columns: the number of keys in a row, the keys share the width of the group equally
        :param group_row: 0 for the upper group of the half, 1 for the lower group
        """
        key_gap = self._px(2)
        frame = UiFrame(parent, background=self._background_color)
        frame.grid(row=group_row, column=0, sticky='ew', pady=(self._gap_m if group_row > 0 else 0, 0))

        # the keys are in the even columns, the odd columns are the gaps between them, this way every key of the
        # group is exactly the same width and the group starts and ends on the edges of its half
        for column in range(columns):
            frame.columnconfigure(2 * column, weight=1, uniform='key')
            if column > 0:
                frame.columnconfigure(2 * column - 1, minsize=key_gap)

        for index, (text, command) in enumerate(keys):
            row, column = divmod(index, columns)
            ttk.Button(frame, text=text, command=command, style='Key.TButton',
                       ).grid(row=row, column=2 * column, sticky='nsew', pady=(key_gap if row > 0 else 0, 0))
        return frame

    def _set_visibility_message_field(self, state: bool):
        """ sets the visibility of the message field based on the state """
        # remove the existing field, it is re-built below when it is visible
        if hasattr(self, '_message_field'):
            self._message_field.destroy()

        if state is True:
            # add a field for text messages, with the same flat border as the tables above and below it
            self._message_field = tk.Text(self._top_frame,
                                          state='normal',
                                          height=self._settings.message_height,
                                          wrap='word',
                                          padx=self._gap_s,
                                          pady=self._px(2), )
            self._flat_border(self._message_field)
            # use the data font, it follows the font settings, see _apply_fonts()
            self._message_field.config(font=self._data_font)

            # set width with settings
            self._message_field.config(width=self._settings.message_width)
            self._message_field.grid(row=self._ROW_MESSAGE, column=0, sticky='nsew', pady=(self._gap_m, 0))
            self._settings.show_message_field = True
            self._tk_var_menu_view_show_message_field.set(True)
            # re-size window to fit all visible elements
            self.re_draw_main_window_to_fit_all_elements()
            self._update_message_display()
        else:
            self._settings.show_message_field = False
            self._tk_var_menu_view_show_message_field.set(False)
            # re-size window to fit all visible elements
            self.re_draw_main_window_to_fit_all_elements()

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
        window, body = self._new_popup('Confirm Clear All Functions')

        # create a label to ask the user if they are sure
        ttk.Label(body, text='Are you sure you want to clear all user functions?').pack(anchor='w')

        def clear_all_user_functions():
            self._c.clear_user_functions()
            window.destroy()

        # create the buttons to confirm or cancel the clear all user functions
        self._add_button_row(body, ok=clear_all_user_functions, cancel=window.destroy)


    def popup_edit_user_function(self):
        """opens a popup window that has a list of functions thhat when clicked displayes the function in a text field"""
        # create a new window

        # -------- Local Methods for Popup Edit User Functions --------

        def on_search_var_change(*args):
            search_text = search_var.get().lower()
            list_box.delete(0, 'end')
            for key in self._c.return_user_functions().keys():
                if search_text in key.lower():
                    list_box.insert('end', key)


        def update_list_box(_in=None, ):
            current_selection = list_box.curselection()

            list_box.delete(0, 'end')
            for key in self._c.return_user_functions().keys():
                list_box.insert('end', key)

            # set to previous current selection
            if current_selection:
                list_box.selection_set(current_selection)
                show_function()

        def show_function(_in=None):
            selected = list_box.curselection()
            if len(selected) == 0:
                return
            key = list_box.get(selected)
            function_string = self._c.return_user_functions().get(key, '')
            function_field.delete('1.0', tk.END)
            function_field.insert('end', function_string)

        def save_changes():
            """ saves the changes made to the function """
            try:
                selected = list_box.curselection()
                if len(selected) == 0:
                    return
                func_str = function_field.get('1.0', tk.END)
                self._c.add_user_function(func_str)
            except Exception as ex:  # open a popup with the exception
                message = f"Exception saving function: {ex}"
                # open a simple text popup displaying the message
                self._popup_message('Warning', message)

        def add_function():
            """ opens a popup to add a function """
            self.popup_add_function(cb_method=update_list_box)
            # clear the list box
            list_box.delete(0, 'end')
            update_list_box()

        def to_stack(exe=False):
            """ add the selected function to the stack, if exe is True then also execute the function after adding to stack """
            # grab selected
            selected = list_box.curselection()
            if len(selected) == 0:
                return

            k = list_box.get(selected)
            if exe is False:

                self._c.user_entry(k)
                self._update_stack_display()

            else:
                x = self._c.return_stack_for_display(0)

                # if you just typed a number it may be a string in stack[0], convert it by enter press
                if isinstance(x, str):
                    self._c.enter_press()
                self._c.user_entry(k)
                self._c.enter_press()
                self._update_stack_display()
                self._update_message_display()

            # set focus to the main window
            self._root.focus_set()

        def run_now():
            to_stack(exe=True)

        def remove_user_function():
            selected = list_box.curselection()
            if len(selected) == 0:
                return
            key = list_box.get(selected)
            self._c.clear_user_functions(key)
            update_list_box()

        def edit_in_idle(widget_in: tk.Text):
            """ opens an """

            # grab all the text
            selected_text = widget_in.get("1.0", tk.END)

            window_text = ("# edit the function below, save and close the window to update the "
                           "function in the calculator \n") + selected_text

            with open("temp.py", "w") as f:
                f.write(window_text)

            self.open_file_in_idle_ide("temp.py")

            with open("temp.py", "r") as f:
                new_text = f.read()
                # remove first line if it starts with "# edit the function below"
                if new_text.startswith("# edit the function below"):
                    new_text = new_text.split("\n", 1)[1]

            # update the text widget with the new text
            widget_in.delete("1.0", tk.END)
            widget_in.insert("1.0", new_text)

            # remove the temp file
            subprocess.run(["rm", "temp.py"])

        # ------- build the popup window --------

        window, body = self._new_popup('Edit User Function', dialog=False)

        # add the buttons first: they are at the bottom and keep their height when the window is re-sized
        button_row = self._add_button_row(body, extra=[('Add Function', add_function),
                                                       ('Remove Function', remove_user_function),
                                                       ('Save Changes', save_changes),
                                                       ('To Stack', to_stack),
                                                       ('Run', run_now), ])
        ttk.Button(button_row, text='Edit in Idle', command=lambda: edit_in_idle(function_field)).pack(side='right')

        # create a search field to search for functions
        search_var = tk.StringVar()
        # set default search var to: type here to search
        search_var.set('search')
        search_entry = ttk.Entry(body, textvariable=search_var)
        search_entry.pack(fill='x')
        search_var.trace_add('write', on_search_var_change)


        # create a list box to show the user functions
        list_box = self._flat_border(tk.Listbox(body, height=10, width=75))
        for key in self._c.return_user_functions().keys():
            list_box.insert('end', key)
        list_box.pack(expand=True, fill='both', pady=(self._gap_m, 0))

        # create a text filed to display the selected function
        function_field = self._flat_border(tk.Text(body, height=25, width=50, padx=self._gap_s, pady=self._px(2)))
        function_field.pack(expand=True, fill='both', pady=(self._gap_m, 0))



        # selecting the listbox in any way shows the function
        # list_box.bind('<Double-1>', show_function)
        # list_box.bind('<Button-1>', show_function)
        list_box.bind('<<ListboxSelect>>', show_function)


    def popup_add_function(self, function_string=None, parent_object=None, cb_method=None):
        """ opens a popup window to add a function to the calculator """

        if function_string is None:
            input_txt = "# write your function below, save and close to window to add the function to the calculator \n "
        else:
            input_txt = function_string

        with open("temp.py", "w") as f:
            f.write(input_txt)

        try:
            self.open_file_in_idle_ide("temp.py")
        except Exception as ex:
                message = f"Error opening idle: {ex}"
                # open popup with the message
                self._popup_message('Error Opening Idle', message,
                                    extra=[('Edit Here', lambda: self.popup_add_function(function_string))])

                # remove the file, check if exists first to avoid recursion errors
                fp = pathlib.Path("temp.py")
                if fp.exists():
                    subprocess.run(["rm", "temp.py"])
                self._update_message_display(message)
                log(f"Error opening idle: {ex}")
                return

        with open("temp.py", "r") as f:
            function_string = f.read()

            # remove the first line if it starts with "# write your function below"
            if function_string.startswith("# write your function below"):
                function_string = function_string.split("\n", 1)[1]

            try:
                self._c.add_user_function(function_string)
            except Exception as ex:
                message = f"Error adding function: {ex}"

                # open popup with the message
                self._popup_message('Error Adding Function', message,
                                    extra=[('Edit', lambda: self.popup_add_function(function_string))])

                self._update_message_display(message)
            else:
                if cb_method is not None:
                    cb_method()

        # remove the temp file
        subprocess.run(["rm", "temp.py"])

    def popup_show_all_functions(self):
        """ opens a popup window to show the all functions available to the calculator """
        # create a new window
        window, body = self._new_popup('All Functions', dialog=False)
        func_dict = self._c.return_all_functions()

        # add the bottom row first, it keeps its height when the window is re-sized: the number of functions on the
        # left and the button to close the window on the right
        button_row = self._add_button_row(body, cancel=window.destroy, cancel_text='Close')
        ttk.Label(button_row, text=f"Number of functions: {len(func_dict)}").pack(side='left')

        # create a text entry field with a scroll bar
        text_frame = ttk.Frame(body)
        text_frame.pack(expand=True, fill='both')
        entry = self._flat_border(tk.Text(text_frame, height=30, width=75, padx=self._gap_s, pady=self._px(2)))
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
        scroll = ttk.Scrollbar(text_frame, orient='vertical', command=entry.yview)
        scroll.pack(side='right', fill='y')
        entry.config(yscrollcommand=scroll.set)
        entry.pack(side='left', expand=True, fill='both')

    def popup_function_buttons(self):
        """ opens a popup window to show the all user functions available to the calculator """
        # create a new window
        window, body = self._new_popup('Function Buttons')

        # create a button for each function, they look like the keys of the calculator
        func_dict = self._c.return_user_functions()
        sorted_dict = dict(sorted(func_dict.items()))
        names = [key for key in sorted_dict.keys() if '__' not in key]
        if len(names) == 0:
            ttk.Label(body, text='There are no user functions yet.').pack(anchor='w')
        for index, key in enumerate(names):
            ttk.Button(body,
                       text=f"{key}",
                       command=lambda btn=key: self._popup_function_button_press(btn),
                       style='Key.TButton',
                       ).pack(fill='x', pady=(self._px(2) if index > 0 else 0, 0))

        # create a button to close the window
        self._add_button_row(body, cancel=window.destroy, cancel_text='Close')

    # add popup to set the font name and sizes for the whole UI
    def popup_set_stack_font_parameters(self):
        """ open a popup in which you can set the UiSettings variables for the font name and the font sizes. One font
        name applies to the whole UI, the sizes are set separately for the data, the buttons and everything else """
        window, body = self._new_popup('Set Font Parameters')
        frm = ttk.Frame(body)
        frm.pack(fill='x')

        # the installed font families, names starting with '@' are the vertical variants on Windows
        families = sorted({name for name in tkfont.families(self._root) if not name.startswith('@')},
                          key=str.lower)
        family_lookup = {name.lower(): name for name in families}
        family_lookup.update({'default': 'Default'})

        ui_family, ui_size = self._font_setting(getattr(self._settings, 'ui_font', None), None)
        if ui_size is None:
            ui_size = self._system_ui_font_size()

        font_name_entry = ttk.Combobox(frm, width=28, values=['Default'] + families)
        font_name_entry.insert(0, str(self._settings.stack_font[0]))
        self._add_form_row(frm, 0, 'Font name:', font_name_entry)

        size_rows = [('Stack, variables and message size:', self._font_setting(self._settings.stack_font, 15)[1]),
                     ('Calculator keys and table headings size:',
                      self._font_setting(self._settings.button_font, 12)[1]),
                     ('Menus and popups size:', ui_size), ]
        size_entries = []
        for row, (label, value) in enumerate(size_rows, start=1):
            entry = ttk.Entry(frm, width=8)
            entry.insert(0, str(value))
            self._add_form_row(frm, row, label, entry, sticky='w')
            size_entries.append(entry)

        def apply_values():
            entered_name = font_name_entry.get().strip()
            new_font_name = family_lookup.get(entered_name.lower())
            if new_font_name is None:
                self._update_message_display(f"Font not found: '{entered_name}', pick a name from the list")
                return
            try:
                new_sizes = [int(entry.get()) for entry in size_entries]
                if min(new_sizes) < 1:
                    raise ValueError('Font size must be >= 1')
            except Exception as ex:
                self._update_message_display(f"Invalid font size: {ex}")
                return
            data_size, button_size, new_ui_size = new_sizes

            # the system font and size are stored as 'Default' and None so a saved state follows the system it is
            # opened on
            if new_font_name == 'Default' and new_ui_size == self._system_ui_font_size():
                new_ui_size = None

            # apply to settings
            self._settings.stack_font = (new_font_name, data_size)
            self._settings.message_font = (new_font_name, data_size)
            self._settings.locals_font = (new_font_name, data_size)
            self._settings.button_font = (new_font_name, button_size)
            self._settings.ui_font = (new_font_name, new_ui_size)

            # the widgets all use named fonts, so this updates every font on screen without re-building anything
            self._apply_fonts()

            self._update_message_display(f"Applied new font: {new_font_name}, sizes: data {data_size}, "
                                         f"buttons {button_size}, menus and popups {size_entries[2].get()}")

            window.destroy()

        # Buttons
        self._add_button_row(body, ok=apply_values, cancel=window.destroy)
        # Enter key = apply
        window.bind('<Return>', lambda e: apply_values())
        font_name_entry.focus()


    def popup_set_stack_message_vars_height(self):
        """ open a popup in which you can set the UiSettings variables for the stack height, the message height and the
        variables height in the UI """
        window, body = self._new_popup('Set Stack / Message / Locals Heights')
        frm = ttk.Frame(body)
        frm.pack(fill='x')

        stack_entry = ttk.Entry(frm, width=8)
        stack_entry.insert(0, str(self._settings.stack_rows))
        self._add_form_row(frm, 0, 'Stack row count:', stack_entry, sticky='w')

        locals_entry = ttk.Entry(frm, width=8)
        locals_entry.insert(0, str(self._settings.locals_rows))
        self._add_form_row(frm, 1, 'Locals row count:', locals_entry, sticky='w')

        message_entry = ttk.Entry(frm, width=8)
        message_entry.insert(0, str(self._settings.message_height))
        self._add_form_row(frm, 2, 'Message row height:', message_entry, sticky='w')

        def apply_values():
            try:
                new_stack = int(stack_entry.get())
                new_locals = int(locals_entry.get())
                new_message = int(message_entry.get())
                if new_stack < 1 or new_locals < 1 or new_message < 1:
                    raise ValueError('Values must be >= 1')
            except Exception as ex:
                self._update_message_display(f"Invalid value: {ex}")
                return

            # apply to settings
            self._settings.stack_rows = new_stack
            self._settings.locals_rows = new_locals
            self._settings.message_height = new_message

            # update stack table height (this method will set the Treeview height)
            try:
                self._update_visible_ui_object_stack(number_visible_rows=new_stack)
            except Exception:
                # fallback: directly set property if UI exists
                if hasattr(self, '_stack_table'):
                    self._stack_table['height'] = new_stack

            # recreate locals table if visible
            if self._settings.show_locals_table:
                if hasattr(self, '_frame_locals'):
                    try:
                        self._frame_locals.destroy()
                    except Exception:
                        pass
                # _set_visibility_locals_table will recreate with the new locals_rows
                self._set_visibility_locals_table(True, number_of_visible_rows=new_locals)

            # recreate message field if visible
            if self._settings.show_message_field:
                if hasattr(self, '_message_field'):
                    try:
                        self._message_field.destroy()
                    except Exception:
                        pass
                self._set_visibility_message_field(True)

            # refresh displays
            self._update_stack_display()
            self._update_locals_display()
            self._update_message_display(
                f"Applied new sizes: stack={new_stack}, locals={new_locals}, message={new_message}")

            window.destroy()

        # Buttons
        self._add_button_row(body, ok=apply_values, cancel=window.destroy)

        # Enter key = apply
        window.bind('<Return>', lambda e: apply_values())
        stack_entry.focus()

    def _popup_function_button_press(self, function: str):
        """ this method gets bound to the function buttons in the popup window """
        self._c.enter_press()
        self._c.user_entry(function)
        self._c.enter_press()
        self._update_stack_display()
        self._update_message_display()
        self._update_locals_display()
        # set focus to the main window
        self._root.focus_set()

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
            log(f"Error loading settings: {ex}, from file: {self._autosave_path}")


        try:
            for lib in self._settings.load_on_launch:
                self._c.load_python_module(lib)
        except Exception as ex:
            self._update_message_display(f"Error loading module on launch: {ex}")
            log(f"Error loading module on launch: {ex}")


    def user_exit(self):
        """ exits the program, saves the state if the settings are set to save state on exit """
        try:
            if self._settings.save_state_on_exit:
                self.menu_save_state(save_path=self._autosave_path)
        except Exception as exc:
            log(f"Unable to save state on exit: {exc}")
        finally:
            self._root.destroy()
            self._root.quit()

    def _get_stack_value_info(self):
        """ bound to the right click menu to get info on the selected stack item
        gets info from the selected stack item and displays it in the message field """
        try:
            selected = self._stack_table.selection()
            if len(selected) == 0:
                return
            sel = self._stack_table.item(selected)
            idx = sel['text']
            value = self._c.return_stack_for_display(int(idx)) # is the actual type, not a string
            if isinstance(value, str):
                info = f'"INFO: {value}, len: {len(value)}, bytes: {str(value).encode()}"'
            elif isinstance(value, int):
                info = f"INFO: {value}, bytes: {int(value).to_bytes(byteorder="big")}, big-endian "
            elif isinstance(value, float):
                info = f"INFO: {value}, bytes: {struct.pack('>d', value)}, big-endian "
            elif isinstance(value, np.ndarray):
                se = value # type: np.ndarray
                info = (f"INFO: [{float(se[0])}, ... , {float(se[-1])}] "
                                      f"shape: {se.shape}, dtype: {se.dtype}, max: {se.max():0.3f}, "
                                      f"min: {se.min():0.3f}, mean: {se.mean():0.3f}, sum: {se.sum():0.3f}")
                calc = self._c
                calc.user_entry(f"array_min={se.min():0.3f}")
                calc.enter_press()
                calc.user_entry(f"array_max={se.max():0.3f}")
                calc.enter_press()
                calc.user_entry(f"array_mean={se.mean():0.3f}")
                calc.enter_press()
                calc.user_entry(f"array_stddev={se.std():0.3f}")
                calc.enter_press()
                calc.user_entry(f"array_sum={se.sum():0.3f}")
                calc.enter_press()
                calc.user_entry(f"array_length={len(se)}")
                calc.enter_press()
                self._update_locals_display()
            elif isinstance(value, list):
                entry_type = type(value[0])
                if entry_type is int or entry_type is float:
                    sm = sum(value)
                    mean = sm / len(value)
                    info = (f"INFO: {value}, len: {len(value)}, type: {entry_type}, max: {max(value):0.3f}, min: {min(value):0.3f}, "
                            f"mean: {mean:0.3f}, sum: {sm:0.3f}")
            else:
                info = f"INFO: {value}, type: {type(value)}"
        except Exception as ex:
            info = f"Error getting info on stack item: {ex}"

        self._update_message_display(info)

    def copy_stack_value(self):
        """ copies the value of the selected stack item to the clipboard """
        selected = self._stack_table.selection()
        if len(selected) == 0:
            return
        sel = self._stack_table.item(selected)
        idx = sel['text']
        value = self._c.return_stack_for_display(int(idx))
        self._root.clipboard_clear()
        self._root.clipboard_append(value)

    def stack_clear_selected(self):
        """ clears the selected value from the stack """
        selected = self._stack_table.selection()
        if len(selected) == 0:
            return
        sel = self._stack_table.item(selected)
        idx = sel['text']
        popped = self._c.clear_stack_level(int(idx))
        self._update_stack_display()
        msg = f"Cleared stack level {idx} value: {popped}"
        self._update_message_display(msg)

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

    def popup_x_plot(self):
        """ applies the plot options and closes the window """
        plots_dict = dict()
        len_str = ' ('

        def get_trace_key_from_svar(svar: tk.StringVar):
            """ returns the trace key from the StringVar """
            return svar.get().split(len_str)[0].strip()

        def clear_plots():
            plots_dict.clear()


        def plot_y():
            """ applies the plot options and closes the window """
            y = get_trace_key_from_svar(y_svar)
            locals = self._c.return_locals()
            Y = locals.get(y, None)
            if Y is None:
                self._update_message_display(f"Error: '{y}' not found in locals.")
                return
            X = list(range(len(Y)))

            new_plot = plots.XyPlotContainer(X,
                                  Y,
                                  name=plot_label.get(),
                                  color=color_svar.get(),
                                  line_style=line_style_svar.get(),
                                  marker=marker_svar.get(),
                                  linewidth=2,
                                  markersize=3,
                                  alpha=1.0,
                                  grid=grid_svar.get(),
                                  xlabel='data points',
                                  ylabel=get_trace_key_from_svar(y_svar),)

            plots_dict.update({trace_label.get(): new_plot})
            self._c.show_plots_dict(plots_dict)
            self._update_message_display()

        # create a new window
        window, body = self._new_popup('Y Plot Options')
        ttk.Label(body, text='Define the plot parameters').pack(anchor='w')
        ttk.Label(body, text='The X values are 0 to len(Y)').pack(anchor='w', pady=(self._gap_s, self._gap_m))
        form = ttk.Frame(body)
        form.pack(fill='x')

        # grab all the locals that are lists or arrays
        locals = self._c.return_locals()
        local_arrays = {key: value for key, value in locals.items() if isinstance(value, (list, np.ndarray))}
        local_array_keys = [f'{key}{len_str}{len(value)})' for key, value in local_arrays.items()]

        if len(local_arrays) < 1:
            local_array_keys = ['No arrays defined']

        # each row is a label with its field right of it

        row = 0
        y_svar = tk.StringVar(window)
        y_svar.set(local_array_keys[0])
        y_combo = ttk.Combobox(form, values=local_array_keys, textvariable=y_svar)
        self._add_form_row(form, row, 'Select Y:', y_combo)

        row = 1  # create text entry for trace label
        trace_label = ttk.Entry(form)
        trace_label.insert(0, 'Trace 1')
        self._add_form_row(form, row, 'Trace Label:', trace_label)

        row = 2  # create a text field for the plot label
        plot_label = ttk.Entry(form)
        plot_label.insert(0, 'Y Plot')
        self._add_form_row(form, row, 'Plot Label:', plot_label)

        row = 3  # create a option menu to select the plot color
        color_options = ['blue', 'red', 'green', 'black', 'orange', 'purple', 'brown']
        color_svar = tk.StringVar(window)
        color_svar.set(color_options[0])  # set default value to the first option
        color_combo = ttk.Combobox(form, values=color_options, textvariable=color_svar)
        self._add_form_row(form, row, 'Plot Color:', color_combo)

        row = 4  # create an option menu to select the plot marker
        marker_options = ['o', '', 'x', 's', '^', 'd', '*']
        marker_svar = tk.StringVar(window)
        marker_svar.set(marker_options[0])  # set default value to the first option
        marker_combo = ttk.Combobox(form, values=marker_options, textvariable=marker_svar)
        self._add_form_row(form, row, 'Plot Marker:', marker_combo)

        row = 5  # create an option menu to select the plot line style
        line_style_options = ['-', '', '--', '-.', ':']
        line_style_svar = tk.StringVar(window)
        line_style_svar.set(line_style_options[0])  # set default value to the
        line_style_combo = ttk.Combobox(form, values=line_style_options, textvariable=line_style_svar)
        self._add_form_row(form, row, 'Plot Line Style:', line_style_combo)

        row = 6  # create a button to select grid on/off
        grid_svar = tk.BooleanVar(window, value=True)  # default to True
        grid_check = ttk.Checkbutton(form, variable=grid_svar, onvalue=True, offvalue=False)
        self._add_form_row(form, row, 'Grid:', grid_check, sticky='w')

        # the buttons that act on the plot are on the left, the button that closes the window on the right
        self._add_button_row(body, cancel=window.destroy, cancel_text='Close',
                             extra=[('Add Plot', plot_y), ('Clear Plots', clear_plots), ])

    def popup_xy_plot(self):
            """ opens a popup window to show the xy plot options """

            # create a new window
            window, body = self._new_popup('XY Plot Options')
            ttk.Label(body, text='Define the plot parameters').pack(anchor='w', pady=(0, self._gap_m))
            form = ttk.Frame(body)
            form.pack(fill='x')

            # grab all the locals that are lists or arrays
            plots_dict = dict()
            len_str = ' ('
            lcls = self._c.return_locals()
            local_arrays = {key: value for key, value in lcls.items() if isinstance(value, (list, np.ndarray))}
            local_array_keys = [f'{key}{len_str}{len(value)})' for key, value in local_arrays.items()]

            if len(local_arrays) < 1:
                local_array_keys = ['No arrays defined']

            # setup the StringVars for the comboboxes
            x_svar = tk.StringVar(window) #  like: 'name'
            y_svar = tk.StringVar(window) # like: 'name'
            x_svar.set(local_array_keys[0])  # set default value to the first key
            y_svar.set(local_array_keys[0])
            x_combo = ttk.Combobox(form, values=local_array_keys, textvariable=x_svar)
            y_combo = ttk.Combobox(form, values=local_array_keys, textvariable=y_svar)

            def update_trace_label_to_selected_y(selected):
                # get the current selected y variable and set the trace label to it
                y = get_trace_key_from_svar(y_svar)
                trace_label.delete(0, 'end')
                trace_label.insert(0, y)

            y_combo.bind("<<ComboboxSelected>>", update_trace_label_to_selected_y)

            trace_label = ttk.Entry(form)
            plot_label = ttk.Entry(form)
            x_axis_name_entry = ttk.Entry(form)
            x_axis_name_entry.insert(0, 'X Axis')
            y_axis_name_entry = ttk.Entry(form)
            y_axis_name_entry.insert(0, 'Y Axis')

            color_svar = tk.StringVar(window)   # like: 'blue', 'red', etc.
            marker_svar = tk.StringVar(window) # like 'o', 'x', etc.
            line_style_svar = tk.StringVar(window) # like '-', '--', etc.
            grid_svar = tk.BooleanVar(window, value=True)  # display grid? default to True

            def build_window_widgets():
                # the rows define the order the widgets are drawn, each row is a label with its field right of it

                row = 0  # the plot label
                plot_label.insert(0, 'XY Plot')
                self._add_form_row(form, row, 'Plot Label:', plot_label)

                # plot x and y axis names
                row = 1
                self._add_form_row(form, row, 'X Axis Label:', x_axis_name_entry)

                row = 2
                self._add_form_row(form, row, 'Y Axis Label:', y_axis_name_entry)

                row = 3
                # insert a seperator line
                sep = ttk.Separator(form, orient='horizontal')
                sep.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(self._gap_m, self._gap_s))

                row = 4
                self._add_form_row(form, row, 'Select X:', x_combo)

                row = 5
                self._add_form_row(form, row, 'Select Y:', y_combo)

                row = 6  # text entry for trace label
                trace_label.insert(0, 'Trace 1')
                self._add_form_row(form, row, 'Trace Label:', trace_label)

                row = 7  # create a option menu to select the plot color
                color_options = ['blue', 'red', 'green', 'black', 'orange', 'purple', 'brown']
                color_svar.set(color_options[0])  # set default value to the first option
                color_combo = ttk.Combobox(form, values=color_options, textvariable=color_svar)
                self._add_form_row(form, row, 'Trace Color:', color_combo)

                row = 8  # create an option menu to select the plot marker
                marker_options = ['o', '', 'x', 's', '^', 'd', '*']
                marker_svar.set(marker_options[0])  # set default value to the first option
                marker_combo = ttk.Combobox(form, values=marker_options, textvariable=marker_svar)
                self._add_form_row(form, row, 'Trace Marker:', marker_combo)

                row = 9  # create an option menu to select the plot line style
                line_style_options = ['-', '', '--', '-.', ':']
                line_style_svar.set(line_style_options[0])  # set default value to the
                line_style_combo = ttk.Combobox(form, values=line_style_options, textvariable=line_style_svar)
                self._add_form_row(form, row, 'Trace Line Style:', line_style_combo)

                row = 10  # create a button to select grid on/off
                grid_check = ttk.Checkbutton(form, variable=grid_svar, onvalue=True, offvalue=False)
                self._add_form_row(form, row, 'Grid:', grid_check, sticky='w')

                # the buttons that act on the plot are on the left, the button that closes the window on the right
                self._add_button_row(body, cancel=window.destroy, cancel_text='Close',
                                     extra=[('Add Trace (show plot)', plot_xy),
                                            ('Clear Traces', clear_plots),
                                            ('Update Lists', update_list_boxes), ])

                update_trace_label_to_selected_y(None)

            def get_trace_key_from_svar(svar: tk.StringVar):
                """ returns the trace key from the StringVar """
                return svar.get().split(len_str)[0].strip()

            def clear_plots():
                plots_dict.clear()

            def plot_xy():
                """ applies the plot options and closes the window """
                x = get_trace_key_from_svar(x_svar)
                y = get_trace_key_from_svar(y_svar)
                locals = self._c.return_locals()
                X = locals.get(x, None)
                Y = locals.get(y, None)
                if X is None or Y is None:
                    self._update_message_display(f"Error: '{x}' or '{y}' not found in locals.")
                    return

                new_plot = plots.XyPlotContainer(X,
                                      Y,
                                      name=plot_label.get(),
                                      color=color_svar.get(),
                                      line_style=line_style_svar.get(),
                                      marker=marker_svar.get(),
                                      linewidth=2,
                                      markersize=3,
                                      alpha=1.0,
                                      grid=grid_svar.get(),
                                      xlabel=get_trace_key_from_svar(x_svar),
                                      ylabel=get_trace_key_from_svar(y_svar),)

                plots_dict.update({trace_label.get(): new_plot})
                title = plot_label.get()
                self._c.show_plots_dict(plots_dict,
                                        title=title,
                                        x_label=x_axis_name_entry.get(),
                                        y_label=y_axis_name_entry.get(),
                                        grid=grid_svar.get(),)
                self._update_message_display()



            def update_list_boxes():
                # grab all the locals that are lists or arrays
                lcls = self._c.return_locals()
                local_arrays = {key: value for key, value in lcls.items() if isinstance(value, (list, np.ndarray))}
                local_array_keys = [f'{key}{len_str}{len(value)})' for key, value in local_arrays.items()]
                x_combo['values'] = local_array_keys
                y_combo['values'] = local_array_keys

            build_window_widgets()



    def popup_xyz_plot(self):
        """ opens a popup window to show the xyz plot options """
        pass

    def popup_create_array(self):
        """ popup to create X (linspace) and Y (function of X); shows table, find-Y, and a plot """

        window, body = self._new_popup('Create Array', dialog=False)
        label_gap = (0, self._gap_s)   # between a label and its field
        field_gap = (0, self._gap_m)   # between a field and the next label

        # Top frame: X creation
        top = ttk.Frame(body)
        top.pack(fill='x')

        ttk.Label(top, text='X name:').grid(row=0, column=0, sticky='w', padx=label_gap)
        x_name_e = ttk.Entry(top, width=12); x_name_e.insert(0, 'X'); x_name_e.grid(row=0, column=1, padx=field_gap)

        ttk.Label(top, text='Start:').grid(row=0, column=2, sticky='w', padx=label_gap)
        start_e = ttk.Entry(top, width=10); start_e.insert(0, '0'); start_e.grid(row=0, column=3, padx=field_gap)

        ttk.Label(top, text='Stop:').grid(row=0, column=4, sticky='w', padx=label_gap)
        stop_e = ttk.Entry(top, width=10); stop_e.insert(0, '100'); stop_e.grid(row=0, column=5, padx=field_gap)

        ttk.Label(top, text='Points:').grid(row=0, column=6, sticky='w', padx=label_gap)
        points_e = ttk.Entry(top, width=8); points_e.insert(0, '1000'); points_e.grid(row=0, column=7, padx=field_gap)



        def create_x():
            try:
                start = float(start_e.get())
                stop = float(stop_e.get())
                pts = int(points_e.get())
                if pts <= 0:
                    raise ValueError('Points must be > 0')
            except Exception as ex:
                self._update_message_display(f"Invalid X parameters: {ex}")
                return
            X = np.linspace(start, stop, pts)
            name = x_name_e.get().strip() or 'X'
            # store to calculator locals by passing a python literal list (calculator user_entry expects expressions)
            try:
                self._c.user_entry(X)
                self._c.enter_press()
                self._c.user_entry(f"{name} =")
                self._c.enter_press()

            except Exception as ex:
                self._update_message_display(f"Error creating X: {ex}")
                return

            self._update_locals_display()
            self._update_message_display(f"Created {name} with {pts} points from {start} to {stop}")
            nonlocal_XY['X'] = X
            refresh_all()

        ttk.Button(top, text='Create X', command=create_x).grid(row=0, column=8)

        # Middle frame: Y creation / function selection, each row is a label with its field right of it
        mid = ttk.Frame(body)
        mid.pack(fill='x', pady=(self._gap_m, 0))

        user_funcs = list(self._c.return_user_functions().keys())
        func_cb = ttk.Combobox(mid, values=user_funcs, width=30)
        self._add_form_row(mid, 0, 'Available user functions:', func_cb, sticky='w')

        y_name_e = ttk.Entry(mid, width=12); y_name_e.insert(0, 'Y')
        self._add_form_row(mid, 1, 'Y name:', y_name_e, sticky='w')

        expr_e = ttk.Entry(mid, width=60)
        expr_e.insert(0, 'np.sin(X)')
        self._add_form_row(mid, 2, 'Expression (use `X`, `np`):', expr_e)

        def on_func_select(evt=None):
            fn = func_cb.get().strip()
            if fn:
                expr_e.delete(0, 'end')
                expr_e.insert(0, f"{fn}(X)")

        func_cb.bind('<<ComboboxSelected>>', on_func_select)

        def create_y():
            X = nonlocal_XY.get('X', None)
            if X is None:
                self._update_message_display("Create X first.")
                return
            expr = expr_e.get().strip()


            if not expr:
                self._update_message_display("Provide an expression for Y (uses X and np).")
                return

            # use the calculator's user_entry to evaluate the expression in the calculator's context
            try:
                self._c.user_entry(expr)
                self._c.enter_press()
                Y = self._c.clear_stack_level(0) # pop the result from the stack
            except Exception as ex:
                self._update_message_display(f"Error evaluating expression: {ex}")
                return

            yname = y_name_e.get().strip('(X)') or 'Y'
            self._c.user_entry(Y)
            self._c.enter_press()
            self._c.user_entry(f"{yname} =")
            self._c.enter_press()

            self._update_locals_display()
            self._update_message_display(f"Created {yname} ({Y.size} points)")
            nonlocal_XY['Y'] = Y
            refresh_all()

        ttk.Button(mid, text='Create Y', command=create_y).grid(row=2, column=2, padx=(self._gap_m, 0),
                                                                pady=(self._gap_s, 0))

        # Lower area: split into left (table & find) and right (plot)
        lower = ttk.Frame(body)
        lower.pack(fill='both', expand=True, pady=(self._gap_m, 0))

        left = ttk.Frame(lower)
        left.pack(side='left', fill='both', expand=True)

        right = ttk.Frame(lower)
        right.pack(side='right', fill='both', expand=True, padx=(self._gap_m, 0))

        # Find Y controls, added first: they are at the bottom and keep their height when the window is re-sized
        find_frame = ttk.Frame(left)
        find_frame.pack(side='bottom', fill='x', pady=(self._gap_s, 0))
        ttk.Label(find_frame, text='Find Y for X =').pack(side='left')
        find_e = ttk.Entry(find_frame, width=12);
        find_e.pack(side='left', padx=(self._gap_s, 0))

        # result field (readonly)
        result_e = ttk.Entry(find_frame, width=16, state='readonly')
        result_e.pack(side='left', padx=(self._gap_s, 0))

        # XY table (Treeview)
        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill='both', expand=True)
        cols = ('x', 'y')
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
        tree.heading('x', text='X')
        tree.heading('y', text='Y')
        tree.column('x', width=self._px(120), anchor='e')
        tree.column('y', width=self._px(120), anchor='e')
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='left', fill='y')

        def _set_result(text: str):
            # temporarily enable to update then set back to readonly
            result_e.config(state='normal')
            result_e.delete(0, 'end')
            result_e.insert(0, str(text))
            result_e.config(state='readonly')

        def find_y():
            try:
                x_val = float(find_e.get())
            except Exception:
                _set_result('Invalid X')
                return

            X = nonlocal_XY.get('X', None)
            Y = nonlocal_XY.get('Y', None)
            if X is None or Y is None:
                _set_result('No data')
                return

            # find closest index
            try:
                idx = (np.abs(X - x_val)).argmin()
                y_val = Y[idx]
                _set_result(y_val)
            except Exception:
                _set_result('Not found')

        ttk.Button(find_frame, text='Find', command=find_y).pack(side='left', padx=(self._gap_s, 0))

        # Plot area using matplotlib
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        fig = Figure(figsize=(4, 3))  # matplotlib scales the figure to the display resolution itself
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=right)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill='both', expand=True)

        # state holder for arrays
        nonlocal_XY = {'X': None, 'Y': None}

        def refresh_table():
            tree.delete(*tree.get_children())
            X = nonlocal_XY.get('X', None)
            Y = nonlocal_XY.get('Y', None)
            if X is None:
                return
            # limit rows displayed for performance; allow scroll for full
            size = X.size
            max_display = 5000  # reasonable cap
            display_count = min(size, max_display)
            for i in range(display_count):
                xv = X[i]
                yv = Y[i] if (Y is not None and i < Y.size) else ''
                tree.insert('', 'end', values=(f"{xv:.6g}", f"{yv:.6g}" if yv != '' else ''))
            if size > max_display:
                tree.insert('', 'end', values=(f"... ({size} total)", ''))

        def refresh_plot():
            ax.clear()
            X = nonlocal_XY.get('X', None)
            Y = nonlocal_XY.get('Y', None)
            if X is None or Y is None:
                ax.set_title('No data')
            else:
                ax.plot(X, Y, '-', lw=1)
                ax.set_xlabel(x_name_e.get().strip() or 'X')
                ax.set_ylabel(y_name_e.get().strip() or 'Y')
                ax.grid(True)
            canvas.draw_idle()

        def refresh_all():
            refresh_table()
            refresh_plot()

        # initial draw
        refresh_all()


    def popup_load_python_module(self):
        """ opens a popup window to load a python module into the calculator """
        window, body = self._new_popup('Load Python Module')

        modules = self._settings.load_on_launch

        # add text label
        ttk.Label(body, text='These modules are loaded on launch').pack(anchor='w')

        # create a list box containing the modules to load on launch
        listbox = self._flat_border(tk.Listbox(body, height=6, width=60))
        for mod in modules:
            listbox.insert('end', mod)
        listbox.pack(fill='both', expand=True, pady=(self._gap_s, 0))

        def add_module():
            """ adds a module to the list box """
            module_name = module_entry.get().strip()
            if module_name == '':
                return
            try:
                self._c.load_python_module(module_name)
                if module_name not in modules:
                    modules.append(module_name)
                    listbox.insert('end', module_name)
                self._update_message_display(f"Loaded module: {module_name}")
            except Exception as ex:
                self._update_message_display(f"Error loading module '{module_name}': {ex}")

        def remove_module():
            """ removes the selected module from the list box """
            selected = listbox.curselection()
            if not selected:
                return
            index = selected[0]
            module_name = listbox.get(index)
            if module_name in modules:
                modules.remove(module_name)
            listbox.delete(index)
            self._update_message_display(f"Removed module: {module_name}")

        # the field for a new module with its button right of it, the field takes the width of the window
        add_row = ttk.Frame(body)
        add_row.pack(fill='x', pady=(self._gap_m, 0))
        add_button = ttk.Button(add_row, text='Add Module', command=add_module)
        add_button.pack(side='right', padx=(self._gap_s, 0))
        module_entry = ttk.Entry(add_row)
        module_entry.insert(0, "<enter module name or path>")
        module_entry.pack(side='left', fill='x', expand=True)

        self._add_button_row(body, cancel=window.destroy, cancel_text='Close',
                             extra=[('Remove Selected Module', remove_module)])

    def _paste_wrapper_no_args(self):
        self.paste(self._root.clipboard_get())

    def paste(self, value):
        """ handles pasting from the clipboard """
        try:
            if isinstance(value, str):
                # check for and remove currency symbols
                currency_symbols = ['$', '€', '£', '¥', '₹']
                for sym in currency_symbols:
                    if sym in value:
                        value = value.replace(sym, '')

                if '\t' in value:  # tab delimited string, likely from a
                    array = self._c.str_to_numpy_array(value, delimiter='\t')
                    self._c.stack_put(array)

                elif '\n' in value: # go ahead and split the string into lines
                    lines = value.split('\n')

                    tags = {'def', 'class'} # for when you paste a function or class definition
                    for tag in tags:
                        if tag in lines[0]:
                            for line in lines:
                                self.button_press(str(line))
                            self.enter_press()
                            break
                    else:  # tag not found

                        try:
                            # remove empty lines
                            lines = [float(line.replace(',', '')) for line in lines if line.strip() != '']

                            # if its a number, lets make it a numpy array
                            if isinstance(lines[0], float | int):
                                self.button_press(str(lines))
                                self.enter_press()
                                self.button_press('np.array')
                            else:
                                self.button_press(str(lines))

                            self.enter_press()

                        except Exception as ex:
                            raise Exception (f"Error evaluating pasted value: {ex}")

                else:
                    self.button_press(str(value))
                    self.enter_press()

                msg = "Pasted value: " + str(self._c.return_stack_for_display(0))

            self._update_stack_display()
            self._update_locals_display()

        except Exception as ex:
            msg = f"Error processing pasted value: {ex}"


        self._update_message_display(msg)

    def popup_edit_numeric_display_format(self):
        """ opens a popup window to edit the format of displayed numerics """
        # create a new window
        window, body = self._new_popup('Edit Float Format String')
        form = ttk.Frame(body)
        form.pack(fill='x')

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

        # each row of the form is a label with its field right of it

        # create a text entry field
        float_entry = ttk.Entry(form, )
        float_entry.insert(0, self._settings.float_format_string)
        float_entry.config(state=state_var, background=read_only_background)
        self._add_form_row(form, 0, 'Float Format String:', float_entry)

        # create a text entry field
        integer_entry = ttk.Entry(form, )
        integer_entry.insert(0, self._settings.integer_format_string)
        integer_entry.config(state=state_var, background=read_only_background)
        self._add_form_row(form, 1, 'Integer Format String:', integer_entry)

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
        ttk.Separator(form, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew',
                                                      pady=(self._gap_m, self._gap_m))

        # create a checkbox to toggle scientific notation
        c_button = ttk.Checkbutton(form, text='Use Engineering Notation', variable=use_eng_notation_tk, onvalue=True, offvalue=False,
                                   command=apply_eng_notation, name='eng_notation')
        c_button.grid(row=3, column=0, columnspan=2, sticky='w')

        # add text below the checkbox that says: 'If use engineering notation is checked, the format string will be ignored'
        ttk.Label(form, text='If Use Engineering Notation is checked, the format strings will be ignored'
                  ).grid(row=4, column=0, columnspan=2, sticky='w', pady=(self._gap_s, 0))

        # create a numeric field
        eng_num_length = ttk.Entry(form, width=8)
        eng_num_length.insert(0, str(self._settings.eng_format_num_length))
        eng_num_length.config(state='disabled', background='grey') if not self._settings.use_engineering_notation_format else eng_num_length.config(state='normal', background='white')
        self._add_form_row(form, 5, 'Number of digits shown in Engineering Format:', eng_num_length, sticky='w')

        # create the buttons to save or cancel the changes
        self._add_button_row(body, ok=apply_format_string, cancel=window.destroy)

        float_entry.focus()

    def popup_edit_plot_options_string(self):
        """ opens a popup window to edit the plot options string, has the buttons 'ok' and 'cancel' """
        # create a new window
        window, body = self._new_popup('Edit Plot Options String')

        # create a text indicator
        ttk.Label(body, text='Plot Options String for simple plots').pack(anchor='w')


        # create a text entry field
        entry = ttk.Entry(body, width=40)
        entry.insert(0, self._settings.plot_options_string)
        entry.focus()
        entry.pack(fill='x', pady=(self._gap_s, 0))

        def apply_plot_options_string():
            self._settings.plot_options_string = entry.get()
            try:
                self._update_stack_display()
            except Exception as ex:
                message = f"Cant use plot options string: {self._settings.plot_options_string} with error: {ex}"
                self._update_message_display(message)
            else:
                window.destroy()

        # create the buttons to save or cancel the changes
        self._add_button_row(body, ok=apply_plot_options_string, cancel=window.destroy)

    def popup_edit_integer_format_string(self):
        """ deprecated method : functionality moved to Edit Numeric Display Format popup"""
        # create a new window
        window, body = self._new_popup('Edit Integer Format String')

        # create a text entry field
        entry = ttk.Entry(body, width=40)
        entry.insert(0, self._settings.integer_format_string)
        # make the focus be on the entry field
        entry.focus()
        entry.pack(fill='x')

        def apply_integer_format_string():
            self._settings.integer_format_string = entry.get()
            try:
                self._update_stack_display()
            except Exception as ex:
                message = f"Cant use format string: {self._settings.integer_format_string} with error: {ex}"
                self._update_message_display(message)
            else:
                window.destroy()

        # create the buttons to save or cancel the changes
        self._add_button_row(body, ok=apply_integer_format_string, cancel=window.destroy)

    def menu_save_state(self, save_path=None):
        """ saves the locals stack and settings to a file of the users choice
         @param save_path: str, the path to save the state to, if None a file dialog will be opened
         """
        # open a file dialog to save the state
        file_extension = ".pycalc"

        if save_path is None:
            # file = filedialog.asksaveasfile(mode='wb', defaultextension=file_extension, initialdir=self._autosave_path)
            file = filedialog.asksaveasfile(mode='wb', defaultextension=file_extension, initialdir=self._autosave_path)
            save_path = file.name
            if file is None:
                return
        else:
            try:
                file = open(save_path, mode='wb')
            except Exception as ex:
                self._update_message_display(f"Error saving state to file: {ex}")
                return

        calc_state = CalculatorUiState()
        calc_state.stack = self._c.return_stack_for_display()
        calc_state.locals = self._c.return_locals()
        calc_state.functions = self._c.return_user_functions()
        calc_state.settings = copy(self._settings)



        # the widths are saved in design pixels, so a saved state looks the same on a display with another scaling
        def design_px(screen_pixels):
            return int(round(screen_pixels / self._ui_scale))

        calc_state.settings.stack_value_width = design_px(self._stack_table.column('value', 'width'))
        calc_state.settings.stack_index_width = design_px(self._stack_table.column('#0', 'width'))
        calc_state.settings.stack_type_width = design_px(self._stack_table.column('type', 'width'))

        if self._settings.show_locals_table == True: # only try to save locals table widths if the locals table is visible

            calc_state.settings.locals_width_key = design_px(self._locals_table.column('#0', 'width'))
            calc_state.settings.locals_width_value = design_px(self._locals_table.column('value', 'width'))

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
            self._apply_fonts()  # the loaded state carries its own font settings
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
            incoming_keys = set(vars(incoming).keys())
            latest = self._settings

            # the current settngs may have fields that do not exist in an older save settings, grab existing keys only
            for key, value in vars(latest).items():
                if key in incoming_keys:
                    setattr(latest, key, getattr(incoming, key))

            self._settings = latest

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

    def button_eval_x(self):
        self._c.run_eval_on_stack_x()
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
                                     values=(entry_type, stack_entry_string),
                                     )

    def _update_message_display(self, direct_message=None):
        """ updates the message field with the message from the calculator, you
        can pass a message to this method to display a message directly in the UI context

        @param direct_message: str , a message to display in the message field, passing a message
        will override getting the message from the calculator, this is useful for displaying
        UI context messages to the user
        """
        if self._settings.show_message_field is True:
            try:
                self._message_field.config(state='normal')
                self._message_field.delete('1.0', 'end')

                if direct_message is not None:
                    self._message_field.insert('1.0', direct_message)
                else:
                    msg = self._c.return_message()
                    if msg is not None:
                        self._message_field.insert('1.0', msg)

                self._message_field.config(state='normal')
            except Exception as ex:
                log(f"Error updating message display: {ex}")

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

    @staticmethod
    def open_file_in_idle_ide(path: str):
        fp = pathlib.Path(path)
        if fp.exists():
            try:
                subprocess.run(["python3", "-m", "idlelib.idle", path])
            except Exception as ex:
                try:
                    subprocess.run(["python", "-m", "idlelib.idle", path])
                except Exception as ex:
                    message = f"Error opening idle: {ex}"
                    raise Exception(message)
