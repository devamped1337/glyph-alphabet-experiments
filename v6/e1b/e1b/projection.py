"""Timing projection and C60/C100 selector (PREREG_E1b §5 as replaced by Amendment A1.1).
projected_stage_s = sum over call types (measured elapsed per representative call or batch x count) + setup.
C100 only if every stage B1, B2, B3 projects <= headroom x budget; else C60 by the same rule; else
'insufficient budget'. Uses only pilot timings (never accuracy)."""

def call_counts(cfg, cname, n_models=2):
    c = cfg["configs"][cname]; F = len(cfg["families_core"]); E = c["core_per_family"] * F
    T = cfg["test_cases_per_entry"]; P = c["planted_calib"]; PT = cfg["planted_testgate"]; L = cfg["f3l_entries"]
    probes = cfg["probes_per_entry_min"]; items = (E + L) * T; sanity = cfg["sanity_subset_per_family"] * F * T
    cache = cfg["cache"]["fixed_per_model"] + cfg["cache"]["hard_per_model"]
    return {
        "B1": {"probe": n_models * probes * (E + P + E + PT), "receiver": 5 * P},   # calib + testgate + manip (strong model)
        "B2": {"receiver": n_models * (items * 2 + 2 * sanity + cfg["byte_identity_paired_items"] + 4 * cache) ,
               "receiver_warm": n_models * items * 2},
        "B3": {"sender": n_models * (E + L), "receiver": n_models * items * 2},
    }

def project(cfg, timings, cname):
    """timings: {call_type: {model: seconds per call}, 'setup_s': {model: seconds}} measured in B0 pilot.
    Per-call time is taken as the max over the pair (models run sequentially, both must fit)."""
    cc = call_counts(cfg, cname); out = {}
    for st, calls in cc.items():
        s = 0.0
        for ctype, n in calls.items():
            per = timings[ctype if ctype in timings else "receiver"]
            s += (n / 2) * sum(per.values())          # n counts both models; sum = each model's share
        s += sum(timings["setup_s"].values())
        out[st] = dict(projected_h=round(s / 3600, 3), budget_h=cfg["budgets_gpu_h"][st])
    return out

def choose(cfg, timings):
    h = cfg["c100_headroom"]; rep = {}
    for cname in ("C100", "C60"):
        p = project(cfg, timings, cname); rep[cname] = p
        if all(v["projected_h"] <= h * v["budget_h"] for v in p.values()):
            return dict(choice=cname, projections=rep, rule=f"every stage <= {h} x budget")
    return dict(choice="INSUFFICIENT_BUDGET", projections=rep, rule=f"every stage <= {h} x budget")
