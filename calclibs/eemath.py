""" a library for ee related math functions. Since these functions are used in the calculator, you can either
define global variables or pass them as arguments. """

import math

# module variables, these can be re-defined at runtime by the calculator
pi = 3.141592653589793 # pi
_two_pi = 6.283185307179586 # 2 * pi
capacitance_f = 1e-12  # default capacitance in farads 1pF
inductance_h = 1e-9  # default inductance in henrys 1nH

# ------------------------------------------------------------------------------------------------------
#                                       RF Functions
# ------------------------------------------------------------------------------------------------------

def capacitor_reactance_ohms(frequency_hz: float):
    """ calculate the reactance of a capacitor in ohms (series capacitor)
    :param frequency_hz: the frequency in hertz if None, uses the global f_hz
    :param capacitance_f: the capacitance in farads, if none uses the global cap_f"""

    Xc = 1 / ( 2 * pi * frequency_hz * capacitance_f)
    return Xc

def inductor_reactance_ohms(frequency_hz: float):
    """ calculate the reactance of an inductor in ohms (series inductor)
    :param frequency_hz: the frequency in hertz
    :param inductance_h: the inductance in henrys """

    Xl = 2 * pi * frequency_hz * inductance_h
    return Xl

def capacitor_susceptance_siemens(frequency_hz: float):
    """ calculate the susceptance of a capacitor in siemens (shunt capacitor)
    :param frequency_hz: the frequency in hertz
    :param capacitance_f: the capacitance in farads """

    Bc = 2 * pi * frequency_hz * capacitance_f
    return Bc

def inductor_susceptance_siemens(frequency_hz: float):
    """ calculate the susceptance of an inductor in siemens (shunt inductor)
    :param frequency_hz: the frequency in hertz
    :param inductance_h: the inductance in henrys """

    Bl = 1 / ( 2 * pi * frequency_hz * inductance_h)
    return Bl

def dtr(degrees:float):
    """ convert degrees to radians, name kept small so direct typed usage in calculator is easier"""
    return degrees * (pi / 180.0)

def impedance_of_reflection_coefficient(gamma_complex: complex):
    """ calculates the impedance of the passed gamma (reflection coefficient) using the equation:
    Z = (1+Γ)/(1-Γ)
    :param gamma_complex: gamma like: complex(0.54,-0.9)"""

    Zi = (1 + gamma_complex) / (1 - gamma_complex)
    return Zi

def admittance_of_reflection_coefficient(gamma_complex: complex):
    """ calculates the impedance of the passed gamma (reflection coefficient) using the equation:
    Y = (1-Γ)/(1+Γ)
    :param gamma_complex: gamma like: complex(0.54,-0.9)"""

    Yi = (1 - gamma_complex) / (1 + gamma_complex)
    return Yi

def polar_to_complex(magnitude: float, angle_degrees: float):
    """ converts polar coordinates to complex number
    :param magnitude: the magnitude
    :param angle_degrees: the angle in degrees """

    angle_radians = dtr(angle_degrees)
    real = magnitude *  math.cos(angle_radians)
    imag = magnitude * math.sin(angle_radians)
    return complex(real, imag)
