import calc


c = calc.Calculator()

def test_basic_math():

    c.user_entry('pi')
    c.user_entry('enter')
    c.user_entry('2')
    c.user_entry('1')
    c.user_entry('E')

    c.user_entry('6')
    c.user_entry('+')
    c.user_entry('enter')
    c.user_entry('45.321E-3')
    c.user_entry('/')
    c.user_entry('[1, 2, 3]')
    c.user_entry('enter')
    c.user_entry('2')
    c.user_entry('*')
    c.user_entry('+')


if __name__ == '__main__':
    test_basic_math()

