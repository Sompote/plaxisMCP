"""Apply boundary conditions to PLAXIS 2D model."""
import sys, types
_dm = types.ModuleType('distutils'); _dvm = types.ModuleType('distutils.version')
class _SV:
    def __init__(self,v): self.v=tuple(int(x) for x in v.split('.')[:3])
    def __ge__(self,o): return self.v>=o.v
_dvm.StrictVersion=_SV; _dm.version=_dvm
sys.modules['distutils']=_dm; sys.modules['distutils.version']=_dvm
sys.path.insert(0, r'C:\env\plaxismcp\plaxisMCP\plxscripting\src')
from plxscripting.easy import new_server

s, g = new_server('localhost', 10000, password='sompote')

print("=== BoreholePolygon_1 Lines ===")
bp = g.BoreholePolygon_1
try:
    lines = bp.Lines
    print(f"Lines type: {type(lines).__name__}")
    n = len(lines)
    print(f"Number of lines: {n}")
    for i in range(n):
        ln = lines[i]
        print(f"  Line[{i}]: {repr(ln)}")
        try:
            attrs = dir(ln)
            print(f"    attrs: {[a for a in attrs if not a.startswith('_')]}")
        except: pass
except Exception as e:
    print(f"Error: {e}")

print()
print("=== Try linedispl command ===")
for cmd in ['linedispl (0 -8) (40 -8)', 'linedispl (0 0) (40 0)']:
    try:
        r = s.call_and_handle_command(cmd)
        print(f"  '{cmd}' => {repr(r)[:200]}")
    except Exception as e:
        print(f"  '{cmd}' => ERROR: {e}")

print()
print("=== Existing LineDispls ===")
try:
    lds = g.LineDispls
    print(f"LineDispls count: {len(lds)}")
    for i in range(len(lds)):
        ld = lds[i]
        print(f"  [{i}]: {repr(ld)[:100]}")
        try:
            attrs = dir(ld)
            print(f"  attrs: {[a for a in attrs if not a.startswith('_')]}")
        except: pass
except Exception as e:
    print(f"Error: {e}")
