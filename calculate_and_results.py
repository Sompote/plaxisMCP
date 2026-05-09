"""
Final calculation run + result extraction for Bangkok embankment model.
Expected results:
  - Phase_1 (Plastic): max settlement Uy (min value, most negative)
  - Phase_2 (Safety):  Factor of Safety from Msf (sum Msf at failure)
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
print("Connected: %s" % s.server_full_name)

def val(prop):
    return prop.value if hasattr(prop, "value") else prop


# ════════════════════════════════════════════════════════════════════════════
# 1. Verify phase setup
# ════════════════════════════════════════════════════════════════════════════
s.call_and_handle_command("gotostages")
phases = g.Phases
print("\nPhase setup:")
for i in range(len(phases)):
    ph = phases[i]
    ct = val(ph.DeformCalcType)
    ph_name = val(ph.Name)
    try:
        prev_name = val(ph.PreviousPhase.Name)
    except Exception:
        prev_name = "(none)"
    print("  [%d] %s  CalcType=%s  prev=%s" % (i, ph_name, ct, prev_name))


# ════════════════════════════════════════════════════════════════════════════
# 2. Re-mesh (ensures fresh mesh regardless of prior state)
# ════════════════════════════════════════════════════════════════════════════
print("\nGenerating mesh...")
s.call_and_handle_command("gotomesh")
try:
    r = s.call_and_handle_command("mesh 0.07")
    print("  %s" % r)
except Exception as e:
    print("  mesh error: %s" % e)


# ════════════════════════════════════════════════════════════════════════════
# 3. Mark all phases for calculation
# ════════════════════════════════════════════════════════════════════════════
s.call_and_handle_command("gotostages")
phases = g.Phases
for ph in phases:
    try:
        ph.ShouldCalculate = True
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════
# 4. Calculate
# ════════════════════════════════════════════════════════════════════════════
print("\nCalculating (all 3 phases)...")
t0 = time.time()
try:
    r = s.call_and_handle_command("calculate")
    elapsed = time.time() - t0
    print("  Done in %.1fs: %s" % (elapsed, r))
except Exception as e:
    elapsed = time.time() - t0
    print("  ERROR after %.1fs: %s" % (elapsed, e))

# ════════════════════════════════════════════════════════════════════════════
# 5. Check CalculationResult for each phase
# ════════════════════════════════════════════════════════════════════════════
print("\nCalculation results:")
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    print("  [%d] %s: CalculationResult=%s" % (i, val(ph.Name), cr))


# ════════════════════════════════════════════════════════════════════════════
# 6. Connect to Output for results
# ════════════════════════════════════════════════════════════════════════════
print("\n=== Connecting to Output for results ===")
try:
    from plxscripting.easy import new_server as new_server_out
    s_out, g_out = new_server_out("localhost", 10001, password="sompote")
    print("Output connected: %s" % s_out.server_full_name)

    # ── Max settlement (Uy) from Phase_1 ──────────────────────────────────
    print("\nMax settlement (Uy) in Phase_1:")
    try:
        phases_out = g_out.Phases
        phase1_out = phases_out[1]
        # Get Uy for all nodes
        uy_vals = g_out.getresults(phase1_out, g_out.ResultTypes.Soil.Uy, "node")
        if hasattr(uy_vals, "__iter__"):
            uy_list = list(uy_vals)
            min_uy = min(uy_list)
            max_uy = max(uy_list)
            print("  Min Uy (max settlement) = %.4f m" % min_uy)
            print("  Max Uy                  = %.4f m" % max_uy)
        else:
            print("  Uy result: %s" % uy_vals)
    except Exception as e:
        print("  Uy error: %s" % e)
        # Try alternative approach
        try:
            r = s.call_and_handle_command("tabulate Phase_1 Uy")
            print("  tabulate => %s" % str(r)[:200])
        except Exception as e2:
            print("  tabulate error: %s" % e2)

    # ── Factor of Safety (Msf) from Phase_2 ───────────────────────────────
    print("\nFactor of Safety (Msf) from Phase_2:")
    try:
        phase2_out = phases_out[2]
        msf_vals = g_out.getresults(phase2_out, g_out.ResultTypes.Soil.SumMsf, "node")
        if hasattr(msf_vals, "__iter__"):
            msf_list = list(msf_vals)
            max_msf = max(msf_list)
            print("  Max Msf (FoS) = %.3f" % max_msf)
        else:
            print("  Msf result: %s" % msf_vals)
    except Exception as e:
        print("  Msf error: %s" % e)

except Exception as e:
    print("Output connection error: %s" % e)
    # Fallback: use tabulate via Input
    print("\nTrying tabulate via Input server:")
    for cmd in ["tabulate Phase_1 Uy", "tabulate Phase_2 SumMsf"]:
        try:
            r = s.call_and_handle_command(cmd)
            print("  %s => %s" % (cmd, str(r)[:200]))
        except Exception as e2:
            print("  %s => ERROR: %s" % (cmd, e2))

print("\nDone.")
