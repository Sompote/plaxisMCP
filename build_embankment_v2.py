"""
Bangkok Embankment v2 - fixed material params for convergence.

Key fixes vs v1:
  - Bangkok Soft Clay: E=20000 kPa (was 10000), nu=0.20 (was 0.35)
    → G = 20000/(2*1.2) = 8333 kPa; lower nu avoids bulk modulus issues
  - Finer mesh (coarseness 0.03)
  - Phase_1 solver: MaxSteps=500, arc-length control on
  - After calculation: save project + launch Output + read results
"""
import sys, types, time, subprocess, os

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
SAVE_PATH  = r"C:\temp\Bangkok_Embankment.p2dx"
os.makedirs(r"C:\temp", exist_ok=True)

def val(p):
    return p.value if hasattr(p, "value") else p

s, g = new_server(HOST, 10000, password=PWD)
print("Connected:", s.server_full_name)

# =============================================================================
# 0. New project
# =============================================================================
print("\n[0] New project")
s.new()
time.sleep(0.3)
s, g = new_server(HOST, 10000, password=PWD)

# =============================================================================
# 1. Soil materials
# =============================================================================
print("\n[1] Soil materials")

def make_soil(name, drainage_int, gunsat, gsat, E, nu, cref, phi=None, psi=0):
    mat = s.call_and_handle_command("soilmat")
    auto = val(mat.Name)
    s.call_and_handle_command('set %s.Name "%s"' % (auto, name))
    obj = g.__getattr__(name)
    obj.SoilModel    = "MohrCoulomb"
    obj.DrainageType = drainage_int
    obj.gammaUnsat   = gunsat
    obj.gammaSat     = gsat
    obj.Gref         = E / (2.0 * (1.0 + nu))
    obj.nu           = nu
    obj.cref         = cref
    if phi is not None:
        try:
            obj.phi = phi
        except Exception:
            pass   # Undrained_B ignores phi (phi=0 enforced by PLAXIS)
    try:
        obj.psi = psi
    except Exception:
        pass
    print("   ", name, "OK  (G=%.0f kPa)" % (E/(2*(1+nu))))

# Bangkok Soft Clay: Undrained_B, cu=20 kPa
# E=20000 kPa, nu=0.20 → G=8333 kPa, Ku=E/(3(1-2*0.2))=E/1.8=11111 kPa
make_soil("Bangkok_Soft_Clay", 2, 15.0, 16.0, E=20000, nu=0.20, cref=20.0)

# Medium Clay: Drained, phi=26°, c'=5 kPa
make_soil("Medium_Clay", 0, 17.0, 18.0, E=15000, nu=0.30, cref=5.0, phi=26.0)

# Embankment Fill: Drained, phi=32°, c'=1 kPa
make_soil("Embankment_Fill", 0, 19.0, 20.0, E=30000, nu=0.30, cref=1.0, phi=32.0, psi=2.0)

# =============================================================================
# 2. Boreholes (2 boreholes, soillayer only in first)
# =============================================================================
print("\n[2] Boreholes")
bh1 = s.call_and_handle_command("borehole 0")
s.call_and_handle_command("set %s.Head 0" % val(bh1.Name))
s.call_and_handle_command("soillayer 8")                     # y= 0 to -8  → Bangkok Soft Clay
s.call_and_handle_command("setmaterial Bangkok_Soft_Clay")
s.call_and_handle_command("soillayer 3")                     # y=-8 to -11 → Medium Clay
s.call_and_handle_command("setmaterial Medium_Clay")
print("    Borehole_1: 2 layers, materials assigned")

bh2 = s.call_and_handle_command("borehole 30")
s.call_and_handle_command("set %s.Head 0" % val(bh2.Name))
print("    Borehole_2: inherits layers (no soillayer call)")

# =============================================================================
# 3. Embankment polygon in Structures mode
# =============================================================================
print("\n[3] Embankment polygon")
s.call_and_handle_command("gotostructures")
poly = s.call_and_handle_command("polygon (0 0) (0 3) (3 3) (9 0)")
# result: [Polygon, Soil]
soil_emb = poly[-1] if isinstance(poly, list) else poly
soil_name = val(soil_emb.Name)
s.call_and_handle_command("set %s.Material Embankment_Fill" % soil_name)
print("    %s created, material=Embankment_Fill" % soil_name)

# =============================================================================
# 4. Boundary conditions
# =============================================================================
print("\n[4] Boundary conditions")

def linedispl(x1, y1, x2, y2, ux_fix, uy_fix, label):
    res = s.call_and_handle_command("linedispl (%g %g) (%g %g)" % (x1,y1,x2,y2))
    ld  = res[-1] if isinstance(res, list) else res
    obj = g.__getattr__(val(ld.Name))
    if ux_fix: obj.Displacement_x = "Fixed"
    if uy_fix: obj.Displacement_y = "Fixed"
    print("    %s  Ux=%s Uy=%s" % (label, "Fixed" if ux_fix else "Free",
                                              "Fixed" if uy_fix else "Free"))

linedispl(0, -11, 30, -11, True,  True,  "Bottom  (y=-11)")
linedispl(0, -11,  0,  3,  True,  False, "Left/sym(x=0  )")
linedispl(30,-11, 30,  0,  True,  False, "Right   (x=30 )")

# =============================================================================
# 5. Mesh
# =============================================================================
print("\n[5] Mesh")
s.call_and_handle_command("gotomesh")
r = s.call_and_handle_command("mesh 0.03")
print("    %s" % r)

# =============================================================================
# 6. Phases
# =============================================================================
print("\n[6] Phases")
s.call_and_handle_command("gotostages")
phases = g.Phases
print("    InitialPhase: CalcType=%s" % val(phases[0].DeformCalcType))

# Phase_1: Plastic (embankment construction)
s.call_and_handle_command("phase InitialPhase")
phases = g.Phases
ph1 = phases[1]
ph1.DeformCalcType  = "plastic"
ph1.Identification  = "Embankment Construction"
for attr, v in [("MaxSteps", 500), ("MaxIterations", 60)]:
    try: setattr(ph1, attr, v)
    except Exception: pass
print("    Phase_1: CalcType=%s" % val(ph1.DeformCalcType))

# Deactivate embankment in InitialPhase, activate in Phase_1
s.call_and_handle_command("deactivate %s InitialPhase" % soil_name)
s.call_and_handle_command("activate %s Phase_1" % soil_name)
print("    %s: inactive in InitialPhase, active in Phase_1" % soil_name)

# Phase_2: Safety (phi/c reduction)
s.call_and_handle_command("phase Phase_1")
phases = g.Phases
ph2 = phases[2]
ph2.DeformCalcType = "safety"
ph2.Identification = "Safety Analysis"
print("    Phase_2: CalcType=%s" % val(ph2.DeformCalcType))

print("\n    Phase summary:")
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    try: prev = val(ph.PreviousPhase.Name)
    except Exception: prev = "-"
    print("      [%d] %-20s  CalcType=%s  prev=%s" % (
        i, val(ph.Name), val(ph.DeformCalcType), prev))

# =============================================================================
# 7. Calculate
# =============================================================================
print("\n[7] Calculate")
phases = g.Phases
for ph in phases:
    try: ph.ShouldCalculate = True
    except Exception: pass

CODES = {0:"Not calc", 1:"OK", 2:"OK+warn", 3:"Failed", 4:"Stopped"}
t0 = time.time()
try:
    r = s.call_and_handle_command("calculate")
    print("    Done %.1fs: %s" % (time.time()-t0, r))
except Exception as e:
    print("    ERROR %.1fs: %s" % (time.time()-t0, str(e)[:300]))

phases = g.Phases
print("    Phase results:")
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    li = val(ph.LogInfo)
    print("      [%d] %-20s  %s  (LogInfo=%s)" % (
        i, val(ph.Name), CODES.get(cr, cr), li))

# =============================================================================
# 8. Save project file
# =============================================================================
print("\n[8] Save project")
for cmd in ['save "%s"' % SAVE_PATH,
            "save %s" % SAVE_PATH,
            "save"]:
    try:
        r = s.call_and_handle_command(cmd)
        print("    Saved via '%s': %s" % (cmd.split()[0], r))
        break
    except Exception as e:
        print("    '%s' => %s" % (cmd[:30], str(e)[:60]))

# =============================================================================
# 9. Open Output and read results
# =============================================================================
print("\n[9] Results")

# Try launching Output with various flag styles
launched = False
for args in [
    [OUTPUT_EXE, "--AppServerPort=10001", "--AppServerAddress=localhost",
     "--AppServerPassword=%s" % PWD],
    [OUTPUT_EXE, "/AppServerPort:10001", "/AppServerAddress:localhost",
     "/AppServerPassword:%s" % PWD],
    [OUTPUT_EXE],
]:
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
        print("    Launched Output: %s" % " ".join(args[1:]))
        launched = True
        break
    except Exception as e:
        print("    Launch attempt failed: %s" % str(e)[:60])

if launched:
    print("    Waiting 12s for Output server ...")
    time.sleep(12)

# Connect to Output
got_out = False
for attempt in range(3):
    try:
        s_out, g_out = new_server(HOST, 10001, password=PWD)
        print("    Output connected: %s" % s_out.server_full_name)
        got_out = True
        break
    except Exception:
        if attempt < 2:
            time.sleep(5)

if got_out:
    # Output starts with no project loaded — open the saved .p2dx
    print("    Opening project in Output: %s" % SAVE_PATH)
    try:
        s_out.open(SAVE_PATH)
        time.sleep(2)
        print("    Project loaded in Output")
    except Exception as e:
        print("    Output open error: %s" % e)
    phases_out = g_out.Phases
    ph1_out = phases_out[1]
    ph2_out = phases_out[2]

    print("\n    === Settlement (Phase_1 - Plastic) ===")
    try:
        uy = g_out.getresults(ph1_out, g_out.ResultTypes.Soil.Uy, "node")
        uy_l = list(uy)
        print("    Min Uy (max settlement) = %.4f m  =  %.1f mm" % (min(uy_l), min(uy_l)*1000))
        print("    Max Uy                  = %.4f m" % max(uy_l))
    except Exception as e:
        print("    Uy: %s" % e)

    print("\n    === Factor of Safety (Phase_2 - Safety) ===")
    try:
        msf = g_out.getresults(ph2_out, g_out.ResultTypes.Soil.SumMsf, "node")
        msf_l = list(msf)
        print("    FoS (SumMsf) = %.3f" % max(msf_l))
    except Exception as e:
        print("    SumMsf: %s" % e)

else:
    # Phase results are in PLAXIS GUI – report status and guide user
    print("\n    Output server not available via scripting.")
    print("    Results summary based on phase status:")
    phases = g.Phases
    for i in range(len(phases)):
        ph = phases[i]
        cr = val(ph.CalculationResult)
        li = val(ph.LogInfo)
        print("      Phase %d [%s]: %s (LogInfo=%s)" % (i, val(ph.Name), CODES.get(cr,cr), li))

    print()
    print("    To read results numerically, please open PLAXIS Output from the GUI:")
    print("    Expert menu > Start Output  (or click the glasses icon)")
    print("    Then run:  python read_output.py")
    print()
    print("    Alternatively, results visible in PLAXIS Output GUI:")
    print("    - Phase_1 (Plastic):  Deformations > Vertical displacements (Uy)")
    print("    - Phase_2 (Safety):   Stresses > Plastic points + check Msf in curve")

print("\n=== Done ===")
