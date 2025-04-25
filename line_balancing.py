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
# Positional-weight computation
# ────────────────────────────────────────────────────────────────────────────────
def compute_positional_weights(tasks, times, predecessors):
    """Return {task: positional weight}."""
    G = nx.DiGraph()
    G.add_nodes_from(tasks)
    for t, preds in predecessors.items():
        for p in preds:
            G.add_edge(p, t)

    topo = list(nx.topological_sort(G))[::-1]          # leaves → roots
    pw = {t: times[t] for t in tasks}
    for node in topo:
        for succ in G.successors(node):
            pw[node] += pw[succ]
    return pw

# ────────────────────────────────────────────────────────────────────────────────
# Line-balancing algorithm (unchanged except for the call to compute_positional_weights)
# ────────────────────────────────────────────────────────────────────────────────
def line_balancing_algorithm(tasks, times, predecessors,
                              cycle_time, heuristic="longest_task_time"):

    total_work = sum(times.values())
    min_stations = max(1, int((total_work + cycle_time - 0.01)//cycle_time))

    workstations, st_times = {}, {}
    assigned, ws = set(), 1
    st_times[ws] = 0

    if heuristic == "ranked_positional_weight":
        pw = compute_positional_weights(tasks, times, predecessors)

    def eligible(t):
        return t not in assigned and all(p in assigned for p in predecessors.get(t, []))

    while len(assigned) < len(tasks):
        cand = [t for t in tasks if eligible(t)]
        if not cand:
            raise ValueError("No eligible tasks – check precedence data.")

        if heuristic == "longest_task_time":
            cand.sort(key=lambda t: times[t], reverse=True)
        else:
            cand.sort(key=lambda t: pw[t], reverse=True)

        placed = False
        for t in cand:
            if st_times[ws] + times[t] <= cycle_time:
                workstations.setdefault(ws, []).append(t)
                st_times[ws] += times[t]
                assigned.add(t)
                placed = True
                break
        if not placed:
            ws += 1
            st_times[ws] = 0

    idle = sum(cycle_time - st_times[s] for s in st_times)
    eff = (total_work / (len(workstations) * cycle_time)) * 100
    metrics = dict(total_work_content=total_work,
                   cycle_time=cycle_time,
                   min_stations=min_stations,
                   actual_stations=len(workstations),
                   idle_time=idle,
                   efficiency=eff,
                   balance_delay=100-eff,
                   station_times=st_times)
    return workstations, metrics

# ────────────────────────────────────────────────────────────────────────────────
# GUI (unchanged)
# ────────────────────────────────────────────────────────────────────────────────
def create_line_balancing_gui(workstations, metrics, tasks, predecessors):
    root = tk.Tk()
    root.title("Line Balancing Results")
    root.geometry("1200x800")

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # ----- Results tab --------------------------------------------------------
    res_f = ttk.Frame(nb); nb.add(res_f, text="Results")

    lf_ws = ttk.LabelFrame(res_f, text="Workstation Assignments")
    lf_ws.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    for s in sorted(workstations):
        tasks_str = ", ".join(workstations[s])
        ttk.Label(lf_ws, text=f"Station {s}: {tasks_str}").grid(sticky="w")
        ttk.Label(lf_ws, text=f"  Total time: {metrics['station_times'][s]} sec").grid(sticky="w")
        ttk.Label(lf_ws, text=f"  Idle time: {metrics['cycle_time'] - metrics['station_times'][s]} sec").grid(sticky="w")

    lf_met = ttk.LabelFrame(res_f, text="Performance Metrics")
    lf_met.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    msg = (f"Total Work Content: {metrics['total_work_content']} sec\n"
           f"Cycle Time: {metrics['cycle_time']} sec\n"
           f"Theoretical Minimum Stations: {metrics['min_stations']}\n"
           f"Actual Stations: {metrics['actual_stations']}\n"
           f"Efficiency: {metrics['efficiency']:.2f}%\n"
           f"Balance Delay: {metrics['balance_delay']:.2f}%")
    ttk.Label(lf_met, text=msg).grid(sticky="w")

    # ----- Graphs common data -------------------------------------------------
    G = nx.DiGraph()
    G.add_nodes_from(tasks)
    for t, preds in predecessors.items():
        for p in preds:  G.add_edge(p, t)
    pos = tree_lr_layout(G)

    # ----- Precedence network -------------------------------------------------
    topo_f = ttk.Frame(nb); nb.add(topo_f, text="Task Precedence Network")
    fig1 = plt.Figure(figsize=(8, 6)); ax1 = fig1.add_subplot(111)
    nx.draw(G, pos, ax=ax1, with_labels=True, node_size=2000,
            node_color='lightblue', font_size=12, font_weight='bold', arrowsize=20)
    ax1.set_title('Precedence graph')
    FigureCanvasTkAgg(fig1, topo_f).get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ----- Task allocation ----------------------------------------------------
    alloc_f = ttk.Frame(nb); nb.add(alloc_f, text="Task Allocation")
    fig2 = plt.Figure(figsize=(8, 6)); ax2 = fig2.add_subplot(111)
    palette = ['tab:red', 'tab:green', 'tab:blue', 'tab:orange', 'tab:purple',
               'tab:brown', 'tab:pink', 'tab:olive', 'tab:cyan']
    colour = {}
    for i, s in enumerate(sorted(workstations)):
        for t in workstations[s]:
            colour[t] = palette[i % len(palette)]
    nx.draw(G, pos, ax=ax2, with_labels=True, node_size=2000,
            node_color=[colour.get(t, 'lightgray') for t in tasks],
            font_size=12, font_weight='bold', arrowsize=20)
    patches = [mpatches.Patch(color=palette[i % len(palette)], label=f'Station {s}')
               for i, s in enumerate(sorted(workstations))]
    ax2.legend(handles=patches, loc='best')
    ax2.set_title('Task allocation')
    FigureCanvasTkAgg(fig2, alloc_f).get_tk_widget().pack(fill=tk.BOTH, expand=True)

    return root

# ────────────────────────────────────────────────────────────────────────────────
# Interactive data collection (console prompts)
# ────────────────────────────────────────────────────────────────────────────────
def collect_data_from_user():
    print("\n=== Assembly-line data entry ===")
    tasks = [t.strip() for t in input("Enter task IDs (comma-separated): ").split(",") if t.strip()]
    times = {}
    predecessors = {}

    for t in tasks:
        times[t] = float(input(f"  Processing time for task '{t}': ").strip())
        preds = input(f"  Immediate predecessors of '{t}' (comma-sep, blank if none): ").strip()
        predecessors[t] = [p.strip() for p in preds.split(",") if p.strip()]

    cycle_time = float(input("\nEnter desired cycle time (sec): ").strip())
    rule = input("Heuristic – (1) longest task time  (2) ranked positional weight [default 1]: ").strip()
    heuristic = "ranked_positional_weight" if rule == "2" else "longest_task_time"

    return tasks, times, predecessors, cycle_time, heuristic

# ────────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────────
# Main (supports quick DEMO or full interactive entry)
# ────────────────────────────────────────────────────────────────────────────────
def main():
    first = input(
        "\nType task IDs (comma-separated) or just hit <Enter> for DEMO: "
    ).strip()

    # ---------------------------------------------------------------------
    # 1)  DEMO : slide example a…n  (cycle-time = 10 s, ranked positional weight)
    # ---------------------------------------------------------------------
    if first == "" or first.lower() == "demo":
        tasks = list("abcdefghijklmn")
        times = {'a':5,'b':1,'c':3,'d':2,'e':4,'f':6,'g':2,
                 'h':5,'i':2,'j':2,'k':3,'l':8,'m':3,'n':4}
        predecessors = {
            'a': [],
            'b': ['a'], 'c': ['a'], 'd': ['a'],
            'e': ['b'],
            'f': ['c', 'd'],
            'g': ['b', 'c'],
            'h': ['e'],
            'i': ['f'],
            'j': ['h'], 'k': ['h'],
            'l': ['i'],
            'm': ['j'],
            'n': ['g', 'k', 'l', 'm'],
        }
        cycle_time = 10
        heuristic  = "ranked_positional_weight"

    # ---------------------------------------------------------------------
    # 2)  Manual entry: we already have the first line (the task list)
    # ---------------------------------------------------------------------
    else:
        tasks = [t.strip() for t in first.split(",") if t.strip()]
        times = {}
        predecessors = {}
        print("\nEnter processing times and predecessors for each task:")
        for t in tasks:
            times[t] = float(input(f"  Processing time for '{t}': ").strip())
            preds = input(f"  Immediate predecessors of '{t}' (comma-sep, blank if none): ").strip()
            predecessors[t] = [p.strip() for p in preds.split(",") if p.strip()]

        cycle_time = float(input("\nEnter desired cycle time (sec): ").strip())
        rule = input("Heuristic – (1) longest task time  (2) ranked positional weight [default 1]: ").strip()
        heuristic = "ranked_positional_weight" if rule == "2" else "longest_task_time"

    # ---------------------------------------------------------------------
    # 3)  Run algorithm & launch GUI
    # ---------------------------------------------------------------------
    workstations, metrics = line_balancing_algorithm(
        tasks, times, predecessors, cycle_time, heuristic)

    root = create_line_balancing_gui(workstations, metrics, tasks, predecessors)
    root.mainloop()



if __name__ == "__main__":
    main()
