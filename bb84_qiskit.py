# BB84 Qiskit implementation — Aer (local) + IBM Runtime (online)
# Generated: 2025-09-12T09:06:03.569557Z

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

def make_rng(seed: Optional[int] = None) -> np.random.Generator:
    """Returns a new NumPy random number generator."""
    return np.random.default_rng(seed)

def rand_bits(rng: np.random.Generator, m: int) -> np.ndarray:
    """Generates a random array of m bits (0 or 1)."""
    return rng.integers(0, 2, size=m, dtype=np.int8)

def rand_bases(rng: np.random.Generator, m: int) -> np.ndarray:
    """Generates a random array of m bases (0 for Z, 1 for X)."""
    return rng.integers(0, 2, size=m, dtype=np.int8)

def one_qubit_bb84_circuit(bit: int, alice_basis: int, bob_basis: int) -> QuantumCircuit:
    """
    Constructs a quantum circuit for a single BB84 transmission.
    
    This circuit prepares a qubit, encodes a classical bit in a chosen basis,
    and then measures it in Bob's chosen basis.
    """
    quantum_circuit = QuantumCircuit(1, 1)
    
    # Alice's preparation step
    if alice_basis == 0:  # Z-basis (computational)
        if bit == 1:
            quantum_circuit.x(0)
    else:  # X-basis (Hadamard)
        quantum_circuit.h(0)
        if bit == 1:
            quantum_circuit.z(0)
            
    # Bob's measurement step
    if bob_basis == 1:  # X-basis (Hadamard)
        quantum_circuit.h(0)
        
    quantum_circuit.measure(0, 0)
    return quantum_circuit

def run_single_shot_batch(circuits: List[QuantumCircuit]) -> List[int]:
    """Runs a batch of circuits on the local AerSimulator."""
    aer_simulator = AerSimulator()
    transpiled_circuits = [transpile(c, aer_simulator) for c in circuits]
    results = aer_simulator.run(transpiled_circuits, shots=1).result()
    
    measured_bits = []
    for i in range(len(transpiled_circuits)):
        counts = results.get_counts(i)
        measured_bits.append(int(next(iter(counts))))
    return measured_bits

@dataclass
class BB84Result:
    """A data class to hold the results of a BB84 key generation run."""
    final_key: List[int]
    qber_sample: float
    total_transmissions: int
    sifted_size_before_sample: int
    sample_indices: List[int]
    kept_indices: List[int]

def sift(alice_raw_bits: np.ndarray, alice_bases: np.ndarray,
         bob_bases: np.ndarray, bob_measured_bits: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compares bases and returns the sifted key bits and their indices.
    
    Returns:
        A tuple containing (alice_sifted_bits, bob_sifted_bits, matching_indices)
    """
    bases_match = (alice_bases == bob_bases)
    matching_indices = np.nonzero(bases_match)[0]
    
    alice_sifted_bits = alice_raw_bits[matching_indices]
    bob_sifted_bits = bob_measured_bits[matching_indices]
    
    return alice_sifted_bits, bob_sifted_bits, matching_indices

def sample_and_verify(concatenated_alice_bits: np.ndarray, concatenated_bob_bits: np.ndarray,
                      sample_size: int, rng: np.random.Generator,
                      qber_threshold: float = 0.02):
    """
    Samples a subset of sifted bits to verify the Quantum Bit Error Rate (QBER).
    
    Returns:
        A tuple containing (kept_bits, qber_value, sample_indices, kept_indices)
    """
    if len(concatenated_alice_bits) < sample_size:
        raise ValueError(f"Not enough sifted bits to sample: have {len(concatenated_alice_bits)}, need {sample_size}")
        
    sample_indices = rng.choice(len(concatenated_alice_bits), size=sample_size, replace=False)
    
    mismatched_bits_count = int(np.sum(concatenated_alice_bits[sample_indices] != concatenated_bob_bits[sample_indices]))
    qber_value = mismatched_bits_count / sample_size
    
    if qber_value > qber_threshold:
        raise ValueError(f"QBER too high in sample: {qber_value:.3f} > {qber_threshold:.3f}")

    # Remove the sampled bits to form the final key
    mask = np.ones(len(concatenated_alice_bits), dtype=bool)
    mask[sample_indices] = False
    
    kept_bob_bits = concatenated_bob_bits[mask]
    kept_indices = np.nonzero(mask)[0].tolist()
    
    return kept_bob_bits.astype(int).tolist(), qber_value, sample_indices.tolist(), kept_indices

def pick_ibm_backend(service, backend_name=None):
    """Picks the best available IBM backend."""
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

def run_single_shot_batch_runtime(circuits: List[QuantumCircuit], *, runtime_service=None, backend_name=None, shots=1):
    """Runs a batch of circuits on an IBM Quantum Runtime backend."""
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
    measured_bits = []
    for i in range(len(circuits)):
        pub = result[i]
        try:
            counts = pub.data.meas.get_counts()
        except Exception:
            counts = pub.join_data().get_counts()
        measured_bits.append(int(next(iter(counts))[-1]))
    return measured_bits

def BB84(final_key_size: int, sample_size: int, *, seed: Optional[int] = None, batch_size: int = 1024,
         executor: str = "aer", runtime_service=None, backend_name: Optional[str] = None,
         qber_threshold: float = 0.02) -> BB84Result:
    """
    Implements the BB84 Quantum Key Distribution protocol to generate a secure key.

    Args:
        final_key_size: The desired length of the final, secure key (n).
        sample_size: The number of bits to sample for the QBER check (s).
        seed: An optional seed for the random number generator.
        batch_size: The number of photons to transmit in each round.
        executor: The quantum backend to use ('aer' for local simulation or 'runtime' for IBM).
        runtime_service: An optional IBM Qiskit Runtime service instance.
        backend_name: An optional name for a specific IBM backend.
        qber_threshold: The maximum acceptable Quantum Bit Error Rate.

    Returns:
        A BB84Result object containing the generated key and protocol statistics.
    """
    if final_key_size <= 0 or sample_size < 0:
        raise ValueError("final_key_size must be >0 and sample_size >=0")
        
    rng = make_rng(seed)
    all_alice_sifted_bits, all_bob_sifted_bits = [], []
    total_transmissions = 0
    
    # Run the protocol in batches until enough sifted bits are collected
    while True:
        alice_raw_bits = rand_bits(rng, batch_size)
        alice_bases = rand_bases(rng, batch_size)
        bob_bases = rand_bases(rng, batch_size)
        
        # Build and run the circuits
        batch_circuits = [one_qubit_bb84_circuit(int(alice_raw_bits[i]), int(alice_bases[i]), int(bob_bases[i])) for i in range(batch_size)]
        
        if executor.lower() == "aer":
            bob_measured_bits = np.array(run_single_shot_batch(batch_circuits), dtype=np.int8)
        elif executor.lower() == "runtime":
            bob_measured_bits = np.array(run_single_shot_batch_runtime(batch_circuits, runtime_service=runtime_service, backend_name=backend_name, shots=1), dtype=np.int8)
        else:
            raise ValueError("executor must be 'aer' or 'runtime'")
        
        total_transmissions += batch_size
        
        # Sift the bits from the current batch
        alice_sifted_bits, bob_sifted_bits, _ = sift(alice_raw_bits, alice_bases, bob_bases, bob_measured_bits)
        
        if len(alice_sifted_bits):
            all_alice_sifted_bits.append(alice_sifted_bits)
            all_bob_sifted_bits.append(bob_sifted_bits)
            
        # Check if we have enough sifted bits for the final key and the QBER sample
        if sum(len(x) for x in all_alice_sifted_bits) >= final_key_size + sample_size:
            break
            
    # Concatenate all the sifted bits from the batches
    concatenated_alice_sifted_bits = np.concatenate(all_alice_sifted_bits) if all_alice_sifted_bits else np.array([], dtype=np.int8)
    concatenated_bob_sifted_bits = np.concatenate(all_bob_sifted_bits) if all_bob_sifted_bits else np.array([], dtype=np.int8)
    
    # Sample bits and check for errors (QBER)
    bob_final_bits, qber_value, sample_indices, kept_indices = sample_and_verify(
        concatenated_alice_sifted_bits, concatenated_bob_sifted_bits, sample_size, rng, qber_threshold=qber_threshold)
    
    if len(bob_final_bits) < final_key_size:
        raise RuntimeError(f"After sampling, not enough bits remain: have {len(bob_final_bits)}, need {final_key_size}")
        
    final_key = bob_final_bits[:final_key_size]
    
    return BB84Result(
        final_key=final_key,
        qber_sample=qber_value,
        total_transmissions=total_transmissions,
        sifted_size_before_sample=len(concatenated_alice_sifted_bits),
        sample_indices=sample_indices,
        kept_indices=kept_indices[:final_key_size]
    )

if __name__ == "__main__":
    res = BB84(final_key_size=100, sample_size=10, seed=42, executor="aer", batch_size=1024)
    print("Total transmissions:", res.total_transmissions)
    print("Sifted bits (before sampling):", res.sifted_size_before_sample)
    print("Sample QBER:", res.qber_sample)
    print("First 32 key bits:", ''.join(map(str, res.final_key[:32])), "...")
    print("Key length:", len(res.final_key))