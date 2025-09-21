# BB84 Quantum Key Distribution Protocol in Qiskit

This repository provides a Python implementation of the BB84 Quantum Key Distribution (QKD) protocol using IBM's Qiskit framework.

The implementation is designed for dual-mode execution: it can be run **offline** on a local, noiseless `AerSimulator` for baseline validation, or **online** on real IBM Quantum hardware via the `QiskitRuntimeService`.

## Key Features

*   **Clear BB84 Implementation:** The code is structured to closely follow the theoretical steps of the BB84 protocol.
*   **Dual Execution Modes:** A simple `executor` flag switches between local simulation and execution on a real quantum processor.
*   **Demonstration of Quantum Noise:** The project includes logged results that showcase the protocol's security mechanism by detecting a high Quantum Bit Error Rate (QBER) from hardware noise and aborting key generation.

## Project Contents

*   `bb84_protocol.py`: A Python module containing the core functions for implementing the BB84 protocol.
*   `BB84_Protocol_Notebook.ipynb`: A Jupyter Notebook that provides a step-by-step walkthrough of the protocol, from circuit construction to key verification.
*   **HTML Run Logs:** Static HTML exports of the notebook, serving as a permanent record of key experimental runs:
    *   `BB84_Protocol_Qiskit_Notebook_Local_Run.html`: A successful key exchange on a noiseless simulator.
    *   `BB84_Protocol_Qiskit_Notebook_Online_Run.html`: A security-aborted run on `ibm_torino` due to high QBER.

## Setup and Installation

### Prerequisites

*   Python (3.9+)
*   Anaconda3 or Miniconda

### 1. Create and Activate a Python Environment

```
# Create a new conda environment
conda create -n qiskit-env python=3.11 -y

# Activate the environment
conda activate qiskit-env
```

### 2. Install Dependencies

```
# Ensure pip is up-to-date
python -m pip install --upgrade pip

# Install required Qiskit packages and JupyterLab
python -m pip install qiskit qiskit-aer qiskit-ibm-runtime jupyterlab
```

## How to Run

### 1. Local Simulation (Default)

The protocol can be run locally without an IBM Quantum account. This uses the `AerSimulator` to simulate a perfect, noise-free quantum channel.

```
# Open the notebook environment
jupyter lab
```

Inside `BB84_Protocol_Notebook.ipynb`, ensure the `EXECUTOR` variable is set to `"aer"` and run the cells.

### 2. Execution on IBM Quantum Hardware

To run on a real quantum device, you must have an IBM Quantum account.

**A. Save Your Credentials:**
First, obtain your API token and instance CRN from your [IBM Quantum account page](https://quantum.ibm.com/). Then, configure the notebook by setting `EXECUTOR = "runtime"` and saving your credentials:

```
from qiskit_ibm_runtime import QiskitRuntimeService

# Replace with your actual credentials
QiskitRuntimeService.save_account(
    token="YOUR_API_TOKEN",
    channel="ibm_quantum",
    instance="YOUR_INSTANCE_CRN",
    overwrite=True
)
```

**B. Run the Protocol:**
After saving your account, run the main `BB84` function call in the notebook. The code will automatically select the least busy backend or use the one specified in `RUNTIME_BACKEND_NAME`.

---

## Protocol Implementation Details

The implementation maps to the theoretical BB84 protocol as follows:

1.  **Preparation (Alice):** Alice generates two classical random sequences: a bit string (the potential key) and a basis string (0 for Z-basis, 1 for X-basis).
2.  **Quantum Transmission:** For each bit, Alice prepares a single qubit in the chosen basis and sends it to Bob. This is simulated by creating a unique `QuantumCircuit` for each transmission. The implementation uses `shots=1` for each circuit to model the single-photon nature of the protocol.
3.  **Measurement (Bob):** Bob generates his own random basis string and measures each incoming qubit accordingly.
4.  **Sifting:** Alice and Bob publicly compare their basis strings and discard all measurements where their bases did not match. This process, on average, discards 50% of the bits.
5.  **Integrity Check (Parameter Estimation):** Alice and Bob publicly compare a random subset of their sifted bits (`s` bits) to calculate the Quantum Bit Error Rate (QBER).
6.  **Verification:** If the measured QBER exceeds a predefined security threshold (`qber_threshold`), the protocol aborts, as the channel is considered insecure. Otherwise, the sample bits are discarded.
7.  **Key Generation:** The remaining sifted bits form the final, secure key.

## Experimental Results

This section documents the results from key runs of the protocol, illustrating the difference between an ideal simulation and a real-world quantum execution.

### Run 1: Local Noiseless Simulation

*   **Date:** 2025-09-14
*   **Backend:** `AerSimulator` (local, no noise)
*   **Result:** A 100-bit secure key was successfully generated. The measured **QBER was 0.0%**, as expected in an ideal, noise-free environment.
*   **Full Output:** [BB84_Protocol_Qiskit_Notebook_Local_Run.html](BB84_Protocol_Qiskit_Notebook_Local_Run.html)

### Run 2: Execution on Quantum Hardware

*   **Date:** 2025-09-21
*   **Backend:** `ibm_torino`
*   **Result:** This specific run detected a **QBER of 10.0%**, a value that exceeded the predefined security threshold of 2%. Consequently, the key generation was automatically and correctly aborted by raising a `ValueError`.
*   **Conclusion:** This run serves as a clear example of the BB84 protocol's security mechanism in action. The high QBER, likely induced by inherent hardware noise and decoherence, was identified as a potential security compromise, leading to the termination of the process.
*   **Note on Variability:** It is important to note that executing this experiment multiple times on the same quantum hardware will yield a range of results due to the  fluctuating noise levels. While this run demonstrated a high error rate, other runs may result in a lower QBER that falls within the acceptable threshold, or even a QBER of 0.0%, allowing for successful key generation.
*   **Full Output:** [BB84_Protocol_Qiskit_Notebook_Online_Run.html](BB84_Protocol_Qiskit_Notebook_Online_Run.html)

---

## Function Signature

The primary function exposed by the `bb84_protocol.py` module is:

```
def BB84(
  n: int,                          # The desired length of the final secret key.
  s: int,                          # The number of sifted bits to sacrifice for the integrity check (QBER).
  *,
  seed: Optional[int] = None,      # RNG seed for reproducibility.
  batch_size: int = 1024,          # Raw transmissions per batch until >= n+s sifted bits are accumulated.
  executor: str = "aer",           # "aer" (local) or "runtime" (IBM online).
  runtime_service=None,            # A QiskitRuntimeService instance (required for "runtime" executor).
  backend_name: Optional[str] = None,  # Optional: name of a specific IBM backend.
  qber_threshold: float = 0.02     # Security threshold for the QBER sample.
) -> BB84Result:
```

## License

This project is licensed under the MIT License.
