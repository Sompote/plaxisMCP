"""
Extract results from already-calculated Bangkok embankment model.
Tries both Input and Output APIs.
"""
import sys, types

_dm = types.ModuleType("distutils"); _dv = types.ModuleType("distutils.version")
class _SV:
    def __init__(self, v): self.v = tuple(int(x) for x in v.split(".")[:3])
    def __ge__(self, o): return self.v >= o.v
_dv.StrictVersion = _SV; _dm.version = _dv
sys.modules["distutils"] = _dm; sys.modules["distutils.version"] = _dv

sys.path.insert(0, r"C:\env\plaxismcp\plaxisMCP\plxscripting\src")
from plxscripting.easy import new_server

HOST, PWD = "localhost", "sompote"
s, g = new_server(HOST, 10000, password=PWD)
s.call_and_handle_command("gotostages")

def val(prop):
    return prop.value if hasattr(prop, "value") else prop

# ── Phase status ───────────────────────────────────────────────────────────────
phases = g.Phases
CODES = {0: "Not calc", 1: "OK", 2: "OK+warn", 3: "Failed", 4: "Stopped"}
print("Phase status:")
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    print("  [%d] %s : %s (LogInfo=%s)" % (i, val(ph.Name), CODES.get(cr, cr), val(ph.LogInfo)))

ph1 = phases[1]
ph2 = phases[2]

# ── Check Phase_1 step info ────────────────────────────────────────────────────
print("\nPhase_1 step info:")
for attr in ["FirstStep", "LastStep", "MaxSteps", "MaxIterations",
             "TimeInterval", "LoadFraction"]:
    try:
        v = val(getattr(ph1, attr))
        print("  %s = %s" % (attr, v))
    except Exception as e:
        print("  %s : N/A" % attr)

# ── Try getresults from Input server for Phase_1 ──────────────────────────────
print("\nTrying g.getresults() for Phase_1 Uy from Input server:")
try:
    uy = g.getresults(ph1, g.ResultTypes.Soil.Uy, "node")
    uy_list = list(uy)
    print("  Nodes: %d" % len(uy_list))
    print("  Min Uy = %.4f m = %.2f mm" % (min(uy_list), min(uy_list)*1000))
    print("  Max Uy = %.4f m" % max(uy_list))
except Exception as e:
    print("  Error: %s" % e)

# ── Try forcing Phase_2 calculation ────────────────────────────────────────────
print("\nTrying to force Phase_2 calculation:")
ph2.ShouldCalculate = True
# Unmark other phases
phases[0].ShouldCalculate = False
phases[1].ShouldCalculate = False
try:
    r = s.call_and_handle_command("calculate")
    print("  calculate => %s" % r)
except Exception as e:
    print("  ERROR: %s" % str(e)[:200])

# Re-check
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    print("  [%d] %s : %s" % (i, val(ph.Name), CODES.get(cr, cr)))

# ── Try getresults from Input for Phase_2 ─────────────────────────────────────
print("\nTrying g.getresults() for Phase_2 SumMsf:")
ph2 = phases[2]
for rt_name in ["SumMsf", "SumMSF", "Msf"]:
    try:
        rt = getattr(g.ResultTypes.Soil, rt_name)
        msf = g.getresults(ph2, rt, "node")
        msf_list = list(msf)
        print("  %s: max=%.3f  min=%.3f" % (rt_name, max(msf_list), min(msf_list)))
        break
    except Exception as e:
        print("  %s: %s" % (rt_name, e))

# ── Inspect available ResultTypes ─────────────────────────────────────────────
print("\nAvailable ResultTypes.Soil (settlement & stability):")
try:
    rt_soil = g.ResultTypes.Soil
    attrs = dir(rt_soil)
    for a in sorted(attrs):
        if not a.startswith("_"):
            if any(x in a.lower() for x in ["uy", "u ", "msf", "displ", "settle", "phi", "mstage"]):
                print("  ResultTypes.Soil.%s" % a)
except Exception as e:
    print("  Error: %s" % e)

# ── Output server ─────────────────────────────────────────────────────────────
print("\nTrying Output server (port 10001):")
try:
    s_out, g_out = new_server(HOST, 10001, password=PWD)
    print("Connected:", s_out.server_full_name)
    phases_out = g_out.Phases
    ph1_out = phases_out[1]
    ph2_out = phases_out[2]

    print("\n-- Settlement (Uy) Phase_1 --")
    try:
        uy = g_out.getresults(ph1_out, g_out.ResultTypes.Soil.Uy, "node")
        uy_list = list(uy)
        print("  Min Uy = %.4f m = %.2f mm" % (min(uy_list), min(uy_list)*1000))
    except Exception as e:
        print("  %s" % e)

    print("\n-- Factor of Safety (SumMsf) Phase_2 --")
    try:
        msf = g_out.getresults(ph2_out, g_out.ResultTypes.Soil.SumMsf, "node")
        msf_list = list(msf)
        print("  FoS = %.3f" % max(msf_list))
    except Exception as e:
        print("  %s" % e)

except Exception as e:
    print("Not available: %s" % str(e)[:80])
    print("\nPlease open PLAXIS Output manually to view results:")
    print("  - In the PLAXIS 2D GUI, click the output button after calculation")
    print("  - Or view results in the Staged Construction viewer")

print("\nDone.")
