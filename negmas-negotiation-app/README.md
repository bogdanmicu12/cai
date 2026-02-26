# NegMAS Negotiation App

This project is a small **automated negotiation** playground built on top of **NegMAS**.

---

## 1) Overview

### What “automated negotiation” means here
Two (or more) self-interested agents have **conflicting preferences**, but still try to reach a **mutually acceptable agreement** (a deal). An agreement is an **offer** (a “bid”) that specifies values for one or more **issues**.

- **Single-issue** example: price only (car sale)
- **Multi-issue** example: price + speed + data (phone contract)

### Core building blocks you will see in the code
A scenario is defined by:

- **Agents**: the negotiators
- **Offer space**: all possible offers (Cartesian product of issue options in multi-issue domains)
- **Protocol**: rules of interaction (who proposes/accepts when, when it ends)
- **Utility functions**: each agent’s private preferences over offers
- **Reservation value**: minimum acceptable utility (no deal is better than worse-than-RV deals)
- **Deadline**: negotiation ends when time/rounds run out

The repository maps those ideas to folders:

- `src/negmas_negotiation_app/domain/`  
  Defines negotiation **issues** and **utility functions** (how offers are evaluated).
- `src/negmas_negotiation_app/scenarios/`  
  Bundles domain + agents + settings into a runnable **scenario**.
- `src/negmas_negotiation_app/mechanisms/`  
  Contains the **negotiation mechanism** (the protocol “engine” coordinating turns, proposals, acceptance, and stopping conditions).
- `src/negmas_negotiation_app/agents/`  
  Negotiation **agents** (strategies) using the **BOA model**:
  - **Bidding strategy**: what offer to propose next (e.g., time-based, adaptive, imitative)
  - **Acceptance strategy**: when to accept an opponent offer (e.g., ACnext / ACasp / AClow-style logic)
  - **Opponent modeling** (optional): estimate opponent preferences/behavior (e.g., frequency analysis, Bayesian)

---

## 2) Project structure

```
negmas-negotiation-app
├── src/
│   └── negmas_negotiation_app/
│       ├── main.py
│       ├── agents/
│       ├── domain/
│       ├── mechanisms/
│       ├── scenarios/
│       └── types/
├── tests/
├── pyproject.toml
├── requirements.txt
└── README.md
```