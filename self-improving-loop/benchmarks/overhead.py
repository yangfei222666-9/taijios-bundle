"""
Overhead benchmark — measures self-improving-loop vs direct call.

Runs three workload profiles (instant / 10 ms / 100 ms) x two modes (direct
call vs wrapped), 200 iterations each, reports the overhead as absolute ms
and relative %.

Usage:
    python benchmarks/overhead.py
"""
import statistics
import tempfile
import time
from pathlib import Path

from self_improving_loop import SelfImprovingLoop


def work_instant():
    return 42


def work_10ms():
    time.sleep(0.010)
    return 42


def work_100ms():
    time.sleep(0.100)
    return 42


WORKLOADS = {
    "instant (<1 μs)": work_instant,
    "10 ms sleep": work_10ms,
    "100 ms sleep": work_100ms,
}

ITERATIONS = 200


def time_direct(fn, n):
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return samples


def time_wrapped(loop, agent_id, fn, n):
    samples = []
    for i in range(n):
        t0 = time.perf_counter()
        loop.execute_with_improvement(
            agent_id=f"{agent_id}-{i}",  # fresh agent_id each call to avoid trigger logic
            task="bench",
            execute_fn=fn,
        )
        samples.append(time.perf_counter() - t0)
    return samples


def stats(samples_sec):
    s_ms = [s * 1000 for s in samples_sec]
    s_ms.sort()
    return {
        "mean_ms": statistics.mean(s_ms),
        "median_ms": s_ms[len(s_ms) // 2],
        "p95_ms": s_ms[int(len(s_ms) * 0.95)],
        "min_ms": min(s_ms),
        "max_ms": max(s_ms),
    }


def fmt(v):
    return f"{v:.3f}"


def main():
    print(f"self-improving-loop · overhead benchmark · {ITERATIONS} iters / workload\n")
    print(f"{'workload':<18}  {'mode':<9}  "
          f"{'mean':>9}  {'median':>9}  {'p95':>9}  "
          f"{'overhead':>10}")
    print("-" * 78)

    with tempfile.TemporaryDirectory() as tmpdir:
        loop = SelfImprovingLoop(data_dir=tmpdir)

        for name, fn in WORKLOADS.items():
            # warm up once to avoid cold-start pollution
            fn()
            loop.execute_with_improvement(agent_id="warmup", task="w", execute_fn=fn)

            direct = stats(time_direct(fn, ITERATIONS))
            wrapped = stats(time_wrapped(loop, "bench", fn, ITERATIONS))

            abs_overhead_ms = wrapped["mean_ms"] - direct["mean_ms"]
            if direct["mean_ms"] > 0:
                rel_overhead = (abs_overhead_ms / direct["mean_ms"]) * 100
                rel_str = f"+{rel_overhead:.1f}%"
            else:
                rel_str = "n/a"

            print(f"{name:<18}  {'direct':<9}  "
                  f"{fmt(direct['mean_ms']):>9}  {fmt(direct['median_ms']):>9}  "
                  f"{fmt(direct['p95_ms']):>9}  {'—':>10}")
            print(f"{name:<18}  {'wrapped':<9}  "
                  f"{fmt(wrapped['mean_ms']):>9}  {fmt(wrapped['median_ms']):>9}  "
                  f"{fmt(wrapped['p95_ms']):>9}  "
                  f"{'+'+fmt(abs_overhead_ms)+' ms ('+rel_str+')':>10}")
            print()


if __name__ == "__main__":
    main()
