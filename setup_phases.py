"""
Configure calculation phases for the Bangkok embankment model.

Phase layout:
  InitialPhase : K0 Procedure      (DeformCalcType=1)  – natural ground, Soil_5 INACTIVE
  Phase_1      : Plastic           (DeformCalcType=3)  – Soil_5 ACTIVE (embankment built)
  Phase_2      : Safety / Phi-c   (DeformCalcType=6)  – follows Phase_1
"""
import sys, types

# ── distutils patch for Python 3.12+ ──────────────────────────────────────────
_dm = types.ModuleType("distutils")
_dvm = types.ModuleType("distutils.version")
class _SV:
    def __init__(self, v): self.v = tuple(int(x) for x in v.split(".")[:3])
    def __ge__(self, o): return self.v >= o.v
_dvm.StrictVersion = _SV; _dm.version = _dvm
sys.modules["distutils"] = _dm; sys.modules["distutils.version"] = _dvm

sys.path.insert(0, r"C:\env\plaxismcp\plaxisMCP\plxscripting\src")
from plxscripting.easy import new_server

s, g = new_server("localhost", 10000, password="sompote")
print(f"Connected: {s.server_full_name}")

# Ensure we are in staged-construction mode so Phases is visible
s.call_and_handle_command("gotostages")

# ── Inspect phases ─────────────────────────────────────────────────────────────
phases = g.Phases
n_phases = len(phases)
print(f"Phase count: {n_phases}")
for i in range(n_phases):
    ph = phases[i]
    name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
    ct   = ph.DeformCalcType.value if hasattr(ph.DeformCalcType, "value") else ph.DeformCalcType
    print(f"  [{i}] {name}  CalcType={ct}")

initial = phases[0]   # InitialPhase / K0

# ── Create Phase_1 (Plastic) from InitialPhase ────────────────────────────────
print("\nCreating Phase_1 (Plastic)…")
try:
    phase1 = s.call_and_handle_command("phase InitialPhase")
    print(f"  Created: {phase1}")
except Exception as e:
    print(f"  ERROR creating phase1: {e}")
    # If already created, grab it
    phase1 = phases[1] if len(phases) > 1 else None

if phase1 is None:
    print("Could not get Phase_1, aborting.")
    sys.exit(1)

# Refresh phases list
phases = g.Phases
phase1 = phases[1]

# Set CalcType = 3 (Plastic)
try:
    phase1.DeformCalcType = 3
    print(f"  Phase_1 DeformCalcType set to 3 (Plastic)")
except Exception as e:
    print(f"  DeformCalcType error: {e}")

# Set identification label
try:
    phase1.Identification = "Embankment construction"
    print(f"  Phase_1 Identification set")
except Exception as e:
    print(f"  Identification error: {e}")

# ── Activate Soil_5 (embankment polygon) in Phase_1 ─────────────────────────
print("\nActivating Soil_5 in Phase_1…")
soil5 = g.Soil_5
# PLAXIS 2D staged construction: activate via command
try:
    result = s.call_and_handle_command(f"activate Soil_5 Phase_1")
    print(f"  activate command => {result}")
except Exception as e:
    print(f"  activate command error: {e}")
    # Fallback: set Active property on the staged IP
    try:
        active_ip = soil5.Active
        # active_ip[phase1] = True
        g.set(active_ip, phase1)
        print(f"  Activated via g.set(active_ip, phase1)")
    except Exception as e2:
        print(f"  g.set fallback error: {e2}")

# Verify Soil_5 status in InitialPhase
print("\nVerifying Soil_5 status in InitialPhase…")
try:
    active_initial = s.get_object_property(soil5, "Active", initial)
    val = active_initial.value if hasattr(active_initial, "value") else active_initial
    print(f"  Soil_5.Active in InitialPhase = {val}")
except Exception as e:
    print(f"  Could not read Soil_5.Active in InitialPhase: {e}")

# ── Create Phase_2 (Safety) from Phase_1 ─────────────────────────────────────
print("\nCreating Phase_2 (Safety/Phi-c reduction)…")
try:
    phase2 = s.call_and_handle_command("phase Phase_1")
    print(f"  Created: {phase2}")
except Exception as e:
    print(f"  ERROR creating phase2: {e}")
    phase2 = phases[2] if len(phases) > 2 else None

if phase2 is None:
    print("Could not get Phase_2, aborting.")
    sys.exit(1)

# Refresh
phases = g.Phases
phase2 = phases[2]

# Set CalcType = 6 (Safety / Phi-c reduction)
try:
    phase2.DeformCalcType = 6
    print(f"  Phase_2 DeformCalcType set to 6 (Safety)")
except Exception as e:
    print(f"  DeformCalcType error: {e}")

# Set identification
try:
    phase2.Identification = "Safety analysis"
    print(f"  Phase_2 Identification set")
except Exception as e:
    print(f"  Identification error: {e}")

# ── Final summary ─────────────────────────────────────────────────────────────
print("\n=== Phase summary ===")
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    name = ph.Name.value if hasattr(ph.Name, "value") else ph.Name
    ct   = ph.DeformCalcType.value if hasattr(ph.DeformCalcType, "value") else ph.DeformCalcType
    prev_name = ""
    try:
        prev = ph.PreviousPhase
        prev_name = prev.Name.value if hasattr(prev.Name, "value") else str(prev)
    except Exception:
        pass
    print(f"  [{i}] {name}  CalcType={ct}  prev={prev_name}")

print("\nDone.")
