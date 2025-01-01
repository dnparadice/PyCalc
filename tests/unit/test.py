import calc
import unittest
import math
import engnum

pi_50 = '3.14159265358979323846264338327950288419716939937510'
c = calc.Calculator()

class TestAllCalculatorFunctions(unittest.TestCase):

    def test_undo(self):
        c.clear_stack()
        c.user_entry('1')
        c.user_entry('enter')
        c.user_entry('2')
        c.user_entry('enter')
        c.user_entry('3')
        c.user_entry('enter')
        c.user_entry('4')
        c.user_entry('enter')
        c.user_entry('5')
        c.user_entry('enter')
        c.user_entry('undo')  # 1.a
        c.user_entry('enter')
        c.user_entry('undo')  # 1.b
        c.user_entry('enter')
        c.user_entry('undo')  # 2.a
        c.user_entry('enter')
        c.user_entry('undo')  # 2.b
        c.user_entry('enter')
        c.user_entry('undo')  # 3.a
        c.user_entry('enter')
        c.user_entry('undo')  # 3.b
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        print(f"STACK: {c.return_stack_for_display()}")
        self.assertEqual(2, num)



class TestUserEntry(unittest.TestCase):

    def test_strings(self):

        # check pi
        c.user_entry('pi')
        c.user_entry('enter')
        pi = c.return_stack_for_display(0)
        self.assertEqual(isinstance(pi, float), True)
        spi = str(pi)
        self.assertEqual(spi, pi_50[:len(spi)])

        # check float
        c.user_entry('45.00001e-12')
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        self.assertEqual(math.isclose(num, 45.00001e-12), True)

        # check int
        c.user_entry('123456789')
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        self.assertEqual(isinstance(num, int), True)
        self.assertEqual(num, 123456789)

        # check math entry
        c.user_entry('(sin(pi/2)**2+4.754/4-9)')
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        self.assertEqual(math.isclose(num, -13623/2000, rel_tol=1e-9), True)

        # check imports
        c.user_entry('import random')
        c.user_entry('enter')
        c.user_entry('random.seed(4321)')
        c.user_entry('enter')
        c.user_entry('random.randint(5, 5000000000)')
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        self.assertEqual(num, 1092128448)

        # check lists
        c.user_entry('[1, 2, 3]')
        c.user_entry('enter')
        c.user_entry('sum')
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        self.assertEqual(num, 6)

        # check arrays
        c.clear_stack()
        c.user_entry('1')
        c.user_entry('enter')
        c.user_entry('2')
        c.user_entry('enter')
        c.user_entry('3')
        c.stack_to_array()
        c.user_entry('10')
        c.user_entry('*')
        c.user_entry('sum')
        c.user_entry('enter')
        num = c.return_stack_for_display(0)
        self.assertEqual(num, 60)

class test_engnum_lib(unittest.TestCase):

    def test_zeros(self):
        # check zero
        self.assertEqual(engnum.format_eng(0.00000), '0.0')
        self.assertEqual(engnum.format_eng(00000.0), '0.0')
        self.assertEqual(engnum.format_eng(00000.0E-0), '0.0')
        self.assertEqual(engnum.format_eng(0), '0.0')
        self.assertEqual(engnum.format_eng(0e0), '0.0')
        self.assertEqual(engnum.format_eng(0e-0), '0.0')
        self.assertEqual(engnum.format_eng(-0e-0), '0.0')
        self.assertEqual(engnum.format_eng(00000000E0), '0.0')
        self.assertEqual(engnum.format_eng(0000.0000E-0), '0.0')
        self.assertEqual(engnum.format_eng(-0000.0000E-0), '0.0')
        self.assertEqual(engnum.format_eng(00), '0.0')
        self.assertEqual(engnum.format_eng(0.0), '0.0')
        self.assertEqual(engnum.format_eng(-0.0), '0.0')

    def test_negatives(self):
        # check negative non zero numbers defined by different exponent values
        self.assertEqual(engnum.format_eng(-1.E-3), '-1.00000E-3')
        self.assertEqual(engnum.format_eng(-10.0E-4), '-1.00000E-3')
        self.assertEqual(float(engnum.format_eng(-.003)), -.003)
        self.assertEqual(float(engnum.format_eng(-.003e1)), -.003e1)
        self.assertEqual(float(engnum.format_eng(-.003e-12)), -.003e-12)
        self.assertEqual(float(engnum.format_eng(-13.003e-12)), -13.003e-12)
        self.assertEqual(float(engnum.format_eng(-13.003875678615876e-12)), -13.003875678615876e-12)





if __name__ == '__main__':
    unittest.main()
