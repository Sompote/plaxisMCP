"""
Complete setup and calculation for Bangkok embankment model.
Handles: mesh regeneration + correct Safety phase ordinal + results extraction.
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
print(f"Connected: {s.server_full_name}")


# ── Helper ────────────────────────────────────────────────────────────────────
def val(prop):
    return prop.value if hasattr(prop, "value") else prop

def phase_summary():
    s.call_and_handle_command("gotostages")
    phases = g.Phases
    print(f"  {len(phases)} phases:")
    for i in range(len(phases)):
        ph = phases[i]
        ct = val(ph.DeformCalcType)
        try:
            prev_name = val(ph.PreviousPhase.Name)
        except Exception:
            prev_name = "(none)"
        print(f"    [{i}] {val(ph.Name)}  CalcType={ct}  prev={prev_name}")


# ════════════════════════════════════════════════════════════════════════════
# Step 1: Fix Phase_2 to Safety using string "safety"
# ════════════════════════════════════════════════════════════════════════════
s.call_and_handle_command("gotostages")
phases = g.Phases
print("=== Phase setup before fix ===")
phase_summary()

print("\nFinding Safety ordinal by trying string 'safety'…")
phases = g.Phases
phase2 = phases[2]
try:
    phase2.DeformCalcType = "safety"
    ct = val(phase2.DeformCalcType)
    print(f"  'safety' accepted → DeformCalcType={ct}")
except Exception as e:
    print(f"  string 'safety' error: {e}")
    # Try integer 7
    for candidate in [5, 7, 8, 9]:
        try:
            phase2.DeformCalcType = candidate
            ct = val(phase2.DeformCalcType)
            print(f"  integer {candidate} → DeformCalcType={ct}")
            break
        except Exception as e2:
            print(f"  integer {candidate} error: {e2}")

print()
phase_summary()

# Verify Phase_1 is Plastic
phases = g.Phases
phase1 = phases[1]
print(f"\nPhase_1 DeformCalcType = {val(phase1.DeformCalcType)}")
print(f"Phase_2 DeformCalcType = {val(phases[2].DeformCalcType)}")


# ════════════════════════════════════════════════════════════════════════════
# Step 2: Verify and fix Soil_5 activation in Phase_1
# ════════════════════════════════════════════════════════════════════════════
print("\n=== Verifying embankment soil activation ===")
soil5 = g.Soil_5
phase0 = phases[0]
phase1 = phases[1]

# Try activating Soil_5 explicitly (safe to call even if already active)
try:
    r = s.call_and_handle_command("activate Soil_5 Phase_1")
    print(f"  activate Soil_5 Phase_1 => {r}")
except Exception as e:
    print(f"  activate error: {e}")

# Deactivate in InitialPhase (should not be active there)
try:
    r = s.call_and_handle_command("deactivate Soil_5 InitialPhase")
    print(f"  deactivate Soil_5 InitialPhase => {r}")
except Exception as e:
    print(f"  deactivate error: {e}")


# ════════════════════════════════════════════════════════════════════════════
# Step 3: Regenerate mesh (in case it was lost)
# ════════════════════════════════════════════════════════════════════════════
print("\n=== Mesh generation ===")
s.call_and_handle_command("gotomesh")
try:
    r = s.call_and_handle_command("mesh 0.07")
    mesh_info = r
    print(f"  Mesh: {mesh_info}")
except Exception as e:
    print(f"  Mesh error: {e}")


# ════════════════════════════════════════════════════════════════════════════
# Step 4: Calculate
# ════════════════════════════════════════════════════════════════════════════
print("\n=== Starting calculation ===")
s.call_and_handle_command("gotostages")
phases = g.Phases
for ph in phases:
    try:
        ph.ShouldCalculate = True
    except Exception:
        pass

t0 = time.time()
try:
    result = s.call_and_handle_command("calculate")
    elapsed = time.time() - t0
    print(f"  calculate => {result}  ({elapsed:.1f}s)")
except Exception as e:
    elapsed = time.time() - t0
    print(f"  calculate error ({elapsed:.1f}s): {e}")

# Check results
print("\n=== Calculation result status ===")
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    print(f"  [{i}] {val(ph.Name)}: CalculationResult={cr}")
    # 0=ok, 1=warning, 2=error(?), check PLAXIS docs

print("\nDone.")
