---
name: plaxis
description: Drive PLAXIS 2D V20 via the MCP server in this repo — connect, build geometry/materials/boreholes, set BCs, mesh, configure phases (K0/Plastic/Safety), calculate, and read results. Use when the user asks anything about PLAXIS, embankments, soft clay, factor of safety, settlement, soil materials, boreholes, staged construction, or any `mcp__plaxis__*` tool. Encodes V20 quirks empirically learned in prior sessions (Eref read-only on cmd-line, Undrained_C + K0 conflict, soillayer thickness sign, `linedispl` vs `linedisplacement`, Safety phase ordinal, results via Output server on port 10001).
---

# PLAXIS 2D workflow skill

This repo wraps the official PLAXIS Python scripting library as an MCP server (`plaxis_mcp_server.py`). PLAXIS itself is a Windows-only geotechnical FEM program; the MCP server talks to a running PLAXIS instance over an encrypted local HTTP server (default port 10000 Input, 10001 Output).

The user's typical workflow is **build a soft-clay-foundation problem (often Bangkok soft clay), construct an embankment, calculate, get max settlement and factor of safety**. Default password observed in prior sessions: `sompote`.

---

## 0. Always do this first

Before any other PLAXIS tool call, call `mcp__plaxis__plaxis_connect`:

```
host=localhost  port=10000  password=<ask user, default "sompote">
```

If the connection fails, the user has not started the scripting server. Tell them:
> Open PLAXIS 2D → **Expert → Configure remote scripting server** → set port `10000` and a password → **Start server**. The PLAXIS title bar should show `*** SERVER ACTIVE on port 10000 (SECURED) ***`.

Then re-call connect.

To check status mid-session: `mcp__plaxis__plaxis_server_status`.

---

## 1. Available MCP tools (this server)

| Tool | Purpose |
|---|---|
| `plaxis_connect` / `plaxis_disconnect` / `plaxis_server_status` | Session management |
| `plaxis_new_project` / `plaxis_open_project` / `plaxis_close_project` | Project lifecycle |
| `plaxis_command` / `plaxis_commands` | Execute one or many raw PLAXIS command-line strings |
| `plaxis_create_soil` | Convenience: create soil material with all params in one call |
| `plaxis_create_borehole` | Convenience: borehole + layered soil profile |
| `plaxis_set_fixities` | Convenience: standard model boundary conditions |
| `plaxis_get_object` / `plaxis_get_property` / `plaxis_set_property` / `plaxis_list_objects` | Object inspection / mutation |
| `plaxis_get_results` | Read tabulated phase results |

**Prefer the convenience tools** (`plaxis_create_soil`, `plaxis_create_borehole`, `plaxis_set_fixities`) over raw `plaxis_command` because they handle V20-specific gotchas (Eref via Gref, drainage-type ordering, `linedispl` not `linedisplacement`).

When a convenience tool isn't enough, fall through to `plaxis_command` / `plaxis_commands`.

---

## 2. Standard problem build order

Follow this sequence for a typical 2D embankment-on-soft-clay problem. The order matters — PLAXIS is modal.

### 2.1 New project → Soil materials

```
plaxis_new_project()
plaxis_create_soil(name="Bangkok_Soft_Clay", drainage_type="Undrained_B",
                   gamma_unsat=15, gamma_sat=16,
                   youngs_modulus=20000, poisson_ratio=0.20,
                   cohesion=20)        # phi defaults; Undrained_B forces phi=0
plaxis_create_soil(name="Medium_Clay", drainage_type="Drained",
                   gamma_unsat=17, gamma_sat=18,
                   youngs_modulus=15000, poisson_ratio=0.30,
                   cohesion=5, friction_angle=26)
plaxis_create_soil(name="Embankment_Fill", drainage_type="Drained",
                   gamma_unsat=19, gamma_sat=20,
                   youngs_modulus=30000, poisson_ratio=0.30,
                   cohesion=1, friction_angle=32, dilatancy_angle=2)
```

### 2.2 Boreholes & soil profile (in Soil mode — default)

**Recommended — use raw commands, not `plaxis_create_borehole` with mismatched borehole calls** (see §4.12 for why):

```
plaxis_command("borehole 0")
plaxis_command("borehole 30")           # second borehole at right model boundary
plaxis_command("set Borehole_1.Head 0")
plaxis_command("set Borehole_2.Head 0")
plaxis_command("soillayer 8")           # only on first borehole — but apply BEFORE setmaterial
plaxis_command("setmaterial Bangkok_Soft_Clay")
plaxis_command("soillayer 5")
plaxis_command("setmaterial Medium_Clay")
# CRITICAL: V20 default polygon is 12 m wide regardless of Borehole_2 position —
# manually extend polygon points to span the full domain (see §4.12)
plaxis_command("movepoint BoreholePolygon_1 1 (30 0)")
plaxis_command("movepoint BoreholePolygon_1 2 (30 -8)")
plaxis_command("movepoint BoreholePolygon_2 1 (30 -8)")
plaxis_command("movepoint BoreholePolygon_2 2 (30 -13)")
# Verify materials propagated correctly:
plaxis_command("echo Soil_1")           # should show Bangkok_Soft_Clay
plaxis_command("echo Soil_2")           # should show Medium_Clay
# If wrong, force-set:
plaxis_command("set Soil_1.Material Bangkok_Soft_Clay")
plaxis_command("set Soil_2.Material Medium_Clay")
```

Borehole y-origin is the surface; layers extend downward. The y-elevations above are `0 → -8 → -13`.

### 2.3 Structures (embankment polygon, loads, plates, etc.)

```
plaxis_command("gotostructures")
plaxis_command("polygon (0 0) (0 3) (3 3) (9 0)")   # half-model, 1V:2H slope, 3 m high
# polygon command returns [Polygon, Soil] — last item is the new Soil_N
plaxis_command("set Soil_5.Material Embankment_Fill")
```

### 2.4 Boundary conditions

**DO NOT use `plaxis_set_fixities` — it has a bug** (see §4.11). Instead, set BCs explicitly:

```
plaxis_command("linedispl (x_min y_min) (x_max y_min)")     # bottom
plaxis_command("linedispl (x_min y_min) (x_min y_max)")     # left
plaxis_command("linedispl (x_max y_min) (x_max y_max)")     # right (use y_max ≤ ground if no soil above)
plaxis_command('set LineDisplacement_1.Displacement_x "Fixed"')
plaxis_command('set LineDisplacement_1.Displacement_y "Fixed"')
plaxis_command('set LineDisplacement_2.Displacement_x "Fixed"')
plaxis_command('set LineDisplacement_2.Displacement_y "Free"')   # CRITICAL — must be explicit
plaxis_command('set LineDisplacement_3.Displacement_x "Fixed"')
plaxis_command('set LineDisplacement_3.Displacement_y "Free"')   # CRITICAL — must be explicit
```

### 2.5 Mesh

```
plaxis_command("gotomesh")
plaxis_command("mesh 0.05")          # coarseness 0.03–0.07; smaller = finer
```

### 2.6 Phases (the tricky part — see §4.5)

```
plaxis_command("gotostages")
# InitialPhase exists by default with DeformCalcType="K0Procedure".
# Create Phase_1 from InitialPhase:
plaxis_command("phase InitialPhase")
plaxis_set_property("Phase_1", "DeformCalcType", "plastic")
plaxis_set_property("Phase_1", "Identification", "Embankment construction")

# Deactivate embankment in InitialPhase, activate in Phase_1
plaxis_command("deactivate Soil_5 InitialPhase")
plaxis_command("activate Soil_5 Phase_1")

# Phase_2 = Safety (phi-c reduction) from Phase_1
plaxis_command("phase Phase_1")
plaxis_set_property("Phase_2", "DeformCalcType", "safety")
plaxis_set_property("Phase_2", "Identification", "Safety analysis")
```

### 2.7 Calculate

```
plaxis_command("calculate")
```

Then check status:
```
plaxis_get_property("Phase_1", "CalculationResult")    # 1=OK, 2=OK+warn, 3=Failed, 4=Stopped
plaxis_get_property("Phase_2", "CalculationResult")
```

### 2.8 Results

See §3.

---

## 3. Reading results

The Input server (port 10000) **can** sometimes return results via `g.getresults(...)`, but the reliable path is the Output server on port 10001.

### Quick path — `tabulate` via Input

```
plaxis_get_results(phase_name="Phase_1", result_type="Uy")        # settlement
plaxis_get_results(phase_name="Phase_2", result_type="SumMsf")    # FoS
```

### Full path — Output server (when above returns nothing)

The Output server doesn't auto-start. Either tell the user to click the **Output** glasses icon in the PLAXIS GUI, **or** drop into a Python script (the repo already has `extract_results.py` and `build_embankment_v2.py` that demonstrate launching `Plaxis2DOutput.exe --AppServerPort=10001 --AppServerPassword=…` then connecting via `new_server(host, 10001, password=…)`).

Key result types (Output `g_out.ResultTypes.Soil.*`):

| Goal | ResultType | Reduce |
|---|---|---|
| Max settlement (downward, mm) | `Uy` | `min(uy_list) * 1000` |
| Total displacement | `Utot` | `max(utot_list)` |
| Factor of safety | `SumMsf` | `max(msf_list)` (last step ≈ FoS) |
| Excess pore pressure | `PExcess` | `min(...)` for max negative |
| Effective stress | `SigmaXX`, `SigmaYY`, `SigmaXY` | as needed |

---

## 4. V20 gotchas — empirically confirmed

These have all bitten prior sessions. Apply preemptively.

### 4.1 `Eref` is read-only via the command line

`set SoilMat.Eref 10000` raises an error. Two workarounds, in order of preference:

1. **Use `Gref` instead** — PLAXIS recomputes Eref:  `Gref = E / (2·(1+ν))`.
2. **Use the Python API** via `plaxis_set_property` (the MCP server's `_best_set` falls back to the Python descriptor automatically). This is what `plaxis_create_soil` already does.

### 4.2 `gammaSat` becomes read-only after `DrainageType = Undrained_C`

So **set unit weights BEFORE drainage type**:

```
set Clay.gammaUnsat 15      ← 1st
set Clay.gammaSat   16      ← 2nd
set Clay.DrainageType 3     ← 3rd (Undrained_C = 3)
```

`plaxis_create_soil` already orders these correctly.

### 4.3 `soillayer` takes thickness, not elevation

```
soillayer 8     ✓ creates an 8 m thick layer downward
soillayer -8    ✗ ERROR (must be positive)
```

Only call `soillayer` for the **first** borehole. Additional boreholes inherit the same layer structure automatically — adding `soillayer` calls to the second borehole creates duplicate layers and breaks the model.

### 4.4 Boundary-condition command is `linedispl`, not `linedisplacement`

```
linedispl (0 -8) (40 -8)                       ← correct
set LineDisplacement_1.Displacement_x "Fixed"  ← Fixed=1, Free=0 (string form is safest)
```

The result of `linedispl` is `[Point, Point, Line, LineDisplacement]`; the LineDisplacement is the last element. Set `Displacement_x`/`Displacement_y` via the Python API on the `LineDisplacement_N` object — the cmd-line form sometimes silently no-ops.

### 4.5 K0 procedure conflicts with Undrained_C materials

The default `InitialPhase.DeformCalcType = "K0Procedure"` cannot coexist with any material set to `Undrained_C`. PLAXIS errors out at calculate time. Two fixes:

```
# Option A — switch InitialPhase to gravity loading
set InitialPhase.DeformCalcType "gravityloading"

# Option B — use Undrained_B (φ=0, c=cu) for soft clays instead of Undrained_C
```

Prior sessions for Bangkok soft clay (cu = 20 kPa) used **Undrained_B**, which works with K0 procedure and is the recommended choice.

### 4.6 Safety phase requires `DeformCalcType = "safety"` (string), not an integer

Integer values (5, 6, 7) sometimes silently set the wrong type or change between PLAXIS versions. Always pass the string:

```
plaxis_set_property("Phase_2", "DeformCalcType", "safety")
```

Verify with `plaxis_get_property("Phase_2", "DeformCalcType")` — it should echo back `safety`.

### 4.7 `polygon` returns `[Polygon, Soil]`

When you create the embankment polygon, the auto-named soil is the **last** element of the result list. Capture its name (typically `Soil_5` after one borehole with two layers, since boreholes also create soil objects) before assigning material:

```
result = plaxis_command("polygon (0 0) (0 3) (3 3) (9 0)")
# result["result"] is a list; the last item is the Soil
# Then: plaxis_command("set Soil_5.Material Embankment_Fill")
```

If unsure of the auto-name, call `plaxis_list_objects("Soils")` to find it.

### 4.8 Mesh is invalidated by structural changes

Going back to `gotostructures` after meshing wipes the mesh. Always finish all geometry / BCs first, then `gotomesh` once. If the user changes geometry, re-mesh.

### 4.9 `ShouldCalculate` must be true on every phase you want calculated

`calculate` only runs phases with `ShouldCalculate = True`. By default new phases are flagged true, but prior sessions hit cases where Phase_2 was skipped because it was flagged false. To be safe before `calculate`:

```
for ph_name in ["InitialPhase", "Phase_1", "Phase_2"]:
    plaxis_set_property(ph_name, "ShouldCalculate", "True")
```

### 4.10 Python 3.12+ needs the `distutils` shim

The MCP server already injects this at startup. If running standalone Python scripts that import `plxscripting`, prepend the shim from `plaxis_mcp_server.py` (lines 21–34) or stdout will hit `ModuleNotFoundError: distutils`.

### 4.11 `plaxis_set_fixities` MCP tool over-constrains lateral BCs (BUG)

The `plaxis_set_fixities` convenience tool calls `linedispl` then only conditionally sets `Displacement_y`. In V20, `Displacement_y` defaults to `"Fixed"`. Result: the left and right boundaries end up Ux=Fixed AND Uy=Fixed — over-constrained. Soft clay can't settle vertically at the lateral boundary, causing artificial stress concentrations and "Soil body collapses" failures during embankment loading.

**Always set `Displacement_y` explicitly to `"Free"` on lateral BCs** — see §2.4 for the working pattern. Don't use `plaxis_set_fixities` until the MCP server bug is fixed.

Diagnostic: if Phase_1 fails with LogInfo "Soil body seems to collapse" at SumMstage ≈ 0.4, with embankment loads that hand-calcs say should be stable, this is almost certainly the cause.

### 4.12 Second borehole without layers does NOT extend the soil polygon (V20 BUG)

In V20, when you create Borehole_1 (with `soillayer` commands), then add Borehole_2 at a different x without any `soillayer` commands of its own, **the GeneratedSoilPolygon stays at a default 12 m wide** (around Borehole_1) — it does NOT extend to Borehole_2. The boreholes have correct per-borehole layer thicknesses (echo BVLayerZone_N confirms), but the visible soil mass is just a 12 m × layer_depth block. Symptoms: lateral BCs at x=80 are floating in empty space; embankment "Soil body collapses" because there's no soil under most of the model.

**Workaround — move polygon points manually after both boreholes are placed:**

```
# After both boreholes + soillayer commands:
plaxis_command("movepoint BoreholePolygon_1 1 (X_RIGHT 0)")           # top-right of layer 1
plaxis_command("movepoint BoreholePolygon_1 2 (X_RIGHT -L1_BOTTOM)")  # bottom-right of layer 1
plaxis_command("movepoint BoreholePolygon_2 1 (X_RIGHT -L1_BOTTOM)")  # top-right of layer 2
plaxis_command("movepoint BoreholePolygon_2 2 (X_RIGHT -PROFILE_BOT)") # bottom-right of layer 2
# Repeat per layer; point indices 1, 2 are the right-side corners (top-right, bottom-right).
```

Then verify with `echo BoreholePolygon_1` — Points should now span x=0 to x=X_RIGHT.

Also verify materials: in V20, `setmaterial X` after `soillayer N` applies to the *most recently created soil cluster*, but **the FINAL `setmaterial` call ends up overwriting all previous layer materials** in some configurations — so you may end up with all layers having the LAST material assigned. Always check with `echo Soil_1` / `echo Soil_2` after layer creation, and explicitly fix with `set Soil_N.Material X` if needed.

### 4.13 Mesh coarseness must match the smallest feature

Coarseness 0.05–0.07 is fine for compact models (≤30 m wide). For wider models (50–80 m) with a small embankment (under 10 m wide), use 0.03–0.04 — otherwise the embankment is resolved with only 1–2 elements and PLAXIS can't capture its stress field, leading to spurious "soil body collapses" reports.

---

## 5. Drainage type encoding

When using raw `set` or `plaxis_set_property`, PLAXIS expects integers:

| String | Int | Notes |
|---|---|---|
| `Drained` | 0 | Granular soils, long-term |
| `Undrained_A` | 1 | Effective stress params (c′, φ′) |
| `Undrained_B` | 2 | Effective stiffness, undrained strength (cu = c, φ=0) — **use for Bangkok soft clay** |
| `Undrained_C` | 3 | Total stress params; **conflicts with K0 procedure** (see §4.5) |
| `NonPorous` | 4 | Concrete, fill above water table when no pore-water analysis needed |

`plaxis_create_soil` accepts the string form and maps it.

---

## 6. Half-model symmetry pattern (common with embankments)

For a symmetric embankment, build only the right half: x = 0 to model_width/2, with the symmetry axis at x = 0. Apply Ux=Fixed (roller) on the left edge — this is what `plaxis_set_fixities` does. Halves the mesh, doubles the speed.

Example domain for the canonical Bangkok problem: `x = 0 → 30 m`, `y = -11 → +3 m`, embankment polygon `(0,0)→(0,3)→(3,3)→(9,0)` (3 m high, 6 m crest from the full-model perspective, 1V:2H slope).

---

## 7. When the user shows a screenshot saying "geometry is wrong"

Common causes from prior sessions:
1. **Embankment hovering above soil surface** — the polygon's bottom edge isn't at y=0. Check the polygon coordinates: bottom edge must match the borehole top y (usually 0).
2. **Slope direction reversed** — vertices in wrong order; PLAXIS doesn't enforce CCW. Re-list as `(0,0)→(0,h)→(crest_x,h)→(toe_x,0)`.
3. **Borehole at wrong x** — boreholes only define soil between them; if the embankment extends past the rightmost borehole, that area has no soil.

Always **verify visually** by asking the user to confirm or by reading back `Points`/`Polygons` via `plaxis_list_objects`.

---

## 8. Reference files in this repo

When the user asks for a complete script (not interactive MCP work), point them at or adapt:

- `build_embankment_v2.py` — full Bangkok embankment build, calc, and results extraction (most complete example)
- `full_setup_and_run.py` — phase setup + mesh + calculate
- `extract_results.py` — Output-server result extraction with fallbacks
- `find_safety.py` — debugging which DeformCalcType integer maps to Safety
- `setup_phases.py` — phase creation from scratch
- `explore_bcs.py` — discovering the `linedispl` command + `LineDispls` collection

These are user scripts, not part of the MCP server. The MCP server itself is `plaxis_mcp_server.py`.

---

## 9. Hard rules

- **Never invent a property name.** If unsure, call `plaxis_get_object` on the parent and look at the `attributes` list before `set`-ing.
- **Never skip the connection check.** Every tool except connect requires it.
- **Never use raw `set Object.Eref ...`** — it will silently fail or error. Use `Gref` or `plaxis_set_property` (which falls back to the Python API).
- **Never call `soillayer` on the second+ borehole.**
- **When the user says "calculate" but the phase setup looks wrong, raise it before running** — calculation is slow and a wrong-phase setup wastes minutes.
