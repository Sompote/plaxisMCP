"""
Bangkok Embankment - Complete PLAXIS 2D model from scratch.

Model:  Half-model, symmetry at x=0
Domain: x=0..30 m, y=-11..+3 m
Layers: Bangkok Soft Clay 0..-8 m  (Undrained_B, cu=20 kPa)
        Medium Clay       -8..-11 m (Drained, phi=26 deg)
Embankment polygon: (0,0)-(0,3)-(3,3)-(9,0)  [fill, phi=32 deg]

Phases:
  InitialPhase : K0 Procedure
  Phase_1      : Plastic  (embankment activated)
  Phase_2      : Safety   (Phi-c reduction)

Results reported: max settlement Uy (Phase_1), FoS=Msf (Phase_2)
"""
import sys, types, time

# --- distutils patch for Python 3.12+ ---
_dm = types.ModuleType("distutils"); _dv = types.ModuleType("distutils.version")
class _SV:
    def __init__(self, v): self.v = tuple(int(x) for x in v.split(".")[:3])
    def __ge__(self, o): return self.v >= o.v
_dv.StrictVersion = _SV; _dm.version = _dv
sys.modules["distutils"] = _dm; sys.modules["distutils.version"] = _dv

sys.path.insert(0, r"C:\env\plaxismcp\plaxisMCP\plxscripting\src")
from plxscripting.easy import new_server

HOST, PORT, PWD = "localhost", 10000, "sompote"
s, g = new_server(HOST, PORT, password=PWD)
print("Connected:", s.server_full_name)


# =============================================================================
# STEP 0 – New project
# =============================================================================
print("\n[0] New project ...")
s.new()
print("    OK")

time.sleep(0.5)
s, g = new_server(HOST, PORT, password=PWD)   # reconnect (session reset)


# =============================================================================
# STEP 1 – Soil materials
# =============================================================================
print("\n[1] Creating soil materials ...")

def set_mat(mat, **props):
    for k, v in props.items():
        try:
            setattr(mat, k, v)
        except Exception as e:
            print("    WARNING %s.%s=%s : %s" % (mat.Name.value, k, v, e))

# Bangkok Soft Clay  (Undrained_B, Mohr-Coulomb, cu=20 kPa)
mat_bsc = s.call_and_handle_command("soilmat")
bsc_name = mat_bsc.Name.value if hasattr(mat_bsc.Name, "value") else str(mat_bsc)
s.call_and_handle_command('set %s.Name "Bangkok_Soft_Clay"' % bsc_name)
mat_bsc = g.Bangkok_Soft_Clay
set_mat(mat_bsc,
    SoilModel        = "MohrCoulomb",
    DrainageType     = 2,          # Undrained_B
    gammaUnsat       = 15.0,
    gammaSat         = 16.0,
    Gref             = 10000.0/(2*(1+0.35)),   # E=10000 kPa, nu=0.35
    nu               = 0.35,
    cref             = 20.0,
)
print("    Bangkok_Soft_Clay OK")

# Medium Clay  (Drained, phi=26 deg)
mat_mc = s.call_and_handle_command("soilmat")
mc_name = mat_mc.Name.value if hasattr(mat_mc.Name, "value") else str(mat_mc)
s.call_and_handle_command('set %s.Name "Medium_Clay"' % mc_name)
mat_mc = g.Medium_Clay
set_mat(mat_mc,
    SoilModel        = "MohrCoulomb",
    DrainageType     = 0,          # Drained
    gammaUnsat       = 17.0,
    gammaSat         = 18.0,
    Gref             = 8000.0/(2*(1+0.30)),
    nu               = 0.30,
    cref             = 5.0,
    phi              = 26.0,
    psi              = 0.0,
)
print("    Medium_Clay OK")

# Embankment Fill  (Drained, phi=32 deg)
mat_ef = s.call_and_handle_command("soilmat")
ef_name = mat_ef.Name.value if hasattr(mat_ef.Name, "value") else str(mat_ef)
s.call_and_handle_command('set %s.Name "Embankment_Fill"' % ef_name)
mat_ef = g.Embankment_Fill
set_mat(mat_ef,
    SoilModel        = "MohrCoulomb",
    DrainageType     = 0,
    gammaUnsat       = 19.0,
    gammaSat         = 20.0,
    Gref             = 20000.0/(2*(1+0.30)),
    nu               = 0.30,
    cref             = 1.0,
    phi              = 32.0,
    psi              = 2.0,
)
print("    Embankment_Fill OK")


# =============================================================================
# STEP 2 – Boreholes (CORRECT: only first borehole calls soillayer)
# =============================================================================
print("\n[2] Creating boreholes ...")

# --- Borehole 1 at x=0 ---
bh1 = s.call_and_handle_command("borehole 0")
bh1_name = bh1.Name.value if hasattr(bh1.Name, "value") else "Borehole_1"
s.call_and_handle_command("set %s.Head 0" % bh1_name)

# Add soil layers (GLOBAL layer scheme – do this ONLY in the first borehole)
# Call setmaterial immediately after soillayer while context is set
s.call_and_handle_command("soillayer 8")                          # y=0 to y=-8
s.call_and_handle_command("setmaterial Bangkok_Soft_Clay")        # assign to layer 1
s.call_and_handle_command("soillayer 3")                          # y=-8 to y=-11
s.call_and_handle_command("setmaterial Medium_Clay")              # assign to layer 2
print("    Borehole_1 created with 2 layers (total 11 m), materials assigned")

# --- Borehole 2 at x=30 ---
# Do NOT call soillayer here – layers are global, borehole 2 inherits them
bh2 = s.call_and_handle_command("borehole 30")
bh2_name = bh2.Name.value if hasattr(bh2.Name, "value") else "Borehole_2"
s.call_and_handle_command("set %s.Head 0" % bh2_name)
print("    Borehole_2 created (inherits same layers)")

# Verify layer count
try:
    bhs = g.Boreholes
    print("    Total boreholes: %d" % len(bhs))
except Exception:
    pass


# =============================================================================
# STEP 3 – Embankment polygon in Structures mode
# =============================================================================
print("\n[3] Creating embankment polygon ...")
s.call_and_handle_command("gotostructures")

poly = s.call_and_handle_command("polygon (0 0) (0 3) (3 3) (9 0)")
# poly is [Polygon, Soil]
soil_emb = None
if isinstance(poly, list):
    for obj in poly:
        if hasattr(obj, "_plx_type") and "Soil" in obj._plx_type:
            soil_emb = obj
            break
if soil_emb is None and isinstance(poly, list) and len(poly) > 1:
    soil_emb = poly[-1]   # last object is the Soil cluster

if soil_emb:
    soil_name = soil_emb.Name.value if hasattr(soil_emb.Name, "value") else str(soil_emb)
    s.call_and_handle_command("set %s.Material Embankment_Fill" % soil_name)
    print("    Polygon created: %s  material=Embankment_Fill" % soil_name)
else:
    print("    WARNING: could not identify Soil object from polygon result")
    print("    poly =", poly)


# =============================================================================
# STEP 4 – Boundary conditions (linedispl)
# =============================================================================
print("\n[4] Applying boundary conditions ...")

def make_linedispl(x1, y1, x2, y2, ux_fixed, uy_fixed, label):
    result = s.call_and_handle_command(
        "linedispl (%g %g) (%g %g)" % (x1, y1, x2, y2)
    )
    # result is list [Point, Point, Line, LineDisplacement]
    ld = result[-1] if isinstance(result, list) else result
    ld_obj = g.__getattr__(ld.Name.value if hasattr(ld.Name, "value") else "LineDisplacement_1")
    if ux_fixed:
        ld_obj.Displacement_x = "Fixed"
    if uy_fixed:
        ld_obj.Displacement_y = "Fixed"
    print("    %s: Ux=%s Uy=%s" % (label, "Fixed" if ux_fixed else "Free",
                                     "Fixed" if uy_fixed else "Free"))

make_linedispl(0, -11, 30, -11, True,  True,  "Bottom (y=-11)")
make_linedispl(0, -11,  0,  3,  True,  False, "Left/Symmetry (x=0)")
make_linedispl(30, -11, 30,  0, True,  False, "Right (x=30)")


# =============================================================================
# STEP 5 – Mesh
# =============================================================================
print("\n[5] Generating mesh ...")
s.call_and_handle_command("gotomesh")
r = s.call_and_handle_command("mesh 0.04")
print("    %s" % r)


# =============================================================================
# STEP 6 – Phases
# =============================================================================
print("\n[6] Setting up calculation phases ...")
s.call_and_handle_command("gotostages")

phases = g.Phases
initial = phases[0]
print("    InitialPhase OK (K0, CalcType=%s)" % initial.DeformCalcType.value)

# Phase_1: Plastic – embankment construction
ph1 = s.call_and_handle_command("phase InitialPhase")
phases = g.Phases
phase1 = phases[1]
phase1.DeformCalcType = "plastic"
phase1.Identification = "Embankment Construction"
print("    Phase_1 created: CalcType=%s" % phase1.DeformCalcType.value)

# Activate embankment soil in Phase_1
try:
    r = s.call_and_handle_command("activate %s Phase_1" % soil_name)
    print("    Activate embankment in Phase_1: %s" % r)
except Exception as e:
    print("    Activation warning: %s" % e)

# Phase_2: Safety – phi/c reduction
ph2 = s.call_and_handle_command("phase Phase_1")
phases = g.Phases
phase2 = phases[2]
phase2.DeformCalcType = "safety"
phase2.Identification = "Safety Analysis - Phi/c Reduction"
print("    Phase_2 created: CalcType=%s" % phase2.DeformCalcType.value)

# Summary
print("\n    Phase summary:")
phases = g.Phases
for i in range(len(phases)):
    ph = phases[i]
    ct = ph.DeformCalcType.value if hasattr(ph.DeformCalcType, "value") else ph.DeformCalcType
    try:
        prev = ph.PreviousPhase.Name.value
    except Exception:
        prev = "(none)"
    print("      [%d] %s  CalcType=%s  prev=%s" % (
        i, ph.Name.value, ct, prev))


# =============================================================================
# STEP 7 – Calculate
# =============================================================================
print("\n[7] Running calculation ...")

def val(prop):
    return prop.value if hasattr(prop, "value") else prop

# Phase_1 solver settings – more steps & iterations for soft clay
phases = g.Phases
phase1 = phases[1]
for attr, v in [("MaxSteps", 500), ("MaxIterations", 60), ("ToleratedError", 0.01)]:
    try:
        setattr(phase1, attr, v)
        print("    Phase_1 %s = %s" % (attr, v))
    except Exception:
        pass  # attribute may not be settable; PLAXIS uses defaults

# Mark all phases
for ph in phases:
    try:
        ph.ShouldCalculate = True
    except Exception:
        pass

t0 = time.time()
try:
    r = s.call_and_handle_command("calculate")
    elapsed = time.time() - t0
    print("    Done in %.1f s" % elapsed)
except Exception as e:
    elapsed = time.time() - t0
    print("    ERROR after %.1f s: %s" % (elapsed, e))

# Result status + LogInfo
CODES = {0: "Not calc", 1: "OK", 2: "OK+warn", 3: "Failed", 4: "Stopped"}
phases = g.Phases
print("\n    Calculation result codes:")
for i in range(len(phases)):
    ph = phases[i]
    cr = val(ph.CalculationResult)
    log = val(ph.LogInfo)
    print("      [%d] %s: %s  (LogInfo=%s)" % (i, val(ph.Name), CODES.get(cr, cr), log))


# =============================================================================
# STEP 7b – If Phase_1 has warnings, still try Phase_2 independently
# =============================================================================
phases = g.Phases
ph1 = phases[1]
ph2 = phases[2]
cr1 = val(ph1.CalculationResult)

if cr1 == 2:   # OK+warnings: Phase_1 applied load, try running Phase_2 anyway
    print("\n[7b] Phase_1 OK+warn - trying Phase_2 independently ...")
    # Mark only Phase_2
    ph1.ShouldCalculate = False
    phases[0].ShouldCalculate = False
    ph2.ShouldCalculate = True
    import time as _time
    t0 = _time.time()
    try:
        r = s.call_and_handle_command("calculate")
        print("    Phase_2 standalone => %s (%.1fs)" % (r, _time.time()-t0))
    except Exception as e:
        print("    Phase_2 error: %s" % str(e)[:200])
    phases = g.Phases
    for i in range(len(phases)):
        ph = phases[i]
        cr = val(ph.CalculationResult)
        print("    [%d] %s : %s" % (i, val(ph.Name), CODES.get(cr, cr)))


# =============================================================================
# STEP 8 – Extract results via Output server
# =============================================================================
print("\n[8] Extracting results ...")

# Launch PLAXIS Output program so its scripting server comes up on port 10001
import subprocess, time as _time2
OUTPUT_EXE = r"C:\Program Files\Bentley\Geotechnical\PLAXIS 2D CONNECT Edition V20\Plaxis2DOutput.exe"
print("    Launching Plaxis2DOutput.exe ...")
try:
    subprocess.Popen([OUTPUT_EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _time2.sleep(8)   # give it time to start and open port 10001
    print("    Waited 8 s for Output to start")
except Exception as e:
    print("    Could not launch Output: %s" % e)

# First try Output server (port 10001)
got_output = False
try:
    s_out, g_out = new_server(HOST, 10001, password=PWD)
    print("    Output connected: %s" % s_out.server_full_name)
    got_output = True
except Exception:
    pass

if got_output:
    phases_out = g_out.Phases
    print("    Output phases: %d" % len(phases_out))

    print("\n    -- Max settlement Uy (Phase_1 Plastic) --")
    try:
        uy_vals = g_out.getresults(phases_out[1], g_out.ResultTypes.Soil.Uy, "node")
        uy_list = list(uy_vals)
        print("      Min Uy (max settlement) = %.4f m = %.1f mm" % (min(uy_list), min(uy_list)*1000))
        print("      Max Uy                  = %.4f m" % max(uy_list))
    except Exception as e:
        print("      Uy error:", e)

    print("\n    -- Factor of Safety (Phase_2 Safety) --")
    try:
        msf_vals = g_out.getresults(phases_out[2], g_out.ResultTypes.Soil.SumMsf, "node")
        msf_list = list(msf_vals)
        print("      FoS (max SumMsf) = %.3f" % max(msf_list))
    except Exception as e:
        print("      SumMsf error:", e)

else:
    # -- Fallback: read Uy/SumMsf via Input tabulate --
    print("    Output server not running. Trying Input tabulate ...")
    phases = g.Phases
    ph1 = phases[1]
    ph2 = phases[2]
    ph1_name = val(ph1.Name)
    ph2_name = val(ph2.Name)

    for cmd in [
        "tabulate %s Uy" % ph1_name,
        "tabulate %s SumMsf" % ph2_name,
        "tabulate %s Uy min" % ph1_name,
    ]:
        try:
            r = s.call_and_handle_command(cmd)
            print("    %s => %s" % (cmd, str(r)[:300]))
        except Exception as e:
            print("    %s => ERROR: %s" % (cmd, str(e)[:80]))

    # -- Try ResultTypes from Input API --
    print("\n    Trying getresults from Input API ...")
    try:
        rt = g.ResultTypes
        print("    ResultTypes available:", type(rt))
        soil_rt = rt.Soil
        for nm in ["Uy", "Utot", "SumMsf", "MStage"]:
            try:
                rv = getattr(soil_rt, nm)
                res = g.getresults(phases[1], rv, "node")
                res_list = list(res)
                print("    Phase_1 %s: min=%.4f max=%.4f" % (nm, min(res_list), max(res_list)))
            except Exception as e2:
                print("    Phase_1 %s: %s" % (nm, str(e2)[:60]))
    except Exception as e:
        print("    ResultTypes not available in Input API: %s" % str(e)[:60])

    print("\n    *** Please open PLAXIS Output from the GUI to view full results ***")
    print("    In PLAXIS 2D: after calculation, click the glasses icon / View menu > Output")
    print("    The Output program connects on port 10001 and has all result types.")

print("\n=== Done ===")
