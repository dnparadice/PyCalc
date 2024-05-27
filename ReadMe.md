![PyCalc - Lists and Plot](media\PyCalc-ListsandPlot.jpg?)

## Hello and welcome to PyCalc, the RPN ~~calculator~~ ~~IDE~~ progam that loves Python

This project is an experiment to see what happens when you take a Python interpreter, and put an RPN calculator style
UI wrapper around it. 
I have spent years using Python Terminal and Jupyter Notebooks and while each one has its strengths, neither one
offers the simplicity or immediacy of a good old fashion calculator when working math problems. But a calculator 
lacks the history and exposition of a Jupyter notebook. 
Why not incorporate the strengths of both a calculator
and a Jupyter Notebook into one App. 
So this project was born and has become a go-to tool for daily engineering math and quick Python scripting.

### Highlights

#### General
- [x] Feature filled RPN style calculator with stack view, history, variables and plotting 
- [x] Novel RPN style interface for interacting with a live Pyton interpreter
- [x] Built in support for Math, NumPy and Matplotlib libraries 
- [x] Import any Python module and its functions are available for use in the calculator
- [x] Python Interpreter backend for full access to Python language features directly on the stack 

#### User Interface 
- [x] Customizable Tkinter.ttk UI with Stack View, Variable View, and History View
- [x] Support for copy and pasting between excel and the calculator
- [x] Session history with undo and redo
- [x] Store variables of any type including functions and classes 
- [x] Save / Restore sessions and state

### How to use the calculator
At the most basic level, the UI is an RPN calculator so if you know how to use an RPN calculator 
it acts as expected. If you don't know how to use an RPN calculator then please use the internet to 
update your knowledge base, also you can type out expressions in this calculator and it will operate 
like a 'normal' calculator.

### Examples (using the UI)

#### basic math

1) press: '1'
2) press: 'enter' -- either on the UI or the keyboard
3) press: '2'
4) press: '+'
5) The result of the operation (1+2) is displayed in the stack view in the X position as '3'

#### using math functions

1) press: '2'
2) press: 'enter'
3) press: 'log'  -- Note that you can either press the 'log' button or type 'log' and press enter
4) The result of the operation (log(2)) is displayed in the stack view in the X position as '0.6931471805599453'

#### using variables

1) press: '2'
2) press: 'enter'
3) type: 'my_var='
4) press: 'enter'
5) The value '2' is stored in the variable 'my_var' and is now displayed in the variable view

#### Using list and array functions with NumPy and Lists

1) press: '2'
2) press: 'enter'
3) press: '3'
4) press: 'enter'
5) press: '4'
6) press: 'stack to list' -- this will convert the stack to a list [2, 3, 4] and display it in the stack view
7) enter: 'np.array' -- this will convert the list to a NumPy array and display it in the stack view
8) enter: 'my_array='
9) press: 'enter' -- this will store the array in the variable 'my_array' and display it in the variable view
10) enter: 'sin' 
11) press: 'enter' -- this will apply the sin function to each element of the array and display the result in the stack view

#### Plotting

1) Continuing from the "Using list and array functions with NumPy and Lists" example 
2) enter: 'my_array'
3) press: 'plot' -- this will plot the array using matplotlib and display the plot in a new window

#### Non RPN style calculations

1) enter: '(1+1)' -- the parentheses let the calculator know that this is a math expression
2) press: 'enter' -- this will evaluate the expression 1+1 and display the result '2' in the stack view

#### Making lists 

This example exposes the underlying power of the calculator to interact directly with the Python interpreter and how
imported Python module's functions can be called directly from the stack to operate on the stack. 

1) enter: '[sin(x/3) for x in range(200)]'
2) press: 'enter' -- this will create a list of sin(x/3) for the range x = 0 to x = 199
3) enter: 'np.array'
4) press: 'enter' -- this will convert the list to a NumPy array and display it in the stack view
5) enter: 'tan'
6) press: 'enter' -- this is the equivalent of calling np.tan(<array at X>) the calculator loads in all 
functions from the NumPy library so you can call them directly from the stack by typing the function name and then 
pressing enter.



#### Notes on Usage 
1) Due to years of using RPN calculators I have adopted the terminology of X=stack[0], Y=stack[1], Z=stack[2] and 
T=stack[3] (thanks HP). In the code I often refer to X and Y as in 'pow(X, Y)' which is equivalent to 
pow(stack[0], stack[1]).
2) You don't need buttons to use the math functions. Just type the argument first then the function. 
3) Calculators typically use the notation ln = log base e and log = log base 10. Since this is a 
calculator, it matches the use of ln=log base e and log=log base 10. This means that there is a 
wrapper on the math.log function so calling log(3, 10) throws an error. If you want to call like 
this you must explicitly call: math.log(3, 10) as the builtin log method (for this calculator) is 
always base 10.

### Future Features 
- Installer for the UI 
- better array / tensor viewer 

### If you made it this far

One of the additional goals I had for this project was to explore the use of Tkinter. I have used various 
other software packages to create UIs and I wanted to give Tkinter a turn. So far tkinter has been fast and easy
to work with. 