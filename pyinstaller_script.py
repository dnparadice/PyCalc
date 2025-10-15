import PyInstaller.__main__


if __name__ == '__main__':


    # see: https://pyinstaller.org/en/stable/usage.html
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
    ])