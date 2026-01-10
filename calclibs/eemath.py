""" a library for ee related math functions. Since these functions are used in the calculator, you can either
define global variables or pass them as arguments. """

import math

# module variables, these can be re-defined at runtime by the calculator
pi = 3.141592653589793 # pi
_two_pi = 6.283185307179586 # 2 * pi
capacitance_f = 1e-12  # default capacitance in farads 1pF
inductance_h = 1e-9  # default inductance in henrys 1nH
Z0 = 50.0  # default characteristic impedance in ohms

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

def complex_to_polar_deg(cnum: complex):
    """ converts a complex number to polar coordinates
    :param cnum: the complex number
    :return : tuple (magnitude, angle in degrees) """

    magnitude = abs(cnum)
    angle_radians = math.atan2(cnum.imag, cnum.real)
    angle_degrees = angle_radians * (180.0 / pi)
    return magnitude, angle_degrees

#    ------------- Transmission Lines  ----------------

def admittance_of_open_stub(electrical_length_degrees: float, Zos=50):
    """ calculates the admittance of an open stub transmission line
    :param electrical_length_degrees: the electrical length in degrees must be < 90 degrees
    :param Zos: the characteristic impedance of the open stub, default is 50 ohms """
    Bos = math.tan(electrical_length_degrees)/Zos
    return Bos

def admittance_of_shorted_stub(electrical_length_degrees: float, Zss=50):
    """ calculates the admittance of a shorted stub transmission line
    :param electrical_length_degrees: the electrical length in degrees must be < 90 degrees
    :param Zss: the characteristic impedance of the shorted stub, default is 50 ohms """
    Bss = -1/(Zss * math.tan(electrical_length_degrees))
    return Bss

def s_param_to_dB(s_param: complex):
    """ converts an S parameter to dB
    :param s_param: the s-parameter as a complex number """
    magnitude = abs(s_param)
    if magnitude == 0:
        return -math.inf
    dB = 10 * math.log10(magnitude ** 2)
    return dB

def s_param_to_missmatch_loss(s_param: complex):
    """ converts an S-parameter to missmatch loss in dB
    :param s_param: the s-parameter like S11, S22, as a complex number """
    magnitude = abs(s_param)
    if magnitude == 1:
        return -math.inf
    ML_dB = -10 * math.log10(1 - magnitude ** 2)
    return ML_dB

def series_caps_solved_for_match(Cs: float, Cx: float):
    """
    Uses local variables Cs for the total capacitance desired, and Cx as the existing capacitance, solved for the 
    matching capacitance Cm. If Cm is greater than Cx then adding a cap to get the desired Cs.
    :param Cs: total capacitance desired in farads
    :param Cx: existing capacitance in farads
    :return: Cm: matching capacitance in farads
    """
    Cm = (Cs*Cx) / (Cx-Cs)
    return Cm
