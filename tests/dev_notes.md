# nice site about tk keybindings 
https://coderslegacy.com/python/tkinter-key-binding/l 


# a block of code example
'''python

def bindings(self):
self.master.bind('a', lambda event: print("A was pressed"))

        self.frame.bind('<Enter>', lambda event: print("Entered Frame"))
 
        self.label.bind('<Button-1>', lambda event: print("Mouse clicked the label"))
 
        self.button.bind('<Enter>', lambda event: self.color_change(self.button, "green"))
        self.button.bind('<Leave>', lambda event: self.color_change(self.button, "black"))
 
        self.entry.bind('<Key>', lambda event: self.pass_check())
        self.entry.bind('<FocusIn>', lambda event: self.Focused_entry())
        self.entry.bind('<FocusOut>', lambda event: self.UnFocused_entry())
'''

# namespace and logging 

It turns out that log and log are two different things. In software one logs a message and in math one logs a number
In the context of module namespace these tokens collide. Instead of explicitly making buttons for all math, I like 
to have the math functions in the namespace so I can dynamically use any math function. 


# Todos:
 - check text size before displaying on the UI and truncate if too long
 - add a right click option to view object
 - 
 - find beta testers 

future features:
