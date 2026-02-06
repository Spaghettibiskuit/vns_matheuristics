# 👨‍🎓 This is the Code for my Thesis on Matheuristics

Title: ***Matheuristics Within the Variable Neighborhood Search Framework: Applied on the Simultaneous Student-Project Allocation and Group Design Problem***

Two heuristics were developed for the Simultaneous Student-Project Allocation and Group Design Problem (SSPAGDP). They are matheuristics since they are model based and pass subproblems to the state-of-the art solver Gurobi. The point of reference for the benchmarks was Gurobi when run without any further algorithm. A heuristic based on variable fixing showed superior performance in the early stages of optimization.

## 🤔 What is the SSPAGDP about?
Here, a project is offered to students and has a rather general topic, which entices students more or less e.g Operations Management or Marketing. Those that offer the project then supervise groups of students in their project work on a specific topic e.g. "The Effect of X on Marketing Strategies in Industry Y".

In the SSPAGDP a weighted sum of total satisfaction with the assignment of students to groups in projects is maximized. The students state their preferences for the different different project and specify students they would like to work with. Those responsible for the projects state preferences and constraints regarding the number of groups they supervise and the size of those groups.

The heuristics that rely on Gurobi and Gurobi on its own then assign students to groups in projects so as to maximize the weighted sum of total satisfaction. For more details, **base_model_builder.py** in the **modeling** folder is a good starting point.

## ⛏️ What was done?
First, an existent Variable Neighborhood Search (VNS) based heuristic for 0-1 MIPs called VNS with Local Branching was adapted so that it is viable for the SSPAGDP (see **local_branching.py**). Since the results were still not better than running Gurobi alone (see **gurobi_alone.py**), a heuristic that temporarily fixates parts of the variable (variable fixing), was developed (see **assignment_fixing.py**). The performance of the latter heuristic is significantly better than Gurobi alone in the early stages, as the instances grow larger.

Instances were created randomly within parameters that seemed reasonable. Also, some measures were taken to imitate dynamic students, albeit rudimentarily. See the modules in the folder **instance_creation** for more.

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







