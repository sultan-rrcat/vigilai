import pandas as pd
import json

records = [json.loads(l) for l in open("../logs/perf.jsonl")]
df = pd.json_normalize(records)  # flattens stages_ms.* and config.* into columns

# Average latency per stage
print(df[["stages_ms.inference","stages_ms.tracker","stages_ms.zone_engine"]].mean())

# Compare FPS across different frame_stride values
print(df.groupby("config.frame_stride")["fps"].mean())

# CPU usage over time
df["ts"] = pd.to_datetime(df["ts"])
df.set_index("ts")[["cpu_pct","fps"]].plot()