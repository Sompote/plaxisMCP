"""
Read calculation status + results from the Bangkok embankment model.
Tries Input API first, then Output API (port 10001) if available.
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
print("Connected Input:", s.server_full_name)


def val(prop):
    return prop.value if hasattr(prop, "value") else prop


# ── Phase status and LogInfo ──────────────────────────────────────────────────
print("\n=== Phase calculation status ===")
phases = g.Phases
RESULT_CODES = {0: "Not calculated", 1: "OK", 2: "OK (warnings)", 3: "Failed", 4: "Stopped"}
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    name = val(ph.Name)
    status = RESULT_CODES.get(cr, "Unknown(%s)" % cr)
    print("  [%d] %s : %s" % (i, name, status))
    try:
        log = val(ph.LogInfo)
        if log and str(log).strip():
            for line in str(log).strip().splitlines()[:15]:
                print("       |", line)
    except Exception as e:
        print("       | (LogInfo error: %s)" % e)


# ── Try to re-run Phase_2 if not calculated ───────────────────────────────────
phases = g.Phases
ph2 = phases[2]
cr2 = val(ph2.CalculationResult)
if cr2 == 0:
    print("\nPhase_2 not calculated – marking and re-running ...")
    try:
        ph2.ShouldCalculate = True
        r = s.call_and_handle_command("calculate")
        print("  calculate =>", r)
    except Exception as e:
        print("  ERROR:", e)
    phases = g.Phases
    for i in range(len(phases)):
        ph = phases[i]
        cr = val(ph.CalculationResult)
        print("  [%d] %s : %s" % (i, val(ph.Name), RESULT_CODES.get(cr, cr)))


# ── Try Output server for numerical results ───────────────────────────────────
print("\n=== Trying Output server (port 10001) ===")
try:
    s_out, g_out = new_server(HOST, 10001, password=PWD)
    print("Connected Output:", s_out.server_full_name)

    phases_out = g_out.Phases
    print("Output phases:", len(phases_out))

    # Max settlement Uy from Phase_1
    print("\n-- Max settlement Uy (Phase_1 Plastic) --")
    ph1_out = phases_out[1]
    try:
        uy = g_out.getresults(ph1_out, g_out.ResultTypes.Soil.Uy, "node")
        uy_list = list(uy)
        print("  Nodes sampled: %d" % len(uy_list))
        print("  Min Uy (max settlement) = %.4f m = %.1f mm" % (min(uy_list), min(uy_list)*1000))
        print("  Max Uy                  = %.4f m" % max(uy_list))
    except Exception as e:
        print("  Uy error:", e)
        # Try Uy via tabulate on soil elements
        try:
            r = s_out.call_and_handle_command("tabulate %s Uy" % val(ph1_out.Name))
            print("  tabulate Uy:", str(r)[:300])
        except Exception as e2:
            print("  tabulate error:", e2)

    # FoS from Phase_2
    print("\n-- Factor of Safety (Phase_2 Safety) --")
    ph2_out = phases_out[2]
    for rt_name in ["SumMsf", "Msf", "SumMSF"]:
        try:
            rt = getattr(g_out.ResultTypes.Soil, rt_name)
            msf = g_out.getresults(ph2_out, rt, "node")
            msf_list = list(msf)
            fos = max(msf_list)
            print("  FoS (max %s) = %.3f" % (rt_name, fos))
            break
        except Exception as e:
            print("  %s error: %s" % (rt_name, e))

except Exception as e:
    print("Output server not available:", str(e)[:100])

    # ── Fallback: extract Msf from Phase properties directly ─────────────────
    print("\n=== Fallback: Phase properties ===")
    phases = g.Phases
    ph1 = phases[1]
    ph2 = phases[2]

    # Look for Msf-related properties on Phase_2
    print("\nPhase_2 attributes (safety-related):")
    try:
        attrs = s.get_object_attributes(ph2)
        for k in sorted(attrs.keys()):
            if any(x in k.lower() for x in ["msf", "safety", "fos", "phi", "stage"]):
                try:
                    v = val(getattr(ph2, k))
                    print("  %s = %s" % (k, v))
                except Exception:
                    print("  %s [unreadable]" % k)
    except Exception as e:
        print("  Error:", e)

    # Look for settlement-related properties on Phase_1
    print("\nPhase_1 attributes (displacement-related):")
    try:
        attrs = s.get_object_attributes(ph1)
        for k in sorted(attrs.keys()):
            if any(x in k.lower() for x in ["u", "disp", "settle", "uy"]):
                try:
                    v = val(getattr(ph1, k))
                    print("  %s = %s" % (k, v))
                except Exception:
                    print("  %s [unreadable]" % k)
    except Exception as e:
        print("  Error:", e)

    # Try tabulate syntax variations
    print("\nTabulate syntax tests:")
    for cmd in [
        "tabulate Phase_1 Uy",
        "tabulate InitialPhase Uy",
        "tabulate Phase_2 SumMsf",
    ]:
        try:
            r = s.call_and_handle_command(cmd)
            print("  '%s' => %s" % (cmd, str(r)[:200]))
        except Exception as e:
            print("  '%s' => ERROR: %s" % (cmd, str(e)[:80]))

print("\nDone.")
