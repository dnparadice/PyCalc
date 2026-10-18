import tkinter as tk
from tkinter import messagebox, ttk


if __name__ == '__main__':
    """ main entry point for the application """
    root = tk.Tk()
    root.withdraw()
    splash = tk.Toplevel(root)
    splash.title('PyCalc')
    splash.resizable(False, False)
    splash.protocol('WM_DELETE_WINDOW', lambda: None)
    ttk.Label(splash, text='Launching PyCalc…', padding=(40, 30)).pack()
    splash.update_idletasks()
    width, height = splash.winfo_reqwidth(), splash.winfo_reqheight()
    x = (splash.winfo_screenwidth() - width) // 2
    y = (splash.winfo_screenheight() - height) // 2
    splash.geometry(f'{width}x{height}+{x}+{y}')
    splash.update()

    try:
        import ui

        calc_app = ui.MainWindow(root=root)
    except Exception as exc:
        messagebox.showerror('PyCalc could not launch', str(exc), parent=splash)
        root.destroy()
        raise
    splash.destroy()
    root.deiconify()
    calc_app.launch_ui()
