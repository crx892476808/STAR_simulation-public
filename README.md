# STAR

A traffic steering framework for Service Function Chain (SFC). STAR denotes “Scalable Traffic steering along ARbitrary routing paths selected by NFVO”.   In order to steer traffic flexibly, STAR first classifies the requests into RSPs and thus can enforce arbitrary routing path decisions from NFVO. Nevertheless, unlike per-RSP frameworks, STAR further divides the entire RSP into several path segments and performs traffic steering in the granularity of path segment to reduce the control traffic and the number of forwarding rules.

This repository contains the simulation code for testing the performance of STAR, SAFE-ME, ip-5-tuple and NSH.

# Getting Started

## Prerequisite

Python3

NetworkX

```shell
pip3 install networkx
```

## Running the example

```shell
mkdir logs
python3 main.py
```

