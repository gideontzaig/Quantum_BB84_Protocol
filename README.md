# BB84 with Qiskit — Local Aer + IBM Runtime (toggleable)

This repo provides a clean, beginner-friendly implementation of the **BB84 quantum key distribution** protocol using **Qiskit**.

- Run **offline** with the local **Aer** simulator.
- Optionally run the **same code online** on IBM Quantum (hardware or eligible simulators) via **Qiskit Runtime**—just flip a flag.

---

## What’s inside

- `BB84_Qiskit_Aer_Notebook.ipynb` — a Jupyter notebook that explains and runs the BB84 pipeline step-by-step.  
- `bb84_qiskit.py` — the same implementation packaged as a Python module.

Both expose a single function:

```python
from bb84_qiskit import BB84

res = BB84(n=100, s=10, seed=42, executor="aer")  # "aer" (local, default) or "runtime" (IBM online)
```

### Return type (`BB84Result` dataclass)

- `key_bits: List[int]` — the final `n` key bits (0/1 list)  
- `qber_sample: float` — error rate measured on the `s` sampled, sifted bits  
- `raw_transmissions: int` — number of qubits sent to accumulate enough sifted bits  
- `sifted_size_before_sample: int` — count of sifted bits prior to sampling  
- `sample_indices: List[int]` — which sifted positions were used for the integrity check  
- `kept_indices: List[int]` — which sifted positions remain (from which the final `n` bits were taken)

---

## Quick start (local, no account required)

### 1) Create a Python environment
```bash
conda create -n qiskit-env python=3.11 -y
conda activate qiskit-env
```

### 2) Install dependencies
```bash
python -m pip install --upgrade pip
python -m pip install qiskit qiskit-aer qiskit-ibm-runtime jupyterlab
```

### 3) Run in a notebook
```bash
jupyter lab
```
Open `BB84_Qiskit_Aer_Notebook.ipynb` and run cells top-to-bottom.

### 4) Or run via the module
```python
from bb84_qiskit import BB84
res = BB84(n=100, s=10, seed=42, executor="aer")
print("QBER:", res.qber_sample, "| First 32 bits:", "".join(map(str, res.key_bits[:32])))
```

---

## How the implementation maps to BB84

1. **Alice chooses** random bits and random bases (Z or X).  
2. **State prep (1 qubit per bit)**  
   - Z-basis: apply `X` iff bit = 1 → |1⟩; else |0⟩  
   - X-basis: apply `H` (|+⟩); if bit = 1 also apply `Z` to get |−⟩  
3. **Bob measures** in a random basis:  
   - Z: measure directly  
   - X: apply `H` then measure  
4. **Sifting:** keep indices where Alice’s and Bob’s bases match.  
5. **Integrity check:** sample `s` sifted positions, compute **QBER**; discard those `s`.  
6. **Key:** take the first `n` of the remaining sifted bits as the final key.  

The implementation uses **one shot per qubit** to mirror the “one photon per bit” spirit of BB84.

---

## Toggle between local and online execution

### Local (offline) — default
```python
res = BB84(n=100, s=10, seed=42, executor="aer")
```

### IBM Runtime (online)
After saving your IBM Quantum credentials (see IBM docs/platform), you can switch executors:

```python
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()  # reads saved account

res = BB84(
    n=100, s=10, seed=123,
    executor="runtime",          # use IBM Runtime
    runtime_service=service,     # pass your service
    backend_name=None            # or specify an accessible backend by name
)
print(res.qber_sample, len(res.key_bits))
```

> The protocol pipeline (prepare → measure → run → sift → sample) is identical. Only the **executor** changes.

---

## Optional parameters (for completeness)

```python
BB84(
  n: int,
  s: int,
  *,
  seed: Optional[int] = None,      # RNG seed for reproducibility
  batch_size: int = 1024,          # raw transmissions per batch until we have >= n+s sifted bits
  executor: str = "aer",           # "aer" (local) or "runtime" (IBM online)
  runtime_service=None,            # QiskitRuntimeService when executor="runtime"
  backend_name: Optional[str] = None,  # specific online backend (optional)
  qber_threshold: float = 0.02     # integrity-check threshold (useful if you add noise)
)
```

---

## Troubleshooting (common)

- **`AttributeError: get_counts` on per-experiment entries**  
  Use `result.get_counts(i)` on the overall result object (not `res.results[i].get_counts()`).

- **Online: `No matching instances found` when creating `QiskitRuntimeService()`**  
  Re-save your account with explicit `instance="..."` and `region="us-east"`, then restart the kernel.

- **No online simulators visible**  
  Keep using Aer locally (or a fake backend). You can still target real hardware with `executor="runtime"`.

---

## License

MIT License.
