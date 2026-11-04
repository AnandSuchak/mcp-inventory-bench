# LASR-MCP Version 2.0: Formal Foundation & Invariant Termination Proof

## 1. Theorem Statement & Formulation

Let $\mathcal{S}$ denote a canonical tool specification expressed in JSON Schema Draft 2020-12, represented as an abstract syntax tree (AST).
We define $\mathcal{C} = \{c_1, c_2, \dots, c_M\}$ as the finite universe of structural constraint nodes in $\mathcal{S}$ ($|\mathcal{C}| = M < \infty$), where each constraint node $c_i$ corresponds to an unambiguous validation keyword (e.g., `pattern`, `enum`, `minimum`, `required`) situated at a specific JSON Pointer path $\pi(c_i)$.

The LASR-MCP dynamic resolution framework operates over a sequence of active constraint sets $A_t \subseteq \mathcal{C}$ at recovery step $t \ge 0$. The initial active constraint set is defined by the three-tier composition:
$$A_0 = C_I^* \cup \widehat{C}_T(x)$$
where:
- $C_I^* \subseteq \mathcal{C}$ is the pre-computed universal invariant foundation.
- $\widehat{C}_T(x) \subseteq \mathcal{C} \setminus C_I^*$ is the top-$k$ predictive constraint bundle inferred from user prompt $x$.

At each invocation step $t$, the agent receives a prompt conditioned on $A_t$ and outputs argument payload $y_t$. An execution-time JSON Schema validator evaluates $y_t$ against the full specification $\mathcal{S}$. If $y_t$ violates one or more schema constraints, the validator returns a non-empty set of diagnostics $\mathcal{E}(y_t, \mathcal{S}) \neq \emptyset$. The deterministic schema slicer $\sigma$ maps each diagnostic to its canonical constraint node in $\mathcal{C}$:
$$\Delta_t = \bigcup_{e \in \mathcal{E}(y_t, \mathcal{S})} \sigma(e, \mathcal{S}) \subseteq \mathcal{C} \setminus A_t$$
The reactive recomposer structurally inlines $\Delta_t$ in-tree, updating the active set:
$$A_{t+1} = A_t \cup \Delta_t$$

---

## 2. Admissibility Conditions

A reactive tool-calling system $(\mathcal{S}, \sigma, \mathcal{M})$ is **admissible** if:
1. **Finite Constraint Universe**: The target schema AST contains a finite number of constraint keyword nodes, $|\mathcal{C}| = M < \infty$.
2. **Strict Monotonicity**: On any validation failure at step $t$, the fault localization slicer identifies at least one previously inactive constraint: $|\Delta_t| \ge 1$ and $\Delta_t \cap A_t = \emptyset$.
3. **Deterministic Splicing**: Each identified constraint $c \in \Delta_t$ is merged into $A_{t+1}$ idempotently without pruning previously active constraints ($A_t \subset A_{t+1}$).

---

## 3. Theorem 1 (Finite Monotonic Recovery Bound)

Let $(\mathcal{S}, \sigma, \mathcal{M})$ be an admissible reactive tool-calling system with initial active constraint set $A_0 \subseteq \mathcal{C}$. The dynamic in-tree recovery process terminates in at most:
$$\boxed{K \le M - |A_0|}$$
schema-expansion transitions, resulting in either a structurally valid payload or complete exhaustion of the schema ($A_K = \mathcal{C}$).

### Proof
1. By the strict monotonicity condition, whenever $y_t$ is structurally invalid, $\Delta_t \subseteq \mathcal{C} \setminus A_t$ and $|\Delta_t| \ge 1$.
2. Consequently:
   $$|A_{t+1}| = |A_t \cup \Delta_t| = |A_t| + |\Delta_t| \ge |A_t| + 1$$
3. Thus, the sequence of active cardinalities $\{|A_0|, |A_1|, |A_2|, \dots\}$ is strictly monotonically increasing:
   $$|A_0| < |A_1| < |A_2| < \dots < |A_K|$$
4. Because every $A_t \subseteq \mathcal{C}$ and $|\mathcal{C}| = M$ is finite, the maximum cardinality of any active set is bounded by $M$.
5. By induction, after $K$ recovery expansion transitions:
   $$|A_K| \ge |A_0| + \sum_{t=0}^{K-1} |\Delta_t| \ge |A_0| + K$$
6. Since $|A_K| \le M$, it follows directly that:
   $$|A_0| + K \le M \implies K \le M - |A_0|$$
7. Because the state space is finite and the set of omitted constraints strictly decreases at each step, the recovery loop cannot cycle or run indefinitely, guaranteeing termination in at most $M - |A_0|$ transitions. $\blacksquare$

---

## 4. Why the Previous $K \le D$ Bound is Invalid (The Sibling Leaf Counterexample)

Earlier heuristic drafts proposed a bound of $K \le \min(D, M - |C_I^*|)$, where $D$ represents the maximum depth of the schema AST. This claim is invalid.

**Concrete Counterexample**:
Consider a schema root containing two independent leaf constraints at the exact same depth ($D = 1$):
- $c_1$: `/properties/warehouse_code/enum` (depth 1)
- $c_2$: `/properties/order_priority/enum` (depth 1)

```
Root Schema (Depth 0)
  ├── Constraint c1: warehouse_code.enum (Depth 1)
  └── Constraint c2: order_priority.enum (Depth 1)
Maximum tree depth: D = 1
```

- **Attempt 1** ($A_0 = \emptyset$): Generator outputs payload violating $c_1$. Validator returns error on $c_1$. Slicer inlines $c_1$. New active set: $A_1 = \{c_1\}$.
- **Attempt 2** ($A_1 = \{c_1\}$): Generator satisfies $c_1$, but violates $c_2$. Validator returns error on $c_2$. Slicer inlines $c_2$. New active set: $A_2 = \{c_1, c_2\}$.
- **Attempt 3** ($A_2 = \{c_1, c_2\}$): Generator satisfies both $c_1$ and $c_2$. Payload valid.

> **Result**: The recovery process took **$K = 2$ transitions**, even though the tree depth is **$D = 1$**.  
> Since $2 \not\le 1$, tree depth does not constrain the number of iterative recovery passes. Theorem 1 establishes the correct, defensible cardinality-based bound.

---

## 5. Generator Compliance & Structural Validity Guarantee

**Proposition 1 (Structural Validity Guarantee)**:  
If the generator model $\mathcal{M}$ satisfies the **exposed-constraint compliance assumption**—namely, that $\mathcal{M}$ never violates any constraint explicitly present in its active schema prompt $A_t$, and failures arise strictly from omitted constraints $\mathcal{C} \setminus A_t$—then the process terminates with a structurally valid invocation ($y_K \models \mathcal{S}$) in $K \le M - |A_0|$ transitions.
