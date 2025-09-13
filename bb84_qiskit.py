# BB84 Qiskit implementation — Aer (local) + IBM Runtime (online)
# Generated: 2025-09-12T09:06:03.569557Z

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

def create_random_generator(seed: Optional[int] = None) -> np.random.Generator:
    return np.random.default_rng(seed)

# Generates a random array of m bits (0 or 1).
def create_random_bits(rng: np.random.Generator, m: int) -> np.ndarray:
    return rng.integers(0, 2, size=m, dtype=np.int8)

# Generates a random array of m bases (0 for Z, 1 for X).
def create_random_bases(rng: np.random.Generator, m: int) -> np.ndarray:
    return rng.integers(0, 2, size=m, dtype=np.int8)

# Constructs a quantum circuit for a single BB84 transmission.
def one_qubit_bb84_circuit(bit: int, alice_basis: int, bob_basis: int) -> QuantumCircuit:
    qc = QuantumCircuit(1, 1)
    if alice_basis == 0:
        if bit == 1:
            qc.x(0)
    else:
        qc.h(0)
        if bit == 1:
            qc.z(0)
    if bob_basis == 1:
        qc.h(0)
    qc.measure(0, 0)
    return qc

# Runs a batch of circuits on the local AerSimulator.
def run_single_shot_batch(circuits: List[QuantumCircuit]) -> List[int]:
    sim = AerSimulator()
    tcs = [transpile(c, sim) for c in circuits]
    res = sim.run(tcs, shots=1).result()
    bits = []
    for i in range(len(tcs)):
        counts = res.get_counts(i)
        bits.append(int(next(iter(counts))))
    return bits

# A data class to hold the results of a BB84 key generation run.
@dataclass
class BB84Result:
    key_bits: List[int]
    qber_sample: float
    raw_transmissions: int
    sifted_size_before_sample: int
    sample_indices: List[int]
    kept_indices: List[int]

# Compares bases and returns the sifted key bits and their indices.    
# Returns atuple containing (alice_sifted_bits, bob_sifted_bits, matching_indices)
def sift(alice_bits: np.ndarray, alice_bases: np.ndarray,
         bob_bases: np.ndarray, bob_bits: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    match = (alice_bases == bob_bases)
    index = np.nonzero(match)[0]
    return alice_bits[index], bob_bits[index], index

# Samples a subset of sifted bits to verify the Quantum Bit Error Rate (QBER).
# Returns a tuple containing (kept_bits, qber_value, sample_indices, kept_indices)
def sample_and_verify(alice_sift: np.ndarray, bob_sift: np.ndarray, s: int, rng: np.random.Generator,
                      qber_threshold: float = 0.02):
    if len(alice_sift) < s:
        raise ValueError(f"Not enough sifted bits to sample: have {len(alice_sift)}, need s={s}")
    sample_idx = rng.choice(len(alice_sift), size=s, replace=False)
    mism = int(np.sum(alice_sift[sample_idx] != bob_sift[sample_idx]))
    qber = mism / s
    mask = np.ones(len(alice_sift), dtype=bool); mask[sample_idx] = False
    kept_b = bob_sift[mask]
    if qber > qber_threshold:
        raise ValueError(f"QBER too high in sample: {qber:.3f} > {qber_threshold:.3f}")
    kept_indices = np.nonzero(mask)[0].tolist()
    return kept_b.astype(int).tolist(), qber, sample_idx.tolist(), kept_indices

# Picks the best available IBM backend based on pending jobs.
def pick_ibm_backend(service, backend_name=None):
    if backend_name:
        return service.backend(backend_name)
    sims = service.backends(simulator=True, operational=True)
    if sims:
        try:
            sims = sorted(sims, key=lambda b: getattr(b.status(), "pending_jobs", 0))
        except Exception:
            pass
        return sims[0]
    qpus = service.backends(simulator=False, operational=True)
    if not qpus:
        raise RuntimeError("No operational IBM backends found for this account/instance.")
    try:
        qpus = sorted(qpus, key=lambda b: getattr(b.status(), "pending_jobs", 0))
    except Exception:
        pass
    return qpus[0]

# Runs a batch of circuits on an IBM Quantum Runtime backend.
def run_single_shot_batch_runtime(circuits: List[QuantumCircuit], *, runtime_service=None, backend_name=None, shots=1):
    try:
        from qiskit_ibm_runtime import SamplerV2 as Sampler, Session, QiskitRuntimeService
    except Exception:
        from qiskit_ibm_runtime import Sampler, Session, QiskitRuntimeService
    service = runtime_service or QiskitRuntimeService()
    backend = pick_ibm_backend(service, backend_name=backend_name)
    with Session(service=service, backend=backend) as session:
        sampler = Sampler(mode=session)
        job = sampler.run(circuits, shots=shots)
        result = job.result()
    bits = []
    for i in range(len(circuits)):
        pub = result[i]
        try:
            counts = pub.data.meas.get_counts()
        except Exception:
            counts = pub.join_data().get_counts()
        bits.append(int(next(iter(counts))[-1]))
    return bits

#  Implements the BB84 Quantum Key Distribution protocol to generate a secure key.
def BB84(n: int, s: int, *, seed: Optional[int] = None, batch_size: int = 1024,
         executor: str = "aer", runtime_service=None, backend_name: Optional[str] = None,
         qber_threshold: float = 0.02) -> BB84Result:
    if n <= 0 or s < 0:
        raise ValueError("n must be >0 and s >=0")
    random_generator = create_random_generator(seed)
    alice_sift_all, bob_sift_all = [], []
    raw_total = 0
    while True:
        m = batch_size
        alice_bits  = create_random_bits(random_generator, m)
        alice_bases = create_random_bases(random_generator, m)
        bob_bases = create_random_bases(random_generator, m)
        circs = [one_qubit_bb84_circuit(int(alice_bits[i]), int(alice_bases[i]), int(bob_bases[i])) for i in range(m)]
        if executor.lower() == "aer":
            bob_bits = np.array(run_single_shot_batch(circs), dtype=np.int8)
        elif executor.lower() == "runtime":
            bob_bits = np.array(run_single_shot_batch_runtime(circs, runtime_service=runtime_service, backend_name=backend_name, shots=1), dtype=np.int8)
        else:
            raise ValueError("executor must be 'aer' or 'runtime'")
        raw_total += m
        alice_sift, bob_sift, _ = sift(alice_bits, alice_bases, bob_bases, bob_bits)
        if len(alice_sift):
            alice_sift_all.append(alice_sift); bob_sift_all.append(bob_sift)
        if sum(len(x) for x in alice_sift_all) >= n + s:
            break
    alice_sift_cat = np.concatenate(alice_sift_all) if alice_sift_all else np.array([], dtype=np.int8)
    bob_sift_cat = np.concatenate(bob_sift_all) if bob_sift_all else np.array([], dtype=np.int8)
    kept_bits, qber, sample_idx, kept_idx = sample_and_verify(alice_sift_cat, bob_sift_cat, s, random_generator, qber_threshold=qber_threshold)
    if len(kept_bits) < n:
        raise RuntimeError(f"After sampling, not enough bits remain: have {len(kept_bits)}, need {n}")
    key_bits = kept_bits[:n]
    return BB84Result(
        key_bits=key_bits,
        qber_sample=qber,
        raw_transmissions=raw_total,
        sifted_size_before_sample=len(alice_sift_cat),
        sample_indices=sample_idx,
        kept_indices=kept_idx[:n]
    )

if __name__ == "__main__":
    res = BB84(n=100, s=10, seed=42, executor="aer", batch_size=1024)
    print("Raw transmissions:", res.raw_transmissions)
    print("Sifted (before sampling):", res.sifted_size_before_sample)
    print("Sample QBER:", res.qber_sample)
    print("First 32 key bits:", ''.join(map(str, res.key_bits[:32])), "...")
    print("Key length:", len(res.key_bits))
