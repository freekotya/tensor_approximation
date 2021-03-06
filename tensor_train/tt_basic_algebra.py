import numpy as np
import mpmath as mp
from mpmath import workdps, mpf
import math

from numpy import dot, zeros, ones, eye, identity as I, reshape, tensordot, kron
from numpy.linalg import svd, norm, qr
from utils import frobenius_norm

from core import TensorTrain


def tt_zeros(n):
    # TODO what shall we do if we have one/two dimensional tensors?
    return TensorTrain.from_cores([np.zeros(elements)[np.newaxis, ..., np.newaxis] for elements in n])


def tt_negate(tt):
    A = TensorTrain(tt)
    A.cores[0] = -A.cores[0]
    return A


def tt_add(tt, other):
    A = TensorTrain()
    if tt.n != other.n:
        raise Exception('tensor dimensions ' + str(tt.n) + ' and ' + str(other.n) + "didn't match!")
    A.d = tt.d
    A.n = tt.n
    A.r = tt.r + other.r
    if tt.r[0] == other.r[0]:
        A.r[0] = tt.r[0]
    else:
        raise Exception("First ranks must match!")
    if tt.r[-1] == other.r[-1]:
        A.r[-1] = tt.r[-1]
    else:
        raise Exception("Last ranks must match!")

    A.cores = []

    next_core = np.zeros((A.r[0], A.n[0], A.r[1]))
    next_core[:, :, :tt.r[1]] = tt.cores[0]
    next_core[:, :, tt.r[1]:] = other.cores[0]
    A.cores.append(next_core)

    for i in xrange(1, A.d - 1):
        next_core = zeros((A.r[i], A.n[i], A.r[i+1]))
        next_core[:tt.r[i], :, :tt.r[i+1]] = tt.cores[i]
        next_core[tt.r[i]:, :, tt.r[i+1]:] = other.cores[i]
        A.cores.append(next_core)

    next_core = np.zeros((A.r[-2], A.n[-1], A.r[-1]))
    next_core[:tt.r[-2], :, :] = tt.cores[-1]
    next_core[tt.r[-2]:, :, :] = other.cores[-1]
    A.cores.append(next_core)
    return A


def tt_mul_scalar(tt, scalar, rmul=False):
    A = TensorTrain(tt)
    if scalar != 0:
        if rmul:
            A.cores[-1] *= scalar
        else:
            A.cores[-1] *= scalar
    else:
        for k in xrange(A.cores):
            A.cores[k] = np.zeros(A.n[k])[np.newaxis, :, np.newaxis]
            A.cores[k] = reshape(A.cores[k], (1, A.n[k], 1))
    return A

def tt_sub(tt, other):
    return tt + -other


def tt_convolve(tt, U):
    if len(U) != tt.d:
        raise Exception('Tensor of rank d must convolve with d vectors!')
    if not all([a == b for a, b in zip(tt.n, [u.size for u in U])]):
        raise Exception('Tensor must convolve with vectors of proper dimensions!')
    v = 1
    for k in xrange(tt.d):
        next_matrix = tensordot(tt.cores[k], U[k], [1, 0])
        v = dot(v, next_matrix)
    # And then, we have an imitative ranks of 1 from left and right, so erase them
    return v[0, 0]


def tt_hadamard_prod(tt, other):
    assert False
    A = TensorTrain()
    if tt.n != other.n:
        raise Exception('tensor dimensions ' + str(tt.n) + ' and ' + str(other.n) + "doesn't match!")
    A.d = tt.d
    A.n = tt.n
    A.r = tt.r * other.r

    A.cores = []

    for k in xrange(A.d):
        self_r = tt.r[k]
        self_r1 = tt.r[k+1]
        other_r = other.r[k]
        other_r1 = other.r[k+1]
        next_core = np.zeros((self_r * other_r, tt.n[k], self_r1 * other_r1))
        for i in xrange(tt.n[k]):
            next_core[:, i, :] = kron(tt.cores[k][:, i, :], other.cores[k][:, i, :])
        A.cores.append(next_core)
    return A


def tt_scalar_product(tt ,other):
    if tt.n != other.n:
        raise Exception('dimensions of tensors must be equal')

    first = np.array(tt.cores[0], dtype=np.float128).reshape(tt.cores[0].shape[1:])
    second = np.array(other.cores[0], dtype=np.float128).reshape(other.cores[0].shape[1:])
    v = np.sum([np.kron(first[i], second[i]) for i in xrange(tt.n[0])], axis=0)
    for k in xrange(1, tt.d):
        A = np.array(tt.cores[k], dtype=np.float128)
        B = np.array(other.cores[k], dtype=np.float128)
        subvectors = [np.dot(v, np.kron(A[:, i, :], B[:, i, :])) for i in xrange(tt.n[k])]
        v = np.sum(subvectors, axis=0)
    # I don't know now how to avoid unstability of scalar product on tensors that are close to zero
    return np.abs(v[0])


def tt_outer_product(tt, other):
    outer_cores = [core.copy() for core in tt.cores] + [core.copy() for core in other.cores]
    TensorTrain.from_cores(outer_cores)


def tt_scalar_product_old(tt, other):
    A = tt * other
    return A.tt_convolve([np.ones(dimension) for dimension in A.n])

"""
# scalar product comparison - tt_scalar_product and tt_scalar_product_old are unstable on
# tensors that are close to zero
def xxx(begin, end):
    from tensor_train import TensorTrain, frobenius_norm
    from tensor_train.tt_basic_algebra import tt_scalar_product, tt_scalar_product_old
    from tests.sinus_cores import sym_sum_sinus_tensor
    res = []
    for i in xrange(begin, end):
        A = sym_sum_sinus_tensor(i)
        B = TensorTrain(A)
        #C = A
        C = A - B
        CC = C.full_tensor()
        raw = frobenius_norm(CC)
        sc = tt_scalar_product(C, C)
        sch = tt_scalar_product_old(C, C)
        print "i: {i}, sc: {sc}, sch: {sch}, raw: {raw}".format(i=i, sc=sc, sch=sch, raw=raw)
        res.append((i, sc, sch, raw))
    return res
"""


"""
Abandoned function - abandon for better times
def tt_add(tt, other):
    dps=500
    A = TensorTrain()
    if tt.n != other.n:
        raise Exception('tensor dimensions ' + str(tt.n) + ' and ' + str(other.n) + "didn't match!")
    A.d = tt.d
    A.n = tt.n
    A.r = tt.r + other.r
    if tt.r[0] == other.r[0]:
        A.r[0] = tt.r[0]
    else:
        raise Exception("First ranks must match!")
    if tt.r[-1] == other.r[-1]:
        A.r[-1] = tt.r[-1]
    else:
        raise Exception("Last ranks must match!")

    A.cores = []

    '''
    if tt.normed() and other.normed():
        dps=500
        A._normed = True
        with workdps(dps):
            A.norm = mpf('1.0')
        next_core = np.zeros((A.n[0], A.r[1]))
        next_core[:, :tt.r[1]] = tt.cores[0]
        next_core[:, tt.r[1]:] = other.cores[0]
        next_core, s, V = svd(next_core, full_matrices=False)
        c = frobenius_norm(s)
        s /= c
        with workdps(dps):
            A.norm *= c
        next_core = next_core[np.newaxis, ...]
        A.cores.append(next_core)
        weight = dot(np.diag(s), V)

        for i in xrange(1, A.d - 1):
            next_core = zeros((A.r[i], A.n[i], A.r[i+1]))
            next_core[:tt.r[i], :, :tt.r[i+1]] = tt.cores[i]
            next_core[tt.r[i]:, :, tt.r[i+1]:] = other.cores[i]
            next_core = reshape(next_core, (A.r[i], A.n[i] * A.r[i+1]))
            next_core = dot(weight, next_core)
            next_core = reshape(next_core, (A.r[i] * A.n[i], A.r[i+1]))
            next_core, s, V = svd(next_core, full_matrices=False)
            assert s.size == A.r[i+1]
            c = frobenius_norm(s)
            s /= c
            with workdps(dps):
                A.norm *= c
            A.cores.append(next_core.reshape((A.r[i], A.n[i], A.r[i+1])))
            weight = dot(np.diag(s), V)
        with workdps(dps):
            c_min, c_max = min(tt.norm, other.norm), max(tt.norm, other.norm)
            first_max = tt.norm == c_max
            c_diff = c_min / c_max

        next_core = np.zeros((A.r[-2], A.n[-1], A.r[-1]))
        next_core[:tt.r[-2], :, :] = tt.cores[-1] if first_max else tt.cores[-1] * c_diff
        next_core[tt.r[-2]:, :, :] = other.cores[-1] if not first_max else other.cores[-1] * c_diff
        next_core /= np.sqrt(2)
        with workdps(dps):
            A.norm *= np.sqrt(2)
            A.norm *= c_max
        next_core = reshape(next_core, (A.r[-2], A.n[-1]))
        next_core = dot(weight, next_core)
        next_core = next_core[:, :, np.newaxis]
        A.cores.append(next_core)
        print frobenius_norm(TensorTrain.from_cores(A.cores))
        return A
    '''

    next_core = np.zeros((A.r[0], A.n[0], A.r[1]))
    next_core[:, :, :tt.r[1]] = tt.cores[0]
    next_core[:, :, tt.r[1]:] = other.cores[0]
    A.cores.append(next_core)

    for i in xrange(1, A.d - 1):
        next_core = zeros((A.r[i], A.n[i], A.r[i+1]))
        next_core[:tt.r[i], :, :tt.r[i+1]] = tt.cores[i]
        next_core[tt.r[i]:, :, tt.r[i+1]:] = other.cores[i]
        A.cores.append(next_core)

    if tt.normed() and other.normed():
        with workdps(dps):
            c_min, c_max = min(tt.norm, other.norm), max(tt.norm, other.norm)
            first_max = tt.norm == c_max
            c_diff = c_min / c_max
            NORM = c_max
        next_core = np.zeros((A.r[-2], A.n[-1], A.r[-1]))
        next_core[:tt.r[-2], :, :] = tt.cores[-1] if first_max else tt.cores[-1] * c_diff
        next_core[tt.r[-2]:, :, :] = other.cores[-1] if not first_max else other.cores[-1] * c_diff
        A.cores.append(next_core)
        t = A.tt_round(eps=0)
        print frobenius_norm(t)
        with workdps(dps):
            t.norm *= NORM
        return t
    else:
        next_core = np.zeros((A.r[-2], A.n[-1], A.r[-1]))
        next_core[:tt.r[-2], :, :] = tt.cores[-1]
        next_core[tt.r[-2]:, :, :] = other.cores[-1]
        A.cores.append(next_core)
        return A
"""