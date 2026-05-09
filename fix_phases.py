"""
Fix the phase setup for the Bangkok embankment model.
Current state (4 phases):
  [0] InitialPhase: K0 (1) - correct
  [1] Phase_1: Consolidation (4) - need Plastic; Soil_5 already active
  [2] Phase_2: Safety (6) from InitialPhase - correct CalcType, wrong prev
  [3] Phase_3: Consolidation (4) from Phase_1 - delete this

Target:
  [0] InitialPhase: K0 (1)
  [1] Phase_1: Plastic, Soil_5 active, prev=InitialPhase
  [2] Phase_2: Safety (6), prev=Phase_1
"""
import sys, types

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

def phase_summary():
    phases = g.Phases
    print(f"  Total phases: {len(phases)}")
    for i in range(len(phases)):
        ph = phases[i]
        name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
        ct   = ph.DeformCalcType.value if hasattr(ph.DeformCalcType, "value") else ph.DeformCalcType
        try:
            prev = ph.PreviousPhase
            prev_name = prev.Name.value if hasattr(prev.Name, "value") else str(prev)
        except Exception:
            prev_name = "(none)"
        print(f"    [{i}] {name}  CalcType={ct}  prev={prev_name}")

print("BEFORE:")
phase_summary()
phases = g.Phases

phase1 = phases[1]
phase2 = phases[2]
phase3 = phases[3]

# ── Step 1: Delete Phase_3 ────────────────────────────────────────────────────
print("\nDeleting Phase_3…")
try:
    r = s.call_and_handle_command("delete Phase_3")
    print(f"  delete Phase_3 => {r}")
except Exception as e:
    print(f"  delete error: {e}")
    # Try undo instead
    try:
        r = s.call_and_handle_command("undo")
        print(f"  undo => {r}")
    except Exception as e2:
        print(f"  undo error: {e2}")

# Refresh
phases = g.Phases
print(f"  Phases after step 1: {len(phases)}")

# ── Step 2: Fix Phase_1 DeformCalcType to Plastic ────────────────────────────
print("\nSetting Phase_1 to Plastic…")
phases = g.Phases
phase1 = phases[1]
try:
    phase1.DeformCalcType = "plastic"
    val = phase1.DeformCalcType.value if hasattr(phase1.DeformCalcType, "value") else phase1.DeformCalcType
    print(f"  Phase_1 DeformCalcType = {val}")
except Exception as e:
    print(f"  Error: {e}")

# ── Step 3: Fix Phase_2 PreviousPhase to Phase_1 ─────────────────────────────
print("\nFixing Phase_2 PreviousPhase to Phase_1…")
phases = g.Phases
phase1 = phases[1]
phase2 = phases[2]
try:
    phase2.PreviousPhase = phase1
    prev = phase2.PreviousPhase
    prev_name = prev.Name.value if hasattr(prev.Name, "value") else str(prev)
    print(f"  Phase_2 PreviousPhase = {prev_name}")
except Exception as e:
    print(f"  Error: {e}")
    # Try via command
    try:
        r = s.call_and_handle_command("set Phase_2.PreviousPhase Phase_1")
        print(f"  set command => {r}")
    except Exception as e2:
        print(f"  set command error: {e2}")

# ── Step 4: Re-verify Soil_5 activation in Phase_1 ───────────────────────────
print("\nVerifying Soil_5 activation…")
soil5 = g.Soil_5
phases = g.Phases
phase0 = phases[0]
phase1 = phases[1]
for ph in [phase0, phase1]:
    ph_name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
    try:
        active_val = s.get_object_property(soil5, "Active", ph)
        val = active_val.value if hasattr(active_val, "value") else active_val
    except Exception as e:
        val = f"ERROR: {e}"
    print(f"  Soil_5.Active in {ph_name} = {val}")

print("\nAFTER:")
phase_summary()

# ── Step 5: Verify Phase_2 Identification ────────────────────────────────────
phases = g.Phases
if len(phases) >= 3:
    phase2 = phases[2]
    try:
        ident = phase2.Identification
        val = ident.value if hasattr(ident, "value") else ident
        print(f"\nPhase_2 Identification = '{val}'")
    except Exception as e:
        print(f"\nCould not read Phase_2 Identification: {e}")
    try:
        ct = phase2.DeformCalcType
        val = ct.value if hasattr(ct, "value") else ct
        print(f"Phase_2 DeformCalcType = {val}")
    except Exception as e:
        print(f"Error: {e}")

print("\nDone.")
