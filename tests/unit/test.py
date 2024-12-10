import calc
import unittest
import math

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



if __name__ == '__main__':
    unittest.main()
