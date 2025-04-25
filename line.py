# ────────────────────────────────────────────────────────────────────────────────
# Imports
# ────────────────────────────────────────────────────────────────────────────────
import collections
import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as mpatches

import networkx as nx

# ────────────────────────────────────────────────────────────────────────────────
# Helper: deterministic tree layout (root left, successors to the right)
# ────────────────────────────────────────────────────────────────────────────────
def tree_lr_layout(G: nx.DiGraph, x_spacing: float = 2.0, y_spacing: float = 1.5):
    """Arrange a DAG like a left-to-right tree and return {node: (x, y)}."""
    level = {}
    for node in nx.topological_sort(G):
        preds = list(G.predecessors(node))
        level[node] = 0 if not preds else 1 + max(level[p] for p in preds)

    columns = collections.defaultdict(list)
    for node, lvl in level.items():
        columns[lvl].append(node)
    for nodes in columns.values():
        nodes.sort()

    pos = {}
    for lvl, nodes in columns.items():
        top = (len(nodes) - 1) / 2
        for i, node in enumerate(nodes):
            pos[node] = (lvl * x_spacing, (top - i) * y_spacing)
    return pos

# ────────────────────────────────────────────────────────────────────────────────
# NEW: exact positional-weight computation
# ────────────────────────────────────────────────────────────────────────────────
def compute_positional_weights(tasks, times, predecessors):
    """Return {task: positional weight}."""
    G = nx.DiGraph()
    for t in tasks:
        G.add_node(t)
    for t, preds in predecessors.items():
        for p in preds:
            G.add_edge(p, t)

    topo = list(nx.topological_sort(G))[::-1]          # leaves → roots
    positional_weights = {t: times[t] for t in tasks}

    for node in topo:                                  # accumulate successors
        for succ in G.successors(node):
            positional_weights[node] += positional_weights[succ]
    return positional_weights

# ────────────────────────────────────────────────────────────────────────────────
# Line-balancing algorithm
# ────────────────────────────────────────────────────────────────────────────────
def line_balancing_algorithm(tasks, times, predecessors,
                              cycle_time, heuristic="longest_task_time"):

    total_work_content = sum(times.values())
    min_stations = max(1, int((total_work_content + cycle_time - 0.01)//cycle_time))

    workstations, station_times = {}, {}
    assigned_tasks, current_station = set(), 1
    station_times[current_station] = 0

    # followers are handy later for eligibility checks
    followers = {t: [] for t in tasks}
    for t in tasks:
        for p in predecessors.get(t, []):
            followers[p].append(t)

    # ---- positional weights -----------------------------
    if heuristic == "ranked_positional_weight":
        positional_weights = compute_positional_weights(tasks, times, predecessors)
    # ------------------------------------------------------

    def eligible(task):
        return task not in assigned_tasks and all(p in assigned_tasks
                                                  for p in predecessors.get(task, []))

    while len(assigned_tasks) < len(tasks):
        cand = [t for t in tasks if eligible(t)]
        if not cand:
            raise ValueError("No eligible tasks found - check precedence data.")

        if heuristic == "longest_task_time":
            cand.sort(key=lambda t: times[t], reverse=True)
        else:  # ranked positional weight
            cand.sort(key=lambda t: positional_weights[t], reverse=True)

        placed = False
        for t in cand:
            if station_times[current_station] + times[t] <= cycle_time:
                workstations.setdefault(current_station, []).append(t)
                station_times[current_station] += times[t]
                assigned_tasks.add(t)
                placed = True
                break
        if not placed:
            current_station += 1
            station_times[current_station] = 0

    actual_stations = len(workstations)
    idle_time = sum(cycle_time - station_times[s] for s in station_times)
    eff = (total_work_content / (actual_stations * cycle_time)) * 100
    metrics = dict(total_work_content=total_work_content,
                   cycle_time=cycle_time,
                   min_stations=min_stations,
                   actual_stations=actual_stations,
                   idle_time=idle_time,
                   efficiency=eff,
                   balance_delay=100-eff,
                   station_times=station_times)
    return workstations, metrics

# ────────────────────────────────────────────────────────────────────────────────
# GUI
# ────────────────────────────────────────────────────────────────────────────────
def create_line_balancing_gui(workstations, metrics, tasks, predecessors):
    root = tk.Tk()
    root.title("Line Balancing Results")
    root.geometry("1200x800")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # 1) Results tab -----------------------------------------------------------
    results_frame = ttk.Frame(notebook)
    notebook.add(results_frame, text="Results")

    frame_ws = ttk.LabelFrame(results_frame, text="Workstation Assignments")
    frame_ws.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    for s in sorted(workstations):
        tasks_str = ", ".join(workstations[s])
        ttk.Label(frame_ws, text=f"Station {s}: {tasks_str}").grid(sticky="w")
        ttk.Label(frame_ws, text=f"  Total time: {metrics['station_times'][s]} sec").grid(sticky="w")
        ttk.Label(frame_ws, text=f"  Idle time: {metrics['cycle_time'] - metrics['station_times'][s]} sec").grid(sticky="w")

    frame_met = ttk.LabelFrame(results_frame, text="Performance Metrics")
    frame_met.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    metrics_txt = (
        f"Total Work Content: {metrics['total_work_content']} sec\n"
        f"Cycle Time: {metrics['cycle_time']} sec\n"
        f"Theoretical Minimum Stations: {metrics['min_stations']}\n"
        f"Actual Stations: {metrics['actual_stations']}\n"
        f"Efficiency: {metrics['efficiency']:.2f}%\n"
        f"Balance Delay: {metrics['balance_delay']:.2f}%"
    )
    ttk.Label(frame_met, text=metrics_txt).grid(sticky="w")

    # Build the task-precedence graph once (shared by both graph tabs)
    G = nx.DiGraph()
    G.add_nodes_from(tasks)
    for t, preds in predecessors.items():
        for p in preds:
            G.add_edge(p, t)
    pos = tree_lr_layout(G)   # deterministic layout

    # 2) Precedence network tab -----------------------------------------------
    topo_frame = ttk.Frame(notebook)
    notebook.add(topo_frame, text="Task Precedence Network")

    fig1 = plt.Figure(figsize=(8, 6))
    ax1 = fig1.add_subplot(111)
    nx.draw(G, pos, ax=ax1, with_labels=True, node_size=2000,
            node_color='lightblue', font_size=12, font_weight='bold', arrowsize=20)
    ax1.set_title('Precedence graph')
    FigureCanvasTkAgg(fig1, topo_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # 3) Task-allocation tab ---------------------------------------------------
    alloc_frame = ttk.Frame(notebook)
    notebook.add(alloc_frame, text="Task Allocation")

    fig2 = plt.Figure(figsize=(8, 6))
    ax2 = fig2.add_subplot(111)

    palette = ['tab:red', 'tab:green', 'tab:blue', 'tab:orange', 'tab:purple',
               'tab:brown', 'tab:pink', 'tab:olive', 'tab:cyan']
    colour = {}
    for i, s in enumerate(sorted(workstations)):
        for t in workstations[s]:
            colour[t] = palette[i % len(palette)]
    node_colours = [colour.get(t, 'lightgray') for t in tasks]

    nx.draw(G, pos, ax=ax2, with_labels=True, node_size=2000,
            node_color=node_colours, font_size=12, font_weight='bold', arrowsize=20)

    patches = [mpatches.Patch(color=palette[i % len(palette)], label=f'Station {s}')
               for i, s in enumerate(sorted(workstations))]
    ax2.legend(handles=patches, loc='best')
    ax2.set_title('Task allocation')
    FigureCanvasTkAgg(fig2, alloc_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

    return root

# ────────────────────────────────────────────────────────────────────────────────
# Demo data & launcher
# ────────────────────────────────────────────────────────────────────────────────
def main_with_gui():
    # Example I
    tasks = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
    times = {'A': 40, 'B': 30, 'C': 50, 'D': 40, 'E': 6,
             'F': 25, 'G': 15, 'H': 20, 'I': 18}
    predecessors = {
        'A': [],
        'B': ['A'],
        'C': ['A'],
        'D': ['B'],
        'E': ['B'],
        'F': ['C'],
        'G': ['C'],
        'H': ['D', 'E'],
        'I': ['F', 'G']
    }
    cycle_time = 60  # seconds



    workstations, metrics = line_balancing_algorithm(
        tasks, times, predecessors, cycle_time, heuristic="longest_task_time"
    )
    root = create_line_balancing_gui(workstations, metrics, tasks, predecessors)
    root.mainloop()

    # ────────────────────────────────────────────────────────────────────────────────
    # Example II
    # Data from the provided image
    # tasks = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n']
    
    # times = {
    #     'a': 5,
    #     'b': 1,
    #     'c': 3,
    #     'd': 2,
    #     'e': 4,
    #     'f': 6,
    #     'g': 2,
    #     'h': 5,
    #     'i': 2,
    #     'j': 2,
    #     'k': 3,
    #     'l': 8,
    #     'm': 3,
    #     'n': 4
    # }
    
    # predecessors = {
    #     'a': [],
    #     'b': ['a'],
    #     'c': ['a'],
    #     'd': ['a'],
    #     'e': ['b'],
    #     'f': ['c', 'd'],
    #     'g': ['b', 'c'],
    #     'h': ['e'],
    #     'i': ['f'],
    #     'j': ['h'],
    #     'k': ['h'],
    #     'l': ['i'],
    #     'm': ['j'],
    #     'n': ['g', 'k', 'l', 'm']
    # }
    
    # # Cycle time from the example
    # cycle_time = 10  # seconds
    
    # # Run the algorithm with longest task time rule
    # workstations, metrics = line_balancing_algorithm(
    #     tasks, times, predecessors, cycle_time, heuristic="ranked_positional_weight"
    # )
    
    # # Create and run the GUI
    # root = create_line_balancing_gui(workstations, metrics, tasks, predecessors)
    # root.mainloop()


if __name__ == "__main__":
    main_with_gui()
