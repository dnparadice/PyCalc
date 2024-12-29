from decimal import Decimal

""" a module for formating numbers to engineering notation """

def eng_format(input: any, use_si_prefix: bool = False, zero_threshold: float = 1E-24) -> str:
    """ format a number to engineering notation that generates a string representation of the
     number that is formated to have exponent values divisible by 3. If use_prefixed is True,
     the return values will have a SI prefix from atto to yotta.
     @param input: the number to be formated
     @param use_si_prefix: if True, the return value will have a SI prefix
     @param zero_threshold: the smallest value that will be displayed, anything smaller will be displayed as 0"""
    # check if input is a number

    output = input  # copy input to output, output is morphed to the final output, input is not changed

    if not isinstance(output, (int, float)):
        raise ValueError("output must be an integer or float")
    if not isinstance(use_si_prefix, bool):
        raise ValueError("use_si_prefix must be a boolean")

    # check if output is zero
    if output == 0:
        return "0.0"

    # check if output is negative
    if output < 0:
        sign = "-"
        output = abs(output)
    else:
        sign = ""

    if isinstance(output, int):
        output = float(output)
        # num_str = str(output)
        # num_len = len(num_str)
        # mod3 = num_len % 3
        # div3 = num_len // 3
        # if mod3 != 0:
        #     zeros = ['0']*(3-mod3)
        #     num_str = ''.join(zeros) + num_str

    flt_str = str(output)

    # determine the exponent of the output
    if output < 1:  # check if output is less than 1
        # check if output is less than the zero threshold
        if output < zero_threshold:
            return f"{sign}0.0"  # ----------------------------------------------->



    else:
        exponent = 0
        while output >= 1000:
            output /= 1000
            exponent += 3

    # format return value:
    # ret = f"{sign}{output:.3f}{'E' if exponent else ''}{exponent:+d}"



    # check if output is less than 1
    # if output < 1:
    #     # check if outputis less than 1e-24
    #     if output < 1e-24:
    #         return f"{sign}0"
    #     exponent = -1
    #     while output < 1:
    #         output *= 10
    #         exponent -= 1
    # else:
    #     exponent = 0
    #     while output >= 1000:
    #         output /= 1000
    #         exponent += 3
    # # check if use_si_prefix is True
    # if use_si_prefix:
    #     large_prefixes = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"]
    #     small_prefixes = ["", "m", "µ", "n", "p", "f", "a", "z", "y"]
    #     if input < 1:
    #         prefixes = small_prefixes
    #     else:
    #         prefixes = large_prefixes
    #
    #     prefix = prefixes[exponent // 3]
    #     exponent %= 3
    #     if exponent < 0:
    #         exponent += 3
    # else:
    #     prefix = ""
    # return f"{sign}{output:.3f}{prefix}{'E' if exponent else ''}{exponent:+d}"


""" ------------------------------ mantissa and exponent formatting  --------------------------------- """


def get_exponent(number):
    """ returns the exponent of a number where the mantissa is represented by the function get_normalized_mantissa

    example 1:  passing 45 ..................returns: 1 (since 45 = 4.5 * 10^1)
    example 2:  passing 0.00045 .............returns: -4 (since 0.00045 = 4.5 * 10^-4)
    example 3:  passing 4.5 .................returns: 0 (since 4.5 = 4.5 * 10^0)
    example 4:  passing 0.45 .................returns: 0 (since 0.45 = 4.5 * 10^0)
    example 4:  passing 45000 .................returns: 4 (since 4.5 = 4.5 * 10^4)
    """
    (sign, digits, exponent) = Decimal(number).as_tuple()
    if abs(exponent) == len(digits):  # for numbers like 0.45
        return 0
    return len(digits) + exponent - 1


def get_normalized_mantissa(number):
    """ returns the normalized mantissa of a number (see warning below)

    Warning: this function is used in creating a string representation of a float, do not use the output
             of this function for calculations, instead use the Decimal class directly.

    example 1:  passing 45 .................returns: 4.5
    example 2:  passing 0.00045 ............returns: 4.499999999999999876834633206
    example 2:  passing 4.5 ................returns: 4.5
    example 3:  passing 0.45 ...............returns: 0.4500000000000000111022302463
    example 3:  passing 45000 ..............returns: 4.5



    """
    return Decimal(number).scaleb(-get_exponent(number)).normalize()


def format_eng(number_in, max_digits_displayed=7):
    """ format a number to engineering notation that generates a string representation of the
     number that is formated to have exponent values divisible by 3.
     @param number_in: the number to be formated
     @param max_digits_displayed:(=7) the maximum number of digits to display in the mantissa """

    if number_in == 0:
        return "0.0"  # ----------------------------------------------------------------------------------------------->

    abs_num_in = abs(number_in)
    mantissa_initial = get_normalized_mantissa(abs_num_in)
    exponent_initial = get_exponent(abs_num_in)
    print(f"abs_num_in: {abs_num_in}, mantissa: {mantissa_initial}, exponent: {exponent_initial}")

    # if the number is between 0.001 and 1000, trim long numbers and return the number as a string
    if 0.001 < abs(abs_num_in) < 1000:
        str_num = str(number_in)
        if len(str_num) > 7:
            str_num = str_num[:7]
        return str_num  # --------------------------------------------------------------------------------------------->

    # create a list of bytes from the mantissa
    bites = list(str(mantissa_initial).encode('utf-8'))
    print(f"bytes: {bites}")
    point = bites.pop(1)  # remove the decimal point (will be reinserted after determining the exponent)
    print(f"bytes: {bites}")

    # determine how to shift the decimal point and exponent
    div = abs(exponent_initial) // 3
    remainder = abs(exponent_initial) % 3
    print(f"div: {div}, remainder: {remainder}")

    # put the point back in the list
    if abs_num_in < 1:

        # define the number of places to shift the decimal point, if remainder is 0 (from %3 operation) no shift needed
        shift = 0 if remainder == 0 else (3 - remainder)
        insertion_idx = 1 + shift
        exp_final = exponent_initial - shift

    else:  # > 1
        insertion_idx = 1 + remainder
        exp_final = exponent_initial - remainder

    if len(bites) < insertion_idx:
        bites.extend([48] * max_digits_displayed)  # pad with plenty of zeros
    bites.insert(insertion_idx, point)

    # trim the list
    trim_point = max_digits_displayed
    if len(bites) < trim_point:
        trimmed = bites
    else:
        trimmed = bites[:trim_point]

    # convert the list back to a string
    new_num = f"{'-' if number_in < 0 else ''}{bytearray(trimmed).decode()}E{exp_final}"
    print(f"new_num: {new_num}, original: {number_in}")
    print(f"equal: {float(new_num) == number_in}")
    return new_num

def test_format_eng_equal(number_in, max_digits_displayed=7) -> bool:
    """ runs a self test on the number and checks if the number is *equal* to the formatted number. Since formatting
    the number may remove precision, the test will check if the number is equal to the original number
    based on how many digits are displayed in the mantissa.

    @param number_in: the number to be tested
    @param max_digits_displayed:(=7) the maximum number of digits to display in the mantissa, uses this value
                                     to determine the precision of the test
    """
    float_formatted = float(format_eng(number_in, max_digits_displayed=max_digits_displayed))

    try:
        # check sign
        if number_in < 0:
            assert float_formatted < 0

        if number_in == 0:
            assert float_formatted == 0

        if number_in > 0:
            assert float_formatted > 0

        # the format_eng function will remove 'precision' from the number, so we need to check if the number is close
        diff = abs(number_in - float_formatted)
        exponent = get_exponent(number_in)
        comp = float(f'1e{exponent - (max_digits_displayed-2)}')
        assert diff < comp

        # passed all the tests
        return True # ------------------------------------------------------------------------------------------------->

    except AssertionError:
        print(f"Equality Exception; number_in: {number_in}, float_formatted: {float_formatted}")
        return False


# demo code:
print(f"test: {test_format_eng_equal(-3.333333333333e-9, max_digits_displayed=3)}")
# input = 0.45
# print(f">>>input: {input} output: {eng_format(input, True)}")
# rsp = format_eng(input)
# print(f"rsp: {rsp}")
mnum = 45000
print(f"mantissa of {mnum}: {get_normalized_mantissa(mnum)}")
print(f"exponent of {mnum}: {get_exponent(mnum)}")