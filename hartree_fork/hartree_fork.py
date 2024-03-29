import alive_progress as prog
import numpy as np
from numpy import linalg
from numpy.typing import NDArray

from . import checks
from .inputs import HFInput


def orthogonalize(S: NDArray) -> NDArray:
    """
    Find a matrix X such that X.T @ S @ X = I

    Parameter
    ---------

    S:
        The overlap matrix.
        Must be positive definite and symmetric.

    Returns
    -------

    A 2D matrix.
    """

    assert checks.pos_def(S)
    assert checks.symmetric(S)

    # s is guarenteed to be > 0 because it's positive definite.
    s, U = linalg.eig(S)

    # Perform diagonalization using canonical orthogonalization.
    X = U @ np.diag(s**-0.5)

    assert np.allclose(X.T @ S @ X, np.eye(X.shape[1])), S

    return X


def density(C: NDArray, N: int):
    """
    Computes the density matrix D where
    D_uv = Sum_i C_ui C_vi, i <= electrons / 2

    Paramters
    ---------

    C:
        The coefficient matrix.

    N:
        The number of electrons (electrons / 2 is the number of occuppied orbitals).

    Returns
    -------

    The symmetric density matrix.
    """

    assert checks.square(C)
    occupied = C[:, : N // 2]

    return np.einsum("ui,vi->uv", occupied, occupied)


def fork(H: NDArray, D: NDArray, ijkl: NDArray):
    J = ijkl
    K = ijkl.transpose(0, 2, 1, 3)

    two_j_sub_k = 2 * J - K

    # Calculate the two electron terms.
    # s: sigma, l: lambda, u: mu, v: nu
    two_electron: NDArray = np.einsum("sl,uvls->uv", D, two_j_sub_k)

    return H + two_electron


def energy(D: NDArray, H: NDArray, F: NDArray) -> float:
    return (D * (H + F)).sum()


def hartree_fork(hf_input: HFInput) -> float:
    # Number of orbitals.
    N = hf_input.electrons

    # Hamiltonian.
    H = hf_input.kinetic + hf_input.potential

    # The 4 integrals (ij|kl).
    ijkl = hf_input.ijkl

    # The overlap matrix.
    S = hf_input.overlap

    # Density is initialized to 0 if it's not provided.
    if (D := hf_input.density_init) is None:
        D = np.zeros(shape=[N, N])

    # N-N repulsion energy
    vnn = hf_input.vnn

    threshold = hf_input.converge
    iterations = hf_input.iterations

    # orthogonalizer = ortho.get("canonical")

    E = 0

    with prog.alive_bar(iterations) as bar:
        for _ in range(iterations):
            bar()

            # Calculate the F, X matrices, update energy E
            F = fork(H, D, ijkl)
            X = orthogonalize(S)
            E = energy(D, H, F)

            # Fp: F' = X.T @ F @ X
            Fp = X.T @ F @ X

            # Cp: C', since F'C' = eC', C' is the eigen vectors of F', C=XC'
            _, Cp = linalg.eig(Fp)
            C = X @ Cp

            D_new = density(C, N)

            # Check difference in density
            if ((D - D_new) ** 2).sum() < threshold:
                bar(skipped=True)
                break

            D = D_new

    return E + vnn
