# Assembly-Line Balancer 📊

An easy-to-run Python GUI that demonstrates **single-model line balancing**
using either

- **Longest-Task-Time (LTT)**, or
- **Ranked-Positional-Weight (RPW)**

heuristics.  
The program lets you **type in any precedence network at run-time** _or_
launch a built-in **DEMO** that reproduces the 14-task textbook example
(`a … n`, cycle-time = 10 s) shown on the lecture slide.

---

## ✨ Features

| Tab                         | What you get                                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------- |
| **Results**                 | Work-station assignments, individual station times & idle, global efficiency / balance-delay. |
| **Task Precedence Network** | Automatically laid-out left-to-right DAG (roots at the left).                                 |
| **Task Allocation**         | Same graph, but each node is coloured by the station to which it was assigned.                |

All plots resize with the window and use true vector graphics (via Matplotlib),
so you can copy-paste them straight into reports.

---

## 🗂 Directory layout

_(No other files are needed – everything is generated at run-time.)_

---

## 📦 Requirements

| Package      | Tested with                                        |
| ------------ | -------------------------------------------------- |
| Python       | 3.8 – 3.12                                         |
| `networkx`   | ≥ 3.0                                              |
| `matplotlib` | ≥ 3.5                                              |
| `tkinter`    | comes with standard CPython on Windows/macOS/Linux |

Install any missing libs via:

```bash
pip install networkx matplotlib


▶️ Running the program


python line_balancer.py

You will see:

Type task IDs (comma-separated) or just hit <Enter> for DEMO:
1. Instant demo
Simply press Enter → the GUI opens with the 14-task example:

a b c d e f h i l j k m g n

Your own data
Enter a comma-separated list of task IDs, e.g.
A,B,C,D

The program then walks you through:

Processing time for 'A':
Immediate predecessors of 'A' (comma-sep, blank if none):
...
Enter desired cycle time (sec):
Heuristic – (1) longest task time  (2) ranked positional weight [default 1]:

When done, the same three-tab GUI appears for your assembly line.
```
