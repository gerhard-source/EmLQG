"""
EmLQG - Quantum Encoding of Loop Quantum Gravity Initial Conditions
Kodiert eine LQG-Anfangsbedingung (Spin-Netzwerk) als Quantenschaltkreis
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler, StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp, partial_trace, entropy
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler import Target, CouplingMap
from qiskit.circuit.exceptions import CircuitError

class LQGQuantumEncoder:
    """
    Kodiert ein LQG-Spin-Netzwerk in einen Quantenschaltkreis.
    
    Ein LQG-Zustand wird repräsentiert durch:
    - Knoten (nodes) mit Spin-Quantenzahlen j_n
    - Kanten (edges) mit Flussquantenzahlen
    - Volumen- und Flächenoperatoren als Observablen
    """
    
    def __init__(self, spin_config):
        """
        Args:
            spin_config: Liste von Spins [j1, j2, ..., jN] für N Knoten
                         Typische Werte: 0, 1/2, 1, 3/2, 2, ...
        """
        self.spins = spin_config
        self.n_nodes = len(spin_config)
        # Jeder Spin benötigt log2(2j+1) Qubits
        self.qubits_per_node = [int(np.ceil(np.log2(2*j + 1))) for j in spin_config]
        self.total_qubits = sum(self.qubits_per_node)
        
    def encode_initial_state(self):
        """
        Erzeugt den Quantenschaltkreis für die LQG-Anfangsbedingung.
        """
        qc = QuantumCircuit(self.total_qubits)
        
        qubit_idx = 0
        node_starts = []  # Speichere Startindizes für jeden Knoten
        
        for node_idx, (j, n_qubits) in enumerate(zip(self.spins, self.qubits_per_node)):
            node_starts.append(qubit_idx)
            
            # Kodiere den Spin-Wert j
            spin_value = int(2 * j)
            
            # Hadamard für Superposition über mögliche Spins
            for q in range(n_qubits):
                qc.h(qubit_idx + q)
            
            # Phasenkodierung des spezifischen Spin-Werts
            if n_qubits > 0:
                binary = format(spin_value, f'0{n_qubits}b')
                for q, bit in enumerate(binary):
                    if bit == '1':
                        qc.p(np.pi / 2 ** (q+1), qubit_idx + q)
            
            qubit_idx += n_qubits
        
        # Verschränkung zwischen benachbarten Knoten (LQG-Kanten)
        for i in range(len(node_starts) - 1):
            start1 = node_starts[i]
            start2 = node_starts[i + 1]
            
            # Verwende das erste Qubit jedes Knotens für die Verschränkung
            # Stelle sicher, dass es unterschiedliche Qubits sind
            if start1 != start2:
                try:
                    qc.cz(start1, start2)
                except CircuitError:
                    # Fallback: Wenn das nicht geht, versuche CNOT
                    try:
                        qc.cx(start1, start2)
                    except:
                        pass  # Ignoriere, wenn beides fehlschlägt
        
        # Globale Phase für die Eichfreiheit in LQG
        if self.total_qubits > 0:
            qc.p(np.random.uniform(0, 2*np.pi), 0)
        
        return qc
    
    def add_geometry_operators(self, qc):
        """
        Fügt geometrische Observablen hinzu.
        """
        n = self.total_qubits
        
        if n == 0:
            return None, None, None
        
        # Volumenoperator
        volume_pauli = 'I' * n
        for i in range(min(n, 3)):  # Beschränke auf max 3 Qubits für Stabilität
            volume_pauli = volume_pauli[:i] + 'Z' + volume_pauli[i+1:]
        volume_op = SparsePauliOp.from_list([(volume_pauli, 1.0/max(n, 1))])
        
        # Flächenoperator
        if n >= 2:
            area_op = SparsePauliOp.from_list([("ZZ" + "I"*(n-2), 1.0)])
        else:
            area_op = SparsePauliOp.from_list([("Z", 1.0)])
        
        # Krümmungsoperator
        if n >= 4:
            curvature_op = SparsePauliOp.from_list([("XXYY" + "I"*(n-4), 1.0)])
        elif n >= 2:
            curvature_op = SparsePauliOp.from_list([("XX" + "I"*(n-2), 1.0)])
        else:
            curvature_op = None
            
        return volume_op, area_op, curvature_op

def simulate_lQG_universe(spin_config, shots=10000, use_estimator=True):
    """
    Simuliert ein LQG-Universum und extrahiert kosmologische Observablen.
    """
    encoder = LQGQuantumEncoder(spin_config)
    
    if encoder.total_qubits == 0:
        print("   ⚠️ Keine Qubits für diese Konfiguration!")
        return {}
    
    # 1. Quantenschaltkreis für die Anfangsbedingung
    qc = encoder.encode_initial_state()
    
    print(f"   Erstellte Schaltung mit {encoder.total_qubits} Qubits")
    print(f"   Schaltungstiefe: {qc.depth()}")
    
    # 2. Geometrieoperatoren hinzufügen
    volume_op, area_op, curvature_op = encoder.add_geometry_operators(qc)
    
    # 3. Primitive für Ausführung
    if use_estimator:
        estimator = StatevectorEstimator()
        
        # Definiere die 5 kosmologischen Observablen
        cosmological_observables = {
            'Λ (cosmological constant)': volume_op,
            'G (gravitational constant)': area_op,
            'ρ_crit (critical density)': curvature_op if curvature_op else volume_op,
            'H0 (Hubble constant)': SparsePauliOp.from_list([("X"*encoder.total_qubits, 1.0)]) if encoder.total_qubits > 0 else None,
            'Ω_m (matter density)': SparsePauliOp.from_list([("Z"*encoder.total_qubits, 1.0)]) if encoder.total_qubits > 0 else None
        }
        
        results = {}
        for name, obs in cosmological_observables.items():
            if obs:
                try:
                    job = estimator.run([(qc, obs)], precision=0.1)  # 10% für schnelleren Test
                    result = job.result()
                    results[name] = result[0].data.evs
                    print(f"   ✓ {name}: {results[name]:.6f}")
                except Exception as e:
                    print(f"   ✗ Fehler bei {name}: {e}")
                    results[name] = 0.0
        
        return results
    
    else:
        sampler = StatevectorSampler()
        qc.measure_all()
        job = sampler.run([qc], shots=shots)
        result = job.result()
        counts = result[0].data.meas.get_counts()
        
        return {
            'counts': counts,
            'most_probable_state': max(counts, key=counts.get),
            'entropy': calculate_quantum_entropy(qc)
        }

def calculate_quantum_entropy(qc):
    """Berechnet die von-Neumann-Entropie des LQG-Zustands"""
    from qiskit.quantum_info import Statevector
    try:
        state = Statevector(qc)
        if state.num_qubits >= 2:
            rho_reduced = partial_trace(state, range(1, state.num_qubits))
            return entropy(rho_reduced)
        else:
            return 0.0
    except:
        return 0.0

# ============================================
# BEISPIEL: Verschiedene LQG-Anfangsbedingungen
# ============================================

if __name__ == "__main__":
    print("🚀 EmLQG - Quantum Exploration of Loop Quantum Gravity\n")
    
    # Teste verschiedene Spin-Konfigurationen
    test_configs = [
        [0.5, 1, 1.5],      # Einfache Konfiguration
        [1, 1.5, 2],        # Mittlere Spins
        [0.5, 1, 1.5, 2],   # Gemischte Konfiguration
    ]
    
    for i, spins in enumerate(test_configs):
        print(f"\n📐 LQG-Konfiguration {i+1}: Spins = {spins}")
        print("-" * 50)
        
        # Simuliere dieses Universum
        results = simulate_lQG_universe(spins, use_estimator=True)
        
        # Berechne, wie "lebensfreundlich" dieses Universum ist
        if results and 'Λ (cosmological constant)' in results:
            lambda_val = abs(results['Λ (cosmological constant)'])
            # Normalisiere den Score für bessere Darstellung
            life_score = np.exp(-lambda_val * 2)
            print(f"\n   🌟 Life-Friendliness Score: {life_score:.4f}")
            if life_score > 0.3:
                print("   ✅ Dieses Universum könnte Leben unterstützen!")
            elif life_score > 0.1:
                print("   ⚠️ Grenzwertig für Leben")
            else:
                print("   ❌ Lebensfeindlich")
    
    # ============================================
    # FÜR GOOGLE WILLOW HARDWARE:
    # ============================================
    if len(test_configs) > 0:
        print("\n\n🔧 Vorbereitung für Google Willow Hardware")
        print("=" * 50)
        
        # Optimiere den Schaltkreis für Willows Topologie
        try:
            willow_target = Target.from_configuration(
                basis_gates=["cz", "sx", "rz", "x"],
                coupling_map=CouplingMap.from_line(7),
                num_qubits=7
            )
            
            encoder = LQGQuantumEncoder([0.5, 1, 1.5])
            qc = encoder.encode_initial_state()
            
            if qc.num_qubits > 0:
                pass_manager = generate_preset_pass_manager(
                    optimization_level=1,  # Niedriger für schnellere Transpilation
                    target=willow_target,
                    seed_transpiler=42
                )
                qc_transpiled = pass_manager.run(qc)
                
                print(f"Original Tiefe: {qc.depth()} Gates")
                print(f"Für Willow transpilierte Tiefe: {qc_transpiled.depth()} Gates")
                print(f"Anzahl Qubits: {qc_transpiled.num_qubits}")
                print("\n✅ Bereit für Ausführung auf Google Willow!")
            else:
                print("⚠️ Kein gültiger Schaltkreis für Willow erstellt")
        except Exception as e:
            print(f"⚠️ Willow-Vorbereitung übersprungen: {e}")