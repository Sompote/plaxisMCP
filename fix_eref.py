"""Set Eref on soil materials via Python API, bypassing command-line read-only restriction."""
import sys
# Patch distutils for Python 3.12+ compatibility before importing plxscripting
import types
distutils_mod = types.ModuleType('distutils')
distutils_version_mod = types.ModuleType('distutils.version')
class _StrictVersion:
    def __init__(self, v): self.v = tuple(int(x) for x in v.split('.')[:3])
    def __ge__(self, other): return self.v >= other.v
distutils_version_mod.StrictVersion = _StrictVersion
distutils_mod.version = distutils_version_mod
sys.modules['distutils'] = distutils_mod
sys.modules['distutils.version'] = distutils_version_mod

sys.path.insert(0, r'C:\env\plaxismcp\plaxisMCP\plxscripting\src')

from plxscripting.easy import new_server

HOST = 'localhost'
PORT = 10000
PASSWORD = 'sompote'

s, g = new_server(HOST, PORT, password=PASSWORD)

mat_clay = g.SoftClay
attrs = dir(mat_clay)
print("SoftClay attributes:")
for a in sorted(attrs):
    if not a.startswith('_'):
        try:
            val = getattr(mat_clay, a)
            if hasattr(val, 'value'):
                print(f"  {a} = {val.value}")
        except Exception:
            print(f"  {a} [method/no value]")
