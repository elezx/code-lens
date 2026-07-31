#!/usr/bin/env python3
"""Emit lizard's per-function metrics for one file as JSON on stdout.

Used by the code-lens `complexity` sensor: lizard has no stable machine-readable
CLI output, but its Python API does, so the sensor shells out to this script.
"""

import json
import sys

import lizard

result = lizard.analyze_file(sys.argv[1])
funcs = [
    {
        "name": f.name,
        "line": f.start_line,
        "cyclomatic": f.cyclomatic_complexity,
        "nloc": f.nloc,
        "params": f.parameter_count,
    }
    for f in result.function_list
]
print(json.dumps(funcs))
