from asyncio import Future
from itertools import repeat
from mpyc import mpctools
from mpyc.runtime import mpc

def format_polynomial_term(coefficient, degree):

    x = f"x^{degree}" if degree >= 2 else "x" if degree == 1 else ""

    if coefficient:
        return str(coefficient) + x + " + "

    else:
        return ""

def format_polynomial(coefficients, degree=0):
    
    term = format_polynomial_term(coefficients[0], degree)

    if len(coefficients) == 1:
        return term[:-3]

    else:
        return term + format_polynomial(coefficients[1:], degree + 1)

class SecurePolynomial:

    def __init__(self, coefficients=None, degree=None, dtype=None):

        if coefficients is not None:
            coefficients = list(coefficients)
            degree = len(coefficients) - 1
            dtype = type(coefficients[0])

        assert degree is not None
        assert dtype is not None

        self.degree = degree
        self.dtype = dtype
        self.coefficients = coefficients

    def __add__(self, other):

        assert self.dtype == other.dtype

        if self.degree < other.degree:
            return other.__add__(self)

        lower_coefficients = [a + b for (a,b) in zip(self.coefficients, other.coefficients)]
        higher_coefficients = self.coefficients[other.degree + 1 : self.degree + 1]

        return SecurePolynomial(lower_coefficients + higher_coefficients)

    def __sub__(self, other):

        raise NotImplementedError

    def __mul__(self, other):

        assert self.dtype == other.dtype
        degree = self.degree + other.degree
        
        raise NotImplementedError

    @mpc.coroutine
    async def evaluate_on_secret(self, value):

        assert type(value) == self.dtype
        await mpc.returnType(self.dtype)
        
        step = lambda x, y: value*x + y

        return mpctools.reduce(step, reversed(self.coefficients[:-1]), self.coefficients[-1])

    @mpc.coroutine
    async def evaluate_on_public(self, value):

        await mpc.returnType(self.dtype)
        
        powers = map(pow, repeat(value), range(self.degree + 1))
        powers = map(self.dtype, powers)
        powers = list(powers)

        return mpc.in_prod(self.coefficients, powers)


if __name__ == "__main__":

    dtype = mpc.SecInt()

    deg1, deg2 = 2, 3

    mpc.run(mpc.start())
    
    p1 = SecurePolynomial([mpc.random.randint(dtype, -63, 64) for _ in range(deg1 + 1)])
    p2 = SecurePolynomial([mpc.random.randint(dtype, -63, 64) for _ in range(deg2 + 1)])

    p3 = p1 + p2 
#    p4 = p1 * p2

    x_s = mpc.random.randint(dtype, -63, 64)
    x_p = 42

    y1 = mpc.run(mpc.output(p1.evaluate_on_secret(x_s)))
    y2 = mpc.run(mpc.output(p2.evaluate_on_public(x_p)))
#    y1 = mpc.run(mpc.output(p3.evaluate_on_secret(x_s)))
#    y2 = mpc.run(mpc.output(p4.evaluate_on_public(x_p)))

    print(f"evaluating p1 on secret value x_s gives {y1}")
    print(f"evaluating p2 on public value x_p gives {y2}")
#    print(f"evaluating p1+p2 on secret x_s gives {y3}")
#    print(f"evaluating p1*p2 on public x_p gives {y2}")

    p1_public = [mpc.run(mpc.output(x)) for x in p1.coefficients]
    p2_public = [mpc.run(mpc.output(x)) for x in p2.coefficients]
    p3_public = [mpc.run(mpc.output(x)) for x in p3.coefficients]
#    p4_public = [mpc.run(mpc.output(x)) for x in p4.coefficients]

    print("revealed values:")

    print(f"p1(x) = {format_polynomial(p1_public)}")
    print(f"p2(x) = {format_polynomial(p2_public)}")
    print(f"p3(x) = {format_polynomial(p3_public)}")
#    print(f"p4(x) = {format_polynomial(p4_public)}")

    print(f"x_s = {mpc.run(mpc.output(x_s))}")
    print(f"x_p = {x_p}")

    mpc.run(mpc.shutdown())
