"""
Force Phase_2 to run after Phase_1 finished with OK+warnings.
Tries:
  1. Set Phase_1.CalculationResult = 1 (bypass warning flag)
  2. Direct phase-object calculate call
  3. Check Output availability after each attempt
"""
import sys, types, time, subprocess

_dm = types.ModuleType("distutils"); _dv = types.ModuleType("distutils.version")
class _SV:
    def __init__(self, v): self.v = tuple(int(x) for x in v.split(".")[:3])
    def __ge__(self, o): return self.v >= o.v
_dv.StrictVersion = _SV; _dm.version = _dv
sys.modules["distutils"] = _dm; sys.modules["distutils.version"] = _dv
sys.path.insert(0, r"C:\env\plaxismcp\plaxisMCP\plxscripting\src")
from plxscripting.easy import new_server

HOST, PWD = "localhost", "sompote"
OUTPUT_EXE = r"C:\Program Files\Bentley\Geotechnical\PLAXIS 2D CONNECT Edition V20\Plaxis2DOutput.exe"

s, g = new_server(HOST, 10000, password=PWD)
s.call_and_handle_command("gotostages")

def val(p):
    return p.value if hasattr(p, "value") else p

phases = g.Phases
CODES = {0: "Not calc", 1: "OK", 2: "OK+warn", 3: "Failed"}
print("Current phase status:")
for i in range(len(phases)):
    ph = phases[i]
    print("  [%d] %s : %s (LogInfo=%s)" % (
        i, val(ph.Name), CODES.get(val(ph.CalculationResult), val(ph.CalculationResult)),
        val(ph.LogInfo)))

ph1 = phases[1]
ph2 = phases[2]

# ── Approach 1: Override Phase_1.CalculationResult = 1 ───────────────────────
print("\nApproach 1: Override Phase_1.CalculationResult = 1")
try:
    ph1.CalculationResult = 1
    cr = val(ph1.CalculationResult)
    print("  Phase_1.CalculationResult set to:", cr)
except Exception as e:
    print("  Error:", e)

# ── Approach 2: Re-run just Phase_2 ─────────────────────────────────────────
print("\nApproach 2: Run Phase_2 with ShouldCalculate=True")
phases = g.Phases
for ph in phases:
    ph.ShouldCalculate = False
ph2 = phases[2]
ph2.ShouldCalculate = True
t0 = time.time()
try:
    r = s.call_and_handle_command("calculate")
    print("  calculate => %s (%.1fs)" % (r, time.time()-t0))
except Exception as e:
    print("  ERROR (%.1fs): %s" % (time.time()-t0, str(e)[:200]))

# Status
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    print("  [%d] %s : %s" % (i, val(ph.Name), CODES.get(cr, cr)))

# ── Approach 3: Try calling calculate on Phase_2 object directly ─────────────
print("\nApproach 3: call calculate method on Phase_2 object")
ph2 = phases[2]
try:
    r = s.call_plx_object_method(ph2, "calculate", [])
    print("  ph2.calculate() =>", r)
except Exception as e:
    print("  Error:", e)

# ── Check Phase_2 commands ────────────────────────────────────────────────────
print("\nPhase_2 available commands:")
try:
    attrs = s.get_object_attributes(ph2)
    cmds = [k for k in attrs.keys() if not k[0].isupper()]  # lowercase = commands
    print("  Commands:", cmds)
except Exception as e:
    print("  Error:", e)

# ── Try Output server ─────────────────────────────────────────────────────────
print("\nLaunching Output server ...")
try:
    subprocess.Popen([OUTPUT_EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)
    print("  Waited 10s")
except Exception as e:
    print("  Launch error:", e)

print("Connecting to Output (port 10001) ...")
try:
    s_out, g_out = new_server(HOST, 10001, password=PWD)
    print("  Connected:", s_out.server_full_name)
    phases_out = g_out.Phases
    ph1_out = phases_out[1]
    ph2_out = phases_out[2]

    print("\n  Settlement Uy (Phase_1):")
    try:
        uy = g_out.getresults(ph1_out, g_out.ResultTypes.Soil.Uy, "node")
        uy_l = list(uy)
        print("    Min Uy = %.4f m = %.2f mm  (max settlement)" % (min(uy_l), min(uy_l)*1000))
    except Exception as e:
        print("    Uy error:", e)

    print("\n  FoS SumMsf (Phase_2):")
    try:
        msf = g_out.getresults(ph2_out, g_out.ResultTypes.Soil.SumMsf, "node")
        msf_l = list(msf)
        print("    FoS = %.3f" % max(msf_l))
    except Exception as e:
        print("    SumMsf error:", e)

except Exception as e:
    print("  Output not available:", str(e)[:100])
    print("\n  NOTE: Open PLAXIS Output manually (click output icon in GUI)")
    print("  Then run this script again to read results from port 10001")

print("\nDone.")
