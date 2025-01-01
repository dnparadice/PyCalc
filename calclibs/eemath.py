""" a library for ee related math functions. Since these functions are used in the calculator, you can either
define global variables or pass them as arguments. """

# global variables, these are re-defined at runtime by the calculator
f_hz = None # frequency in hertz
cap_f = None # capacitance in farads
_two_pi = 6.283185307179586 # 2 * pi

# capacitors

def cap_reactance_ohms(capacitance_f: float|None=None, frequency_hz:float|None=None, ):
    """ calculate the reactance of a capacitor in ohms
    @param frequency_hz: the frequency in hertz if None, uses the global f_hz
    @param capacitance_f: the capacitance in farads, if none uses the global cap_f"""
    if capacitance_f is None:
        capacitance_f = cap_f
    if frequency_hz is None:
        frequency_hz = f_hz

    return 1.0 / (_two_pi * frequency_hz * capacitance_f)