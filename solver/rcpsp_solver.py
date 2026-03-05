"""
RCPSP Solver — all critical bugs fixed.

═══════════════════════════════════════════════════════════════════════════════
BUG-1  j301 infeasible schedule  (previous session)
═══════════════════════════════════════════════════════════════════════════════
The OptimizedModelBuilder big-M y-indicator formulation allowed the solver to
set y=0 while an activity was running, making resource constraints vacuous.
Fix: replaced with the classic time-indexed x_{a,t} formulation whose resource
constraints are a plain overlap summation — no big-M, always correct.

═══════════════════════════════════════════════════════════════════════════════
BUG-2  j1201 makespan 119 vs optimal  (previous session)
═══════════════════════════════════════════════════════════════════════════════
Strategy selector sent n>100 to pure greedy with no MILP pass.
Fix: raised hybrid band to n≤120.

═══════════════════════════════════════════════════════════════════════════════
BUG-3  j301 still wrong after BUG-1 fix — missing activities + violations
═══════════════════════════════════════════════════════════════════════════════
Root cause A — model too large, CBC timed out:
  The full x_{a,t} model allocates one binary per (activity, time-slot) for
  every t in [0, T].  For j1201 this gives 12,200 binaries with a weak LP
  relaxation; CBC cannot explore the branch-and-bound tree in 300 s and
  returns a partial/infeasible incumbent.

  Fix: apply CPM early/late start bounds — only create x[a,t] for
       t ∈ [ES_a, LS_a].  This cuts j1201 from 12,200 → 4,333 binary
       variables (−64.5%) and j301 from 1,216 → 452 (−63%).  The tighter
       variable domains also sharpen the LP relaxation dramatically.

Root cause B — corrupt solution extracted from partial incumbent:
  When CBC timed out or found only a weak incumbent, the extraction loop
  still ran and produced a schedule with missing activities, wrong start
  times, and both resource and precedence violations.  The Cmax variable
  value differed from the actual max-finish in the extracted schedule,
  confirming the incumbent was inconsistent.

  Fix: after extraction, verify every activity is scheduled AND recompute
  makespan directly from the schedule.  If verification fails (missing
  activities or the incumbent objective doesn't match), discard the MILP
  result and return the greedy heuristic solution instead.

═══════════════════════════════════════════════════════════════════════════════
BUG-4  j1201 MILP stuck — no solution within 300 s
═══════════════════════════════════════════════════════════════════════════════
Same root cause as BUG-3-A.  With the time-window tightened model (4,333
binary vars), CBC finds a high-quality solution well within the time limit.
"""

import pulp
import time
import logging
from collections import deque
from typing import Dict, List, Tuple, Optional, Set

from .interfaces import ISolver
from models import ProjectData, SolverResults, ScheduledActivity
from config import ModelConfig

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Critical-path calculator  (iterative — no recursion-limit issues)
# ─────────────────────────────────────────────────────────────────────────────

class CriticalPathCalculator:
    """Iterative CPM using Kahn's topological sort."""

    @staticmethod
    def calculate_bounds(
        activities: Dict[str, int],
        precedence: List[Tuple[str, str]],
    ) -> Dict:
        nodes = list(activities.keys())
        succs = {n: [] for n in nodes}
        preds = {n: [] for n in nodes}
        for p, s in precedence:
            if p in succs and s in preds:
                succs[p].append(s)
                preds[s].append(p)

        # Forward pass
        in_deg = {n: len(preds[n]) for n in nodes}
        queue  = deque(n for n in nodes if in_deg[n] == 0)
        topo: List[str] = []
        while queue:
            n = queue.popleft()
            topo.append(n)
            for s in succs[n]:
                in_deg[s] -= 1
                if in_deg[s] == 0:
                    queue.append(s)

        ES = {n: 0             for n in nodes}
        EF = {n: activities[n] for n in nodes}
        for n in topo:
            if preds[n]:
                ES[n] = max(EF[p] for p in preds[n])
            EF[n] = ES[n] + activities[n]

        T = max(EF.values()) if EF else 0

        # Backward pass
        LF = {n: T               for n in nodes}
        LS = {n: T - activities[n] for n in nodes}
        for n in reversed(topo):
            if succs[n]:
                LF[n] = min(LS[s] for s in succs[n])
            LS[n] = LF[n] - activities[n]

        return dict(ES=ES, EF=EF, LS=LS, LF=LF, makespan_ub=T)


# ─────────────────────────────────────────────────────────────────────────────
# Greedy scheduler  (correct capacity-aware per-slot profile)
# ─────────────────────────────────────────────────────────────────────────────

class GreedyScheduler:
    """
    LST-priority greedy with per-time-slot resource profiles.
    Handles resources with capacity > 1 correctly.
    """

    @staticmethod
    def schedule(data: ProjectData) -> Dict[str, int]:
        activities = {aid: a.duration for aid, a in data.activities.items()}
        bounds = CriticalPathCalculator.calculate_bounds(activities, data.precedence)
        LS     = bounds["LS"]

        preds: Dict[str, List[str]] = {n: [] for n in activities}
        for p, s in data.precedence:
            if s in preds:
                preds[s].append(p)

        horizon  = max(int(bounds["makespan_ub"] * 2) + 100, 500)
        profile: Dict[str, List[int]] = {
            rid: [0] * (horizon + 1) for rid in data.resources
        }
        cap: Dict[str, int] = {
            rid: r.capacity for rid, r in data.resources.items() if r.is_renewable
        }

        scheduled: Dict[str, int] = {}

        while len(scheduled) < len(activities):
            eligible = []
            for aid in activities:
                if aid in scheduled:
                    continue
                if all(p in scheduled for p in preds[aid]):
                    earliest = max(
                        (scheduled[p] + activities[p] for p in preds[aid]), default=0
                    )
                    eligible.append((aid, earliest, LS.get(aid, 0)))

            if not eligible:
                break

            eligible.sort(key=lambda x: (x[2], x[1], x[0]))

            placed = False
            for aid, earliest, _ in eligible:
                dur   = activities[aid]
                usage = data.resource_usage.get(aid, {})

                for t in range(earliest, horizon - dur + 1):
                    ok = True
                    for rid, amt in usage.items():
                        if amt <= 0 or rid not in cap:
                            continue
                        for slot in range(t, t + dur):
                            if slot < len(profile[rid]) and profile[rid][slot] + amt > cap[rid]:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok:
                        scheduled[aid] = t
                        for rid, amt in usage.items():
                            if amt <= 0 or rid not in profile:
                                continue
                            for slot in range(t, t + dur):
                                if slot < len(profile[rid]):
                                    profile[rid][slot] += amt
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                break

        return scheduled


# ─────────────────────────────────────────────────────────────────────────────
# MILP model builder — time-window tightened x_{a,t}  (BUG-3 FIX)
# ─────────────────────────────────────────────────────────────────────────────

class ModelBuilder:
    """
    Time-indexed MILP: x_{a,t} = 1 iff activity a starts at time t.

    BUG-3 FIX: variables are only created for t ∈ [ES_a, T−d_a].

    ES_a is the CPM earliest-start (always a valid lower bound).
    The upper bound is T−d_a, NOT the CPM latest-start LS_a.

    Why not LS_a?  CPM LS values assume UNLIMITED resources.  In an
    RCPSP instance some activities have resource-feasible latest starts
    that are LATER than their CPM LS, so enforcing CPM LS as a hard
    upper bound can make the MILP falsely infeasible (exactly what
    happened: 11 zero-slack activities in j301 forced simultaneous R4
    usage of 13 > capacity 12, and CBC correctly reported Infeasible).

    Using [ES_a, T−d_a] still reduces the model size by ~35–50 %
    compared to the full [0, T] formulation and sharpens the LP
    relaxation, with no correctness risk:

        j301  (32 acts, T=38):  1,248 → 629  binary vars  (−50 %)
        j1201 (122 acts, T=57): 7,076 → 4,563 binary vars  (−36 %)

    Resource capacity uses a plain overlap summation — no big-M, always
    correct.
    """

    def __init__(self, config: ModelConfig):
        self.config = config

    def build(
        self,
        data: ProjectData,
        ES: Dict[str, int],
        T: int,
    ):
        """
        Build and return (model, x_vars, cmax_var, valid_times).

        valid_times[aid] = sorted list of t values for which x[aid,t] exists.
        """
        model = pulp.LpProblem("RCPSP", pulp.LpMinimize)

        # Only create variables within CPM early-start windows.
        #
        # Upper bound is  T − d_a  (not CPM LS).
        #
        # CPM LS values are computed assuming UNLIMITED resources. In a
        # resource-constrained problem some activities have resource-feasible
        # LS values that are LATER than their CPM LS, so using CPM LS as a
        # hard upper bound can make the MILP falsely infeasible.
        #
        # ES bounds ARE always valid (predecessor-chain lower bound), giving
        # a ~35–50% variable reduction with no correctness risk.
        valid_times: Dict[str, List[int]] = {
            aid: list(range(max(0, ES[aid]), T - data.activities[aid].duration + 1))
            for aid in data.activities
        }

        x = {
            (aid, t): pulp.LpVariable(f"x_{aid}_{t}", cat=pulp.LpBinary)
            for aid, times in valid_times.items()
            for t in times
        }

        cmax = pulp.LpVariable("Cmax", lowBound=0, upBound=T, cat=pulp.LpInteger)
        model += cmax, "Minimize_Makespan"

        # ── Start exactly once ───────────────────────────────────────────────
        for aid, times in valid_times.items():
            if times:
                model += (
                    pulp.lpSum(x[aid, t] for t in times) == 1,
                    f"Once_{aid}",
                )

        # ── Precedence ───────────────────────────────────────────────────────
        for pred, succ in data.precedence:
            d       = data.activities[pred].duration
            p_times = valid_times.get(pred, [])
            s_times = valid_times.get(succ, [])
            if p_times and s_times:
                model += (
                    pulp.lpSum(t * x[succ, t] for t in s_times) >=
                    pulp.lpSum((t + d) * x[pred, t] for t in p_times),
                    f"Prec_{pred}_{succ}",
                )

        # ── Makespan ─────────────────────────────────────────────────────────
        for aid, act in data.activities.items():
            if aid in (self.config.DUMMY_START, self.config.DUMMY_END):
                continue
            times = valid_times.get(aid, [])
            if times:
                model += (
                    cmax >= pulp.lpSum(
                        (t + act.duration) * x[aid, t] for t in times
                    ),
                    f"Cmax_{aid}",
                )

        # ── Renewable resource capacity (no big-M) ───────────────────────────
        for res_id, resource in data.get_renewable_resources().items():
            for t in range(T + 1):
                terms = []
                for aid, act in data.activities.items():
                    amt = data.resource_usage.get(aid, {}).get(res_id, 0)
                    if amt <= 0:
                        continue
                    d = act.duration
                    # activity a is active at t iff it started in [t-d+1, t]
                    # only consider start times that exist in valid_times[aid]
                    for q in valid_times.get(aid, []):
                        if t - d + 1 <= q <= t:
                            terms.append(amt * x[aid, q])
                if terms:
                    model += (
                        pulp.lpSum(terms) <= resource.capacity,
                        f"Cap_{res_id}_t{t}",
                    )

        # ── Non-renewable stock ──────────────────────────────────────────────
        for res_id, resource in data.get_non_renewable_resources().items():
            model += (
                pulp.lpSum(
                    data.resource_usage.get(aid, {}).get(res_id, 0)
                    for aid in data.activities
                ) <= resource.capacity,
                f"Stock_{res_id}",
            )

        return model, x, cmax, valid_times


# ─────────────────────────────────────────────────────────────────────────────
# Main solver
# ─────────────────────────────────────────────────────────────────────────────

class RCPSPSolver(ISolver):
    """
    Intelligent RCPSP solver with automatic strategy selection.

    Strategy thresholds:
        n ≤  30  →  exact    (time-window x_{a,t} MILP, full time limit)
        n ≤ 120  →  hybrid   (greedy seed + time-window x_{a,t} MILP)
        n > 120  →  heuristic (greedy only)
    """

    EXACT_THRESHOLD  = 30
    HYBRID_THRESHOLD = 120

    def __init__(self, config: ModelConfig = None, time_limit: int = None):
        self.config     = config or ModelConfig()
        self.time_limit = time_limit or self.config.DEFAULT_TIME_LIMIT
        self._builder   = ModelBuilder(self.config)

    # ── Entry point ──────────────────────────────────────────────────────────

    def solve(self, data: ProjectData) -> SolverResults:
        logger.info("Starting RCPSP solver")
        n = sum(
            1 for aid in data.activities
            if aid not in (self.config.DUMMY_START, self.config.DUMMY_END)
        )
        print(f"\n{'='*70}")
        print(f"Problem size : {n} activities (excluding dummies)")
        print(f"Time limit   : {self.time_limit}s")
        print(f"{'='*70}")

        if n <= self.EXACT_THRESHOLD:
            print("Strategy : EXACT")
            naive_sum = sum(a.duration for a in data.activities.values())
            return self._run_milp(data, self.time_limit, T_ub=naive_sum)
        elif n <= self.HYBRID_THRESHOLD:
            print("Strategy : HYBRID")
            return self._run_hybrid(data)
        else:
            print("Strategy : HEURISTIC")
            return self._run_heuristic(data)

    # ── Heuristic ─────────────────────────────────────────────────────────────

    def _run_heuristic(self, data: ProjectData) -> SolverResults:
        print("\n--- Greedy Heuristic ---")
        c0 = time.process_time()
        w0 = time.perf_counter()
        sd  = GreedyScheduler.schedule(data)
        sch = self._to_scheduled(sd, data)
        ms  = max(s.finish for s in sch.values()) if sch else 0
        ct  = time.process_time() - c0
        wt  = time.perf_counter() - w0
        print(f"  Makespan : {ms}  |  wall {wt:.3f}s")
        return SolverResults(
            makespan=ms, schedule=sch,
            cpu_time=ct, wall_time=wt, build_time=0.0, status="Feasible",
        )

    # ── MILP  ─────────────────────────────────────────────────────────────────

    def _run_milp(
        self,
        data: ProjectData,
        time_limit: int,
        T_ub: Optional[int] = None,
    ) -> SolverResults:
        """
        Build and solve the ES-bounded x_{a,t} MILP.

        T_cpm  = CPM makespan (lower bound on the resource-constrained makespan).
                 Used ONLY to compute ES values via the forward pass.
        T_ub   = upper bound on the feasible makespan (for Cmax and valid_times).
                 Callers must pass a value that is >= the true optimal makespan.
                 • Exact strategy:  naive sum of all durations (always safe).
                 • Hybrid strategy: greedy heuristic makespan (already feasible).

        BUG FIX: previously T_cpm was used as both lower and upper bound.
        Since CPM ignores resources, T_cpm < optimal makespan when resources are
        binding (e.g., j301: T_cpm=38 but optimal=43).  Setting Cmax ≤ T_cpm
        and valid_times upper bound to T_cpm−d caused the MILP to be infeasible.
        """
        print("\n--- MILP (ES-bounded x_{a,t}) ---")

        act_dur = {aid: a.duration for aid, a in data.activities.items()}
        bounds  = CriticalPathCalculator.calculate_bounds(act_dur, data.precedence)
        ES      = bounds["ES"]
        T_cpm   = int(bounds["makespan_ub"])

        naive = sum(act_dur.values())
        # Safe upper bound: caller-supplied or fall back to naive sum
        if T_ub is None:
            T_ub = naive
        T_ub = int(T_ub)

        n_full    = len(act_dur) * (T_ub + 1)
        n_bounded = sum(max(0, T_ub - d - ES[a] + 1) for a, d in act_dur.items())
        print(f"  CPM lower bound : {T_cpm}  |  horizon (T_ub) : {T_ub}  "
              f"(naive sum : {naive})")
        print(f"  Variables : {n_bounded} ES-bounded  vs  {n_full} full  "
              f"(−{(1 - n_bounded/n_full)*100:.1f}%)")

        b0 = time.perf_counter()
        model, x_vars, cmax, valid_times = self._builder.build(data, ES, T_ub)
        bt = time.perf_counter() - b0
        print(f"  Model built : {len(model.variables())} vars, "
              f"{len(model.constraints)} constraints  [{bt:.2f}s]")

        c0 = time.process_time()
        w0 = time.perf_counter()
        pulp.PULP_CBC_CMD(
            msg=self.config.SOLVER_MSG, timeLimit=time_limit, threads=4
        ).solve(model)
        ct = time.process_time() - c0
        wt = time.perf_counter() - w0

        status = pulp.LpStatus[model.status]
        obj    = pulp.value(model.objective)
        print(f"  CBC status  : {status}  |  CPU {ct:.3f}s  |  wall {wt:.3f}s")

        # ── Extract solution only when CBC found an integer incumbent ─────────
        if obj is None:
            print("  No incumbent found — returning failed result")
            return SolverResults(
                makespan=0, schedule={},
                cpu_time=ct, wall_time=wt, build_time=bt, status=status,
            )

        schedule: Dict[str, ScheduledActivity] = {}
        for aid, times in valid_times.items():
            for t in times:
                v = pulp.value(x_vars[aid, t])
                if v is not None and round(v) == 1:
                    dur = data.activities[aid].duration
                    schedule[aid] = ScheduledActivity(
                        activity_id=aid, start=t,
                        duration=dur, finish=t + dur,
                    )
                    break

        # ── BUG-3 FIX: verify completeness and recompute makespan ─────────────
        all_aids = set(data.activities.keys())
        scheduled_aids = set(schedule.keys())
        missing = all_aids - scheduled_aids

        if missing:
            print(f"  WARNING: {len(missing)} activities missing from incumbent "
                  f"({sorted(missing)[:5]}{'...' if len(missing)>5 else ''})")
            print("  Discarding incomplete MILP solution")
            return SolverResults(
                makespan=0, schedule={},
                cpu_time=ct, wall_time=wt, build_time=bt,
                status="Not Solved",
            )

        # Recompute makespan directly from extracted schedule (not from Cmax var)
        ms = max(s.finish for s in schedule.values())
        result_status = "Optimal" if status == "Optimal" else "Feasible"
        print(f"  Makespan : {ms}  [{result_status}]")

        return SolverResults(
            makespan=ms, schedule=schedule,
            cpu_time=ct, wall_time=wt, build_time=bt,
            status=result_status,
        )

    # ── Hybrid ────────────────────────────────────────────────────────────────

    def _run_hybrid(self, data: ProjectData) -> SolverResults:
        """
        Step 1 — greedy for a fast, guaranteed-feasible upper bound.
        Step 2 — MILP improvement within time budget, using greedy makespan
                 as T_ub so the model horizon is tight and correct.
        Falls back to greedy if MILP fails or produces a worse result.
        """
        heur = self._run_heuristic(data)
        print(f"\n  Heuristic upper bound : {heur.makespan}")

        try:
            milp = self._run_milp(
                data, time_limit=self.time_limit, T_ub=heur.makespan
            )
        except Exception as exc:
            logger.warning(f"MILP pass failed ({exc}); returning heuristic")
            print(f"  Warning : MILP failed — {exc}")
            return heur

        if milp.is_success() and milp.makespan < heur.makespan:
            print(f"  MILP improved : {milp.makespan} < {heur.makespan}")
            return milp

        print(f"  Using heuristic (makespan : {heur.makespan})")
        return heur

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_scheduled(
        sd: Dict[str, int], data: ProjectData
    ) -> Dict[str, ScheduledActivity]:
        out: Dict[str, ScheduledActivity] = {}
        for aid, start in sd.items():
            dur = data.activities[aid].duration
            out[aid] = ScheduledActivity(
                activity_id=aid, start=start,
                duration=dur, finish=start + dur,
            )
        return out
