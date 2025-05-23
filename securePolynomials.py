from asyncio import Future
from itertools import accumulate, repeat
from mpyc.runtime import mpc

def format_polynomial_term(coefficient, degree):

    x_power = f"x^{degree}" if degree >= 2 else "x" if degree == 1 else ""

    if coefficient:
        return str(coefficient) + x_power + " + "

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

    def __neg__(self):

        return SecurePolynomial([-a for a in self.coefficients])

    def __add__(self, other):

        assert self.dtype == other.dtype

        if self.degree < other.degree:
            return other.__add__(self)

        lower_coefficients = [a + b for (a,b) in zip(self.coefficients, other.coefficients)]
        higher_coefficients = self.coefficients[other.degree + 1 : self.degree + 1]

        return SecurePolynomial(lower_coefficients + higher_coefficients)

    def __sub__(self, other):

        return self + (-other)

    def __mul__(self, other):

        assert self.dtype == other.dtype
        degree = self.degree + other.degree

        mins_self  = (other.degree + 1)*(0,) + tuple(range(1, self.degree  + 1))
        mins_other = (self.degree  + 1)*(0,) + tuple(range(1, other.degree + 1))

        maxs_self   = tuple(range(1, self.degree  + 1)) + (other.degree + 1)*(self.degree  + 1,)
        maxs_other  = tuple(range(1, other.degree + 1)) + (self.degree  + 1)*(other.degree + 1,)
        
        ranges_self  = [ self.coefficients[min_:max_] for (min_, max_) in zip(mins_self,  maxs_self) ]
        ranges_other = [other.coefficients[min_:max_] for (min_, max_) in zip(mins_other, maxs_other)]

        coefficients = [mpc.in_prod(range_self, list(reversed(range_other))) for (range_self, range_other) in zip(ranges_self, ranges_other)]

        return SecurePolynomial(coefficients)

    @mpc.coroutine
    async def evaluate_on_secret(self, x_s):

        assert type(x_s) == self.dtype
        await mpc.returnType(self.dtype)

        res = self.coefficients[-1]

        for a in reversed(self.coefficients[:-1]):
            res = x_s*res + a

        return res

    @mpc.coroutine
    async def evaluate_on_public(self, x_p):

        await mpc.returnType(self.dtype)
        
        powers = accumulate(self.degree * [x_p], type(x_p).__mul__, initial=x_p**0)

        return mpc.sum([a * power for (a, power) in zip(self.coefficients, powers)])


if __name__ == "__main__":

    dtype = mpc.SecInt()

    deg1, deg2 = 2, 3

    mpc.run(mpc.start())
    
    p1 = SecurePolynomial([mpc.random.randint(dtype, -63, 64) for _ in range(deg1 + 1)])
    p2 = SecurePolynomial([mpc.random.randint(dtype, -63, 64) for _ in range(deg2 + 1)])

    p3 = p1 + p2 
    p4 = p1 - p2
    p5 = p1 * p2

    x_s = mpc.random.randint(dtype, -63, 64)
    x_p = 42

    y1 = mpc.run(mpc.output(p1.evaluate_on_secret(x_s)))
    y2 = mpc.run(mpc.output(p2.evaluate_on_public(x_p)))
    y3 = mpc.run(mpc.output(p3.evaluate_on_secret(x_s)))
    y4 = mpc.run(mpc.output(p4.evaluate_on_public(x_p)))
    y5 = mpc.run(mpc.output(p4.evaluate_on_secret(x_s)))

    print(f"evaluating p1 on secret value x_s gives {y1}")
    print(f"evaluating p2 on public value x_p gives {y2}")
    print(f"evaluating p1+p2 on secret value x_s gives {y3}")
    print(f"evaluating p1-p2 on public value x_p gives {y4}")
    print(f"evaluating p1*p2 on public value x_s gives {y5}")

    p1_public = [mpc.run(mpc.output(x)) for x in p1.coefficients]
    p2_public = [mpc.run(mpc.output(x)) for x in p2.coefficients]
    p3_public = [mpc.run(mpc.output(x)) for x in p3.coefficients]
    p4_public = [mpc.run(mpc.output(x)) for x in p4.coefficients]
    p5_public = [mpc.run(mpc.output(x)) for x in p5.coefficients]

    print("revealed values:")

    print(f"p1(x) = {format_polynomial(p1_public)}")
    print(f"p2(x) = {format_polynomial(p2_public)}")
    print(f"(p1+p2)(x) = {format_polynomial(p3_public)}")
    print(f"(p1-p2)(x) = {format_polynomial(p4_public)}")
    print(f"(p1*p2)(x) = {format_polynomial(p5_public)}")

    print(f"x_s = {mpc.run(mpc.output(x_s))}")
    print(f"x_p = {x_p}")

    mpc.run(mpc.shutdown())
