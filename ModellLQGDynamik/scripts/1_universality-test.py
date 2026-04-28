#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1_universality-test.py
UNIVERSALITY-TEST FÜR LQG-ATTRAKTOREN
Testet, ob verschiedene heutige Universen zum gleichen primordialen Zustand führen

Korrigierte Version – Syntaxfehler behobenCreated on Sat Apr 25 10:40:01 2026

@author: gh
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import random

# =============================================================================
# SPIN-NETZWERK KLASSEN
# =============================================================================

@dataclass
class SpinEdge:
    id: int
    source: int
    target: int
    spin: float
    
    @property
    def area(self) -> float:
        return np.sqrt(self.spin * (self.spin + 1))

@dataclass
class SpinVertex:
    id: int
    edges: List[int]
    volume: float = 0.0
    position: Tuple[float, float, float] = (0, 0, 0)

class SpinNetwork:
    def __init__(self, vertices: List[SpinVertex], edges: List[SpinEdge]):
        self.vertices = vertices
        self.edges = edges
        self.vertex_dict = {v.id: v for v in vertices}
        self.edge_dict = {e.id: e for e in edges}
        self._next_vertex_id = max([v.id for v in vertices]) + 1 if vertices else 0
        self._next_edge_id = max([e.id for e in edges]) + 1 if edges else 0
        
    def copy(self) -> 'SpinNetwork':
        new_vertices = [SpinVertex(v.id, v.edges.copy(), v.volume, v.position) 
                       for v in self.vertices]
        new_edges = [SpinEdge(e.id, e.source, e.target, e.spin) 
                    for e in self.edges]
        return SpinNetwork(new_vertices, new_edges)
    
    @property
    def total_volume(self) -> float:
        return sum(v.volume for v in self.vertices)
    
    @property
    def total_area(self) -> float:
        return sum(e.area for e in self.edges)
    
    def homogeneity_metric(self) -> float:
        if len(self.vertices) < 2:
            return 1.0
            
        volumes = [v.volume for v in self.vertices]
        spins = [e.spin for e in self.edges]
        
        if not volumes or not spins:
            return 1.0
            
        volume_mean = np.mean(volumes)
        spin_mean = np.mean(spins)
        
        if volume_mean == 0 or spin_mean == 0:
            return 1.0
            
        volume_variation = np.std(volumes) / volume_mean
        spin_variation = np.std(spins) / spin_mean
        
        homogeneity = 1.0 / (1.0 + volume_variation + spin_variation)
        return homogeneity

# =============================================================================
# LQG-OPERATIONEN (VERKÜRZT FÜR DEN TEST)
# =============================================================================

class ImprovedLQGOperations:
    """LQG-Operationen mit dynamischen Schrittweiten"""
    
    @staticmethod
    def edge_split(network: SpinNetwork, edge_id: int, step_weight: float = 1.0) -> SpinNetwork:
        """Teilt eine Kante mit gewichteter Spin-Aufteilung"""
        if edge_id not in network.edge_dict:
            return network.copy()
            
        edge = network.edge_dict[edge_id]
        new_network = network.copy()
        
        new_vid = new_network._next_vertex_id
        new_vertex = SpinVertex(new_vid, [], volume=0.3 * step_weight)
        new_network.vertices.append(new_vertex)
        new_network.vertex_dict[new_vid] = new_vertex
        
        new_network.edges = [e for e in new_network.edges if e.id != edge_id]
        new_network.edge_dict.pop(edge_id, None)
        
        new_spin1 = edge.spin * step_weight
        new_spin2 = edge.spin * (1 - step_weight)
        
        new_edge1 = SpinEdge(new_network._next_edge_id, edge.source, new_vid, new_spin1)
        new_edge2 = SpinEdge(new_network._next_edge_id + 1, new_vid, edge.target, new_spin2)
        
        new_network.edges.extend([new_edge1, new_edge2])
        new_network.edge_dict[new_edge1.id] = new_edge1
        new_network.edge_dict[new_edge2.id] = new_edge2
        
        new_vertex.edges = [new_edge1.id, new_edge2.id]
        
        if edge.source in new_network.vertex_dict:
            new_network.vertex_dict[edge.source].edges.append(new_edge1.id)
        if edge.target in new_network.vertex_dict:
            new_network.vertex_dict[edge.target].edges.append(new_edge2.id)
        
        new_network._next_vertex_id += 1
        new_network._next_edge_id += 2
        
        return new_network
    
    @staticmethod
    def edge_merge(network: SpinNetwork, step_weight: float = 1.0) -> Tuple[SpinNetwork, bool]:
        """Verschmilzt Kanten mit dynamischer Spin-Kombination"""
        best_network = network.copy()
        best_homo_gain = 0
        success = False
        
        edges = list(network.edges)
        for i, e1 in enumerate(edges):
            for e2 in edges[i+1:]:
                vertices1 = {e1.source, e1.target}
                vertices2 = {e2.source, e2.target}
                common = vertices1.intersection(vertices2)
                
                if common:
                    common_vertex = common.pop()
                    other1 = (vertices1 - {common_vertex}).pop()
                    other2 = (vertices2 - {common_vertex}).pop()
                    
                    new_network = network.copy()
                    
                    new_spin = (e1.spin + e2.spin) * step_weight
                    new_edge = SpinEdge(new_network._next_edge_id, other1, other2, new_spin)
                    
                    new_network.edges = [e for e in new_network.edges if e.id not in [e1.id, e2.id]]
                    new_network.edge_dict.pop(e1.id, None)
                    new_network.edge_dict.pop(e2.id, None)
                    
                    new_network.vertices = [v for v in new_network.vertices if v.id != common_vertex]
                    new_network.vertex_dict.pop(common_vertex, None)
                    
                    new_network.edges.append(new_edge)
                    new_network.edge_dict[new_edge.id] = new_edge
                    
                    if other1 in new_network.vertex_dict:
                        new_network.vertex_dict[other1].edges.append(new_edge.id)
                    if other2 in new_network.vertex_dict:
                        new_network.vertex_dict[other2].edges.append(new_edge.id)
                    
                    new_network._next_edge_id += 1
                    
                    homo_gain = new_network.homogeneity_metric() - network.homogeneity_metric()
                    if homo_gain > best_homo_gain:
                        best_network = new_network
                        best_homo_gain = homo_gain
                        success = True
        
        return best_network, success

# =============================================================================
# DYNAMISCHE SIMULATION
# =============================================================================

class DynamicSimulation:
    """Simulation mit dynamisch angepassten Schrittweiten"""
    
    def __init__(self, target_homogeneity: float = 0.9, max_steps: int = 20):
        self.target_homogeneity = target_homogeneity
        self.max_steps = max_steps
        self.ops = ImprovedLQGOperations()
    
    def forward_simulation(self, initial_state: SpinNetwork) -> Tuple[List[SpinNetwork], List[float]]:
        """Vorwärts mit adaptiven Schrittweiten"""
        history = [initial_state]
        step_weights = [1.0]
        current = initial_state.copy()
        
        for step in range(self.max_steps):
            current_homo = current.homogeneity_metric()
            
            if current_homo <= self.target_homogeneity:
                break
            
            homo_distance = current_homo - self.target_homogeneity
            step_weight = min(1.0, max(0.1, 1.0 - homo_distance))
            
            if current.edges:
                edges_by_spin = sorted(current.edges, key=lambda e: e.spin, reverse=True)
                current = self.ops.edge_split(current, edges_by_spin[0].id, step_weight)
            
            for vertex in current.vertices:
                vertex.volume = len(vertex.edges) * 0.2 * step_weight
            
            history.append(current)
            step_weights.append(step_weight)
        
        return history, step_weights
    
    def reverse_simulation(self, initial_state: SpinNetwork) -> Tuple[List[SpinNetwork], List[float]]:
        """Reverse mit adaptiven Schrittweiten"""
        history = [initial_state]
        step_weights = [1.0]
        current = initial_state.copy()
        
        for step in range(self.max_steps):
            current_homo = current.homogeneity_metric()
            
            if current_homo >= self.target_homogeneity:
                break
            
            if len(current.vertices) <= 2:
                break
            
            homo_distance = self.target_homogeneity - current_homo
            step_weight = min(1.0, max(0.1, homo_distance))
            
            new_current, success = self.ops.edge_merge(current, step_weight)
            
            if success and new_current.homogeneity_metric() > current_homo:
                current = new_current
                history.append(current)
                step_weights.append(step_weight)
            else:
                break
        
        return history, step_weights

# =============================================================================
# GENERIERUNG VON TEST-NETZWERKEN (KORRIGIERT)
# =============================================================================

def generate_base_today_universe() -> SpinNetwork:
    """Generiert das Basis-Universum (6 Knoten, wie in Ihren Tests)"""
    vertices = [
        SpinVertex(0, [], volume=0.85, position=(0,0,0)),
        SpinVertex(1, [], volume=0.82, position=(1,0,0)),
        SpinVertex(2, [], volume=0.81, position=(2,0,0)),
        SpinVertex(3, [], volume=0.83, position=(0,1,0)),
        SpinVertex(4, [], volume=0.80, position=(1,1,0)),
        SpinVertex(5, [], volume=0.82, position=(2,1,0))
    ]
    
    spin_values = [1.0, 1.5, 2.0, 0.5, 1.0, 1.5, 1.0, 0.5, 2.0, 1.5, 1.0, 0.5]
    connections = [
        (0,1), (0,2), (0,3), (0,4),
        (1,2), (1,3), (1,5),
        (2,4), (2,5),
        (3,4), (3,5),
        (4,5)
    ]
    
    edges = []
    for i, ((src, tgt), spin) in enumerate(zip(connections, spin_values)):
        edges.append(SpinEdge(i, src, tgt, spin))
        vertices[src].edges.append(i)
        vertices[tgt].edges.append(i)
    
    return SpinNetwork(vertices, edges)


def generate_random_spin_network(n_vertices: int, n_edges_factor: float = 1.5) -> SpinNetwork:
    """Generiert ein zufälliges Spin-Netzwerk (KORRIGIERT)"""
    vertices = []
    for i in range(n_vertices):
        volume = 0.8 + random.uniform(-0.3, 0.3)
        pos = (random.uniform(-2, 2), random.uniform(-2, 2), random.uniform(-2, 2))
        vertices.append(SpinVertex(i, [], volume=volume, position=pos))
    
    n_edges = int(n_vertices * n_edges_factor)
    edges = []
    edge_set = set()
    spin_values = [0.5, 1.0, 1.5, 2.0, 2.5]
    edge_id = 0
    
    attempts_total = 0
    max_attempts = 500
    
    while len(edges) < n_edges and attempts_total < max_attempts:
        src = random.randint(0, n_vertices - 1)
        tgt = random.randint(0, n_vertices - 1)
        if src != tgt and (src, tgt) not in edge_set and (tgt, src) not in edge_set:
            edge_set.add((src, tgt))
            spin = random.choice(spin_values)
            edges.append(SpinEdge(edge_id, src, tgt, spin))
            vertices[src].edges.append(edge_id)
            vertices[tgt].edges.append(edge_id)
            edge_id += 1
        attempts_total += 1
    
    return SpinNetwork(vertices, edges)


def generate_systematic_variants(base_network: SpinNetwork) -> List[SpinNetwork]:
    """Generiert systematische Varianten eines Basis-Netzwerks"""
    variants = []
    
    # Variante 1: Original
    variants.append(base_network.copy())
    
    # Variante 2: Leicht erhöhte Spins
    net2 = base_network.copy()
    for e in net2.edges:
        e.spin *= 1.1
    variants.append(net2)
    
    # Variante 3: Leicht reduzierte Spins
    net3 = base_network.copy()
    for e in net3.edges:
        e.spin *= 0.9
    variants.append(net3)
    
    # Variante 4: Einen Knoten hinzufügen
    net4 = base_network.copy()
    new_vid = net4._next_vertex_id
    new_vertex = SpinVertex(new_vid, [], volume=0.8)
    net4.vertices.append(new_vertex)
    net4.vertex_dict[new_vid] = new_vertex
    net4._next_vertex_id += 1
    
    existing_ids = [v.id for v in net4.vertices if v.id != new_vid]
    if len(existing_ids) >= 2:
        src, tgt = existing_ids[0], existing_ids[1]
        for i, (s, t) in enumerate([(src, new_vid), (new_vid, tgt)]):
            new_edge = SpinEdge(net4._next_edge_id + i, s, t, 1.0)
            net4.edges.append(new_edge)
            net4.edge_dict[new_edge.id] = new_edge
            if s in net4.vertex_dict:
                net4.vertex_dict[s].edges.append(new_edge.id)
            if t in net4.vertex_dict:
                net4.vertex_dict[t].edges.append(new_edge.id)
        net4._next_edge_id += 2
    variants.append(net4)
    
    return variants


# =============================================================================
# UNIVERSALITY-TEST (HAUPTKLASSE)
# =============================================================================

class UniversalityTest:
    """Testet, ob verschiedene Ausgangszustände zum gleichen Attraktor konvergieren"""
    
    def __init__(self, target_homogeneity: float = 0.7, max_steps: int = 15):
        self.target_homogeneity = target_homogeneity
        self.max_steps = max_steps
        self.simulator = DynamicSimulation(target_homogeneity, max_steps)
    
    def compute_attractor_signature(self, network: SpinNetwork) -> Dict:
        """Berechnet eine eindeutige Signatur des Attraktors"""
        return {
            'n_vertices': len(network.vertices),
            'n_edges': len(network.edges),
            'homogeneity': network.homogeneity_metric(),
            'total_volume': network.total_volume,
            'total_area': network.total_area,
            'avg_spin': np.mean([e.spin for e in network.edges]) if network.edges else 0,
            'std_spin': np.std([e.spin for e in network.edges]) if network.edges else 0,
        }
    
    def run_universality_test(self, test_networks: List[SpinNetwork]) -> Dict:
        """Führt den vollständigen Universalitäts-Test durch"""
        print("\n" + "="*80)
        print("🌌 UNIVERSALITY-TEST: Ist der Urknall ein universeller Attraktor?")
        print("="*80)
        
        results = {
            'primordial_states': [],
            'signatures': [],
            'trajectories': [],
            'success': []
        }
        
        # 1. Reverse-Simulation für jedes Netzwerk
        for i, network in enumerate(test_networks):
            print(f"\n📡 Test-Netzwerk {i+1}: {len(network.vertices)} Knoten, H={network.homogeneity_metric():.3f}")
            
            history, _ = self.simulator.reverse_simulation(network)
            
            if history and len(history) > 0:
                primordial = history[-1]
                signature = self.compute_attractor_signature(primordial)
                results['primordial_states'].append(primordial)
                results['signatures'].append(signature)
                results['trajectories'].append(history)
                results['success'].append(True)
                print(f"   → Primordial: {len(primordial.vertices)} Knoten, H={primordial.homogeneity_metric():.3f}")
            else:
                results['success'].append(False)
                print(f"   ❌ Keine Konvergenz")
        
        # 2. Vergleiche der primordialen Zustände
        print("\n" + "-"*80)
        print("📊 VERGLEICH DER PRIMORDIALEN ZUSTÄNDE")
        print("-"*80)
        
        similarities = []
        successful_sigs = [s for i, s in enumerate(results['signatures']) if results['success'][i]]
        
        for i in range(len(successful_sigs)):
            for j in range(i+1, len(successful_sigs)):
                sim = 1.0 - abs(successful_sigs[i]['homogeneity'] - successful_sigs[j]['homogeneity'])
                similarities.append(sim)
                print(f"   Ähnlichkeit {i+1} ↔ {j+1}: {sim:.3f}")
        
        results['avg_similarity'] = np.mean(similarities) if similarities else 0
        results['std_similarity'] = np.std(similarities) if similarities else 0
        results['convergence_rate'] = sum(results['success']) / len(results['success']) if results['success'] else 0
        
        return results


# =============================================================================
# VISUALISIERUNG
# =============================================================================

def visualize_results(results: Dict, test_networks: List[SpinNetwork]):
    """Visualisiert die Ergebnisse"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Homogenitäts-Pfade
    ax1 = axes[0]
    for i, traj in enumerate(results['trajectories']):
        if traj:
            steps = range(len(traj))
            homos = [n.homogeneity_metric() for n in traj]
            ax1.plot(steps, homos, 'o-', label=f'Netz {i+1}', linewidth=2, markersize=4)
    ax1.set_xlabel('Rekonstruktions-Schritte')
    ax1.set_ylabel('Homogenität H')
    ax1.set_title('Konvergenz der Homogenität')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Statistik
    ax2 = axes[1]
    stats = [
        ('Konvergenzrate', results['convergence_rate']),
        ('Mittlere Ähnlichkeit', results['avg_similarity']),
        ('Std. Ähnlichkeit', results['std_similarity'])
    ]
    names = [s[0] for s in stats]
    values = [s[1] for s in stats]
    colors = ['green' if v > 0.8 else 'orange' if v > 0.6 else 'red' for v in values]
    ax2.bar(names, values, color=colors)
    ax2.set_ylabel('Score')
    ax2.set_ylim(0, 1)
    ax2.set_title('Universalitäts-Statistik')
    ax2.tick_params(axis='x', rotation=15)
    
    plt.tight_layout()
    plt.show()


# =============================================================================
# HAUPTAUSFÜHRUNG
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 DER GROSSE UNIVERSALITY-TEST")
    print("="*80)
    print("\nFrage: Ist der Urknall ein universeller Attraktor?")
    print("Das heißt: Führen verschiedene 'heutige' Universen")
    print("zum selben primordialen Zustand?\n")
    
    # Generiere Test-Universen
    print("📡 Generiere Test-Universen...")
    base_today = generate_base_today_universe()
    test_networks = generate_systematic_variants(base_today)
    
    # Füge zufällige Netzwerke hinzu
    for i in range(2):
        random_net = generate_random_spin_network(n_vertices=random.randint(4, 6))
        test_networks.append(random_net)
    
    print(f"   → {len(test_networks)} Test-Netzwerke generiert")
    
    # Führe Test durch
    tester = UniversalityTest(target_homogeneity=0.65, max_steps=12)
    results = tester.run_universality_test(test_networks)
    
    # Visualisiere
    visualize_results(results, test_networks)
    
    # Abschließende Bewertung
    print("\n" + "="*80)
    print("🎯 ABSCHLIESSENDE BEWERTUNG")
    print("="*80)
    
    if results['convergence_rate'] > 0.7 and results['avg_similarity'] > 0.8:
        print("✅ DIE HYPOTHESE WIRD BESTÄTIGT!")
        print("   → Der Urknall ist ein universeller Attraktor.")
    elif results['convergence_rate'] > 0.5 and results['avg_similarity'] > 0.6:
        print("⚠️ DIE HYPOTHESE IST PLAUSIBEL, ABER NICHT EINDEUTIG")
        print("   → Weitere Tests mit größeren Netzwerken nötig.")
    else:
        print("❌ DIE HYPOTHESE WIRD NICHT BESTÄTIGT")
        print("   → Der Urknall ist kein universeller Attraktor in diesem Modell.")
    
    print(f"\n📊 DETAILS:")
    print(f"   Konvergenzrate: {results['convergence_rate']:.1%}")
    print(f"   Mittlere Ähnlichkeit: {results['avg_similarity']:.3f}")
    print(f"   Standardabweichung: {results['std_similarity']:.3f}")