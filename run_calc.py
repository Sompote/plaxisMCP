"""
Run PLAXIS 2D calculation for the Bangkok embankment model and extract results.
"""
import sys, types, time

_dm = types.ModuleType("distutils"); _dvm = types.ModuleType("distutils.version")
class _SV:
    def __init__(self, v): self.v = tuple(int(x) for x in v.split(".")[:3])
    def __ge__(self, o): return self.v >= o.v
_dvm.StrictVersion = _SV; _dm.version = _dvm
sys.modules["distutils"] = _dm; sys.modules["distutils.version"] = _dvm

sys.path.insert(0, r"C:\env\plaxismcp\plaxisMCP\plxscripting\src")
from plxscripting.easy import new_server

s, g = new_server("localhost", 10000, password="sompote")
s.call_and_handle_command("gotostages")
print(f"Connected: {s.server_full_name}")

phases = g.Phases
n = len(phases)
print(f"Phase count: {n}")
for i in range(n):
    ph = phases[i]
    name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
    ct   = ph.DeformCalcType.value if hasattr(ph.DeformCalcType, "value") else ph.DeformCalcType
    print(f"  [{i}] {name}  CalcType={ct}")

# ── Mark all phases for calculation ─────────────────────────────────────────
print("\nMarking phases for calculation…")
for i in range(n):
    ph = phases[i]
    ph_name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
    try:
        ph.ShouldCalculate = True
        print(f"  {ph_name}: ShouldCalculate = True")
    except Exception as e:
        print(f"  {ph_name}: {e}")

# ── Run calculation ──────────────────────────────────────────────────────────
print("\nStarting calculation (this may take a while)…")
t0 = time.time()
try:
    result = s.call_and_handle_command("calculate")
    elapsed = time.time() - t0
    print(f"  calculate => {result} (elapsed: {elapsed:.1f}s)")
except Exception as e:
    elapsed = time.time() - t0
    print(f"  calculate error (elapsed {elapsed:.1f}s): {e}")

# Alternatively, try g.calculate() method
print("\nTrying g.calculate()…")
try:
    result = s.call_plx_object_method(g.plx_global if hasattr(g, "plx_global") else g, "calculate", [])
    print(f"  g.calculate() => {result}")
except Exception as e:
    print(f"  Error: {e}")

# ── Check calculation results ────────────────────────────────────────────────
print("\nChecking phase results…")
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    ph_name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
    try:
        cr = ph.CalculationResult
        val = cr.value if hasattr(cr, "value") else cr
        print(f"  {ph_name} CalculationResult = {val}")
    except Exception as e:
        print(f"  {ph_name} result error: {e}")

print("\nDone.")
