# 👨‍🎓 This is the Code for my Thesis on Matheuristics

Title: ***Matheuristics Within the Variable Neighborhood Search Framework: Applied on the Simultaneous Student-Project Allocation and Group Design Problem***

Two heuristics were developed for the Simultaneous Student-Project Allocation and Group Design Problem (SSPAGDP). They are matheuristics since they are model-based. Both pass subproblems to the state-of-the art solver Gurobi. The point of reference for the benchmarks was Gurobi when run without any further algorithm. The heuristic based on variable fixing showed superior performance in the early stages of optimization.

## 🤔 What is the SSPAGDP about?
Projects that have rather general topics are offered to students e.g Operations Management or Marketing. Within a project groups of students work on specific topics e.g. "The Effect of X on Marketing Strategies in Industry Y". Those offering the project supervise the groups in their project work.

In the SSPAGDP a weighted sum of total satisfaction with the assignment of students to groups in projects is maximized. The students state their preference for each project and specify students they would like to work with. Those responsible for the projects state preferences and constraints regarding the number of groups they supervise and the size of those groups.

The two heuristics that rely on Gurobi and Gurobi on its own then assign students to groups in projects so as to maximize the weighted sum of total satisfaction. For more details, **base_model_builder.py** in the **modeling** folder is a good starting point.

## ⛏️ What was done?
First, an existent Variable Neighborhood Search (VNS) based heuristic for 0-1 MIPs called VNS with Local Branching was adapted so that it is viable for the SSPAGDP (see **local_branching.py**). Since the results were not much if at all better than running Gurobi alone (see **gurobi_alone.py**), a new heuristic was developed. In it parts of the variables are temporarily fixated (variable fixing). More specifically part of the assignment variables are fixed which state whether student x is in group y of project z (see heuristic at **assignment_fixing.py**). The performance of the variable fixing heuristic gets significantly better than Gurobi alone in the early stages of the optimization, as the instances grow larger.

Instances were created randomly within parameters that seemed reasonable. Also, some measures were taken to imitate real-life dynamics among students, albeit rudimentarily. See the modules in the folder **instance_creation** for more.

## 📋 Requirements
- Python 3.13.11
- Gurobi 13.0.0
- pandas 2.3.3
- gurobipy 13.0.0

If you have conda installed, you may run
```
conda create --name <foo_env> python=3.13.11 pandas=2.3.3 gurobi::gurobi=13.0.0
```
where <foo_env> should be replaced by the environment name of your choice.

`gurobi::gurobi` installs the Gurobi conda package from the gurobi channel. It includes more than just `gurobipy`. If you don't use conda you may run

```
python -m pip install gurobipy==13.0.0
```

The Gurobi version 13.0.0 was installed separately.

## 🚀 Usage
If your current working directory is the root folder of the project, you may run 
```
>>> from assignment_fixing import assignment_fixing
>>> from local_branching import local_branching
>>> from gurobi_alone import gurobi_alone
>>> solution_fixing = assignment_fixing(30, 300, 0, time_limit=60)
>>> solution_branching = local_branching(30, 300, 0, time_limit=60)
>>> solution_gurobi = gurobi_alone(30, 300, 0, time_limit=60)
```

Here you would have solved the instance with 30 projects, 300 students and the instance index 0. The instance index is needed to differentiate instances that were created with the same parameters and only differ due to randomness. The time limit is in seconds. All instances that were already created are in the folder **instances**. If you want save new instances, take a look at **save_instances.py**.

The return value of `assignment_fixing`, `local_branching` and `gurobi_alone` is an object which allows you to assess the solution (see **solution_processing/solution_access.py** for more).

The benchmarks ran on a ThinkPad T490s with an Intel i7-8565U CPU and 16GB memory, running Microsoft Windows 11 Enterprise. The results are in the **benchmarks** folder. If you want to run new benchmarks, take a look at **benchmark.py**.

