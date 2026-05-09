"""Find Safety phase ordinal and fix Phase_2."""
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

def val(prop):
    return prop.value if hasattr(prop, "value") else prop

phases = g.Phases
phase2 = phases[2]

print("Testing DeformCalcType values for Phase_2:")
for candidate in [3, 5, 7, 10, 11, 12]:
    try:
        phase2.DeformCalcType = candidate
        ct = val(phase2.DeformCalcType)
        print("  %d => %s" % (candidate, ct))
    except Exception as e:
        msg = str(e)[:80]
        print("  %d => ERROR: %s" % (candidate, msg))

print("\nSetting 'safety' string:")
try:
    phase2.DeformCalcType = "safety"
    ct = val(phase2.DeformCalcType)
    print("  'safety' => %s" % ct)
except Exception as e:
    print("  error: %s" % str(e)[:120])

print("\nFinal Phase_2 DeformCalcType = %s" % val(phase2.DeformCalcType))

# Also check all allowed strings
print("\nTesting all string values:")
for s_val in ["plastic", "consolidation", "safety", "dynamic",
              "fullycoupledflowdeformation", "dynamicwithconsolidation"]:
    try:
        phase2.DeformCalcType = s_val
        ct = val(phase2.DeformCalcType)
        print("  '%s' => %s" % (s_val, ct))
    except Exception as e:
        print("  '%s' => ERROR: %s" % (s_val, str(e)[:80]))
