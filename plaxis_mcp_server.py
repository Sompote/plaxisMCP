"""
PLAXIS MCP Server - Connect Claude to PLAXIS via the Model Context Protocol.

Revised to use the official PLAXIS scripting library shipped with
PLAXIS 2D CONNECT Edition V20 and to set material properties via the
Python API (not the command-line 'set' command) so that read-only
command-line properties like Eref are handled correctly.
"""

import sys
import os
import json
import logging
from typing import Optional

# ── Library paths ────────────────────────────────────────────────────────────
# Prefer the official library that ships with PLAXIS; fall back to the
# bundled copy in the project if the official one is not present.
_OFFICIAL = (
    r"C:\Program Files\Bentley\Geotechnical"
    r"\PLAXIS 2D CONNECT Edition V20\python\Lib\site-packages"
)
_BUNDLED = os.path.join(os.path.dirname(__file__), "plxscripting", "src")

for _p in [_OFFICIAL, _BUNDLED]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "plaxis",
    instructions=(
        "PLAXIS geotechnical FEM software server. "
        "Use 'plaxis_connect' first to establish a connection, then use other tools. "
        "Commands follow PLAXIS command line syntax (e.g. 'line 0 0 10 0', 'point 5 5')."
    ),
)

logger = logging.getLogger("plaxis-mcp")

# ── Global connection state ───────────────────────────────────────────────────
_state: dict = {"server": None, "global": None, "connected": False}


def _require_connection():
    if not _state["connected"]:
        raise RuntimeError(
            "Not connected to PLAXIS. Call 'plaxis_connect' first "
            "with the correct host, port, and password."
        )
    return _state["server"], _state["global"]


# ── Drainage type mapping (string → int) ─────────────────────────────────────
_DRAINAGE = {
    "drained": 0, "0": 0,
    "undrained_a": 1, "undrained a": 1, "undraineda": 1, "1": 1,
    "undrained_b": 2, "undrained b": 2, "undrainedd": 2, "2": 2,
    "undrained_c": 3, "undrained c": 3, "undrainedcc": 3, "3": 3,
    "nonporous": 4, "non-porous": 4, "4": 4,
}


def _drainage_int(dtype: str) -> int:
    return _DRAINAGE.get(dtype.lower().strip(), 0)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _serialize_result(result):
    if result is None:
        return None
    if isinstance(result, (bool, int, float, str)):
        return result
    if isinstance(result, (list, tuple)):
        return [_serialize_result(r) for r in result]
    return _describe_proxy(result)


def _describe_proxy(obj):
    info = {"repr": repr(obj)}
    for attr in ("_plx_type", "_guid"):
        try:
            info[attr.lstrip("_")] = getattr(obj, attr)
        except AttributeError:
            pass
    try:
        n = obj.Name
        info["name"] = n.value if hasattr(n, "value") else str(n)
    except Exception:
        pass
    return info


def _py_set(obj, prop: str, value):
    """
    Set a property on a PLAXIS proxy object via the Python API descriptor
    mechanism.  This bypasses command-line read-only restrictions (e.g. Eref).
    Converts the value to float when possible.
    """
    try:
        numeric = float(value)
        setattr(obj, prop, numeric)
        return True, f"Set via Python API: {prop} = {numeric}"
    except (TypeError, ValueError):
        setattr(obj, prop, value)
        return True, f"Set via Python API: {prop} = {value}"


def _cmd_set(s, obj_name: str, prop: str, value):
    """Set via PLAXIS command line 'set Object.Prop value'."""
    cmd = f"set {obj_name}.{prop} {value}"
    s.call_and_handle_command(cmd)
    return True, f"OK: {cmd}"


def _best_set(s, g, obj_name: str, prop: str, value):
    """
    Try command-line set first; fall back to Python API if blocked
    (command-line read-only properties like Eref).
    """
    try:
        return _cmd_set(s, obj_name, prop, value)
    except Exception as cmd_err:
        try:
            obj = g.__getattr__(obj_name)
            return _py_set(obj, prop, value)
        except Exception as api_err:
            raise RuntimeError(
                f"cmd error: {cmd_err} | api error: {api_err}"
            ) from api_err


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_connect(
    host: str = "localhost",
    port: int = 10000,
    password: str = "",
    timeout: float = 5.0,
) -> str:
    """Connect to a running PLAXIS application.

    PLAXIS must already be running with the scripting server enabled.
    Default ports: Input=10000, Output=10001, SoilTest=10002.

    Args:
        host: PLAXIS server hostname (default: localhost)
        port: PLAXIS server port (default: 10000 for Input)
        password: Server password (shown in PLAXIS scripting server dialog)
        timeout: Connection timeout in seconds
    """
    try:
        from plxscripting.easy import new_server
        s, g = new_server(host, port, timeout=timeout, password=password)
        _state["server"] = s
        _state["global"] = g
        _state["connected"] = True
        server_name = "Unknown"
        try:
            server_name = s.server_full_name
        except Exception:
            pass
        return json.dumps({"status": "connected", "server": server_name,
                           "host": host, "port": port})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_disconnect() -> str:
    """Disconnect from the PLAXIS server."""
    _state.update({"server": None, "global": None, "connected": False})
    return json.dumps({"status": "disconnected"})


@mcp.tool()
def plaxis_server_status() -> str:
    """Check the current connection status to PLAXIS."""
    if not _state["connected"]:
        return json.dumps({"status": "disconnected"})
    s = _state["server"]
    info: dict = {"status": "connected"}
    try:
        info["active"] = s.active
        info["server_name"] = s.server_full_name
    except Exception as e:
        info["active"] = False
        info["error"] = str(e)
    return json.dumps(info)


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_new_project() -> str:
    """Create a new PLAXIS project."""
    s, g = _require_connection()
    try:
        s.call_and_handle_command("new")
        return json.dumps({"status": "success", "result": "OK"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_open_project(filepath: str) -> str:
    """Open an existing PLAXIS project file.

    Args:
        filepath: Full path to the .p2dx / .p3d PLAXIS project file
    """
    s, g = _require_connection()
    try:
        s.open(filepath)
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_close_project() -> str:
    """Close the current PLAXIS project."""
    s, g = _require_connection()
    try:
        s.close()
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_command(command: str) -> str:
    """Execute a PLAXIS command line string.

    This is the most versatile tool - it accepts any valid PLAXIS command.

    Examples:
        - "line 0 0 10 0" (create a line from (0,0) to (10,0))
        - "point 5 5" (create a point at (5,5))
        - "gotomesh" (switch to mesh mode)
        - "mesh 0.05" (generate mesh with coarseness 0.05)
        - "gotostructures" (switch to structures mode)
        - "gotostages" (switch to staged construction)
        - "calculate" (start calculation)
        - "undo" / "redo"
        - "set Line_1.Material SoilMat_1"
        - "tabulate Phase_1 ResultType ..."

    Args:
        command: A valid PLAXIS command line string
    """
    s, g = _require_connection()
    try:
        result = s.call_and_handle_command(command)
        return json.dumps({"status": "success", "result": _serialize_result(result)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_commands(commands: list[str]) -> str:
    """Execute multiple PLAXIS commands in sequence.

    Args:
        commands: List of PLAXIS command strings to execute in order
    """
    s, g = _require_connection()
    results = []
    for cmd in commands:
        try:
            result = s.call_and_handle_command(cmd)
            results.append({"command": cmd, "status": "success",
                            "result": _serialize_result(result)})
        except Exception as e:
            results.append({"command": cmd, "status": "error", "message": str(e)})
            break
    return json.dumps(results)


# ═══════════════════════════════════════════════════════════════════════════════
# OBJECT INSPECTION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_get_object(name: str) -> str:
    """Get a PLAXIS named object and its properties.

    Use this to inspect objects like Points, Lines, Phases, Soils, etc.

    Args:
        name: The PLAXIS object name (e.g., "Point_1", "Line_1", "Phase_1",
              "Points", "Lines", "Soils", "Phases")
    """
    s, g = _require_connection()
    try:
        obj = g.__getattr__(name)
        info: dict = {"name": name, "type": str(type(obj).__name__)}
        try:
            length = len(obj)
            info["count"] = length
            if 0 < length <= 20:
                info["items"] = [_describe_proxy(obj[i]) for i in range(length)]
        except (TypeError, AttributeError):
            pass
        try:
            attrs = s.get_object_attributes(obj)
            info["attributes"] = list(attrs.keys())[:60]
        except Exception:
            pass
        return json.dumps({"status": "success", "object": info})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_get_property(object_name: str, property_name: str) -> str:
    """Get a specific property value from a PLAXIS object.

    Args:
        object_name: Name of the object (e.g., "Point_1", "Line_1")
        property_name: Name of the property (e.g., "x", "y", "Material", "Name")
    """
    s, g = _require_connection()
    try:
        obj = g.__getattr__(object_name)
        prop = getattr(obj, property_name)
        value = prop.value if hasattr(prop, "value") else prop
        return json.dumps({"status": "success", "object": object_name,
                           "property": property_name, "value": _serialize_result(value)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_set_property(object_name: str, property_name: str, value: str) -> str:
    """Set a property value on a PLAXIS object.

    Uses the Python API attribute assignment which works for all properties
    including those read-only via the command-line 'set' command (e.g. Eref).
    Falls back to the command-line 'set' if needed.

    Args:
        object_name: Name of the object (e.g., "Point_1", "SoilMat_1")
        property_name: Name of the property to set
        value: New value
    """
    s, g = _require_connection()
    try:
        ok, msg = _best_set(s, g, object_name, property_name, value)
        return json.dumps({"status": "success", "result": msg})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_list_objects(object_type: str) -> str:
    """List all objects of a given type in the current project.

    Args:
        object_type: Type group name, e.g. "Points", "Lines", "Polygons",
                     "Soils", "Phases", "Boreholes", "FixedEndAnchors",
                     "Plates", "Geogrids", "EmbeddedBeams", "Materials"
    """
    s, g = _require_connection()
    try:
        collection = g.__getattr__(object_type)
        items = []
        try:
            length = len(collection)
            for i in range(min(length, 100)):
                items.append(_describe_proxy(collection[i]))
        except (TypeError, AttributeError):
            items.append(str(collection))
        return json.dumps({"status": "success", "type": object_type,
                           "count": len(items), "items": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIAL TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_create_soil(
    name: str,
    material_model: str = "MohrCoulomb",
    drainage_type: str = "Drained",
    gamma_unsat: float = 16.0,
    gamma_sat: float = 20.0,
    youngs_modulus: Optional[float] = None,
    poisson_ratio: Optional[float] = None,
    cohesion: Optional[float] = None,
    friction_angle: Optional[float] = None,
    dilatancy_angle: float = 0.0,
) -> str:
    """Create a soil material and set its parameters.

    Properties are set via the Python API (not the command-line 'set' command)
    so that Eref and other command-line read-only properties are handled.
    Eref is set indirectly via Gref = E / (2*(1+nu)) since Gref is writable.

    Args:
        name: Material name
        material_model: "MohrCoulomb" | "HardeningSoil" | "LinearElastic" | etc.
        drainage_type: "Drained" | "Undrained_A" | "Undrained_B" | "Undrained_C" | "NonPorous"
        gamma_unsat: Unsaturated unit weight (kN/m³)
        gamma_sat: Saturated unit weight (kN/m³)
        youngs_modulus: Young's modulus E (kN/m²)
        poisson_ratio: Poisson's ratio ν
        cohesion: Cohesion c_ref (kN/m²)
        friction_angle: Friction angle φ (degrees)
        dilatancy_angle: Dilatancy angle ψ (degrees, default 0)
    """
    s, g = _require_connection()
    log: list[str] = []
    try:
        # 1. Create material (auto-named SoilMat_N)
        mat_proxy = s.call_and_handle_command("soilmat")
        auto_name = _describe_proxy(mat_proxy).get("name", "SoilMat_1")
        log.append(f"Created: {auto_name}")

        # 2. Rename
        s.call_and_handle_command(f'set {auto_name}.Name "{name}"')
        log.append(f"Renamed to: {name}")

        # Helper: set via Python API using the new name
        def _set(prop, val):
            ok, msg = _best_set(s, g, name, prop, val)
            log.append(msg)

        # 3. Soil model and drainage (command-line friendly)
        _set("SoilModel", f'"{material_model}"')
        _set("DrainageType", _drainage_int(drainage_type))

        # 4. Unit weights
        _set("gammaUnsat", gamma_unsat)
        _set("gammaSat", gamma_sat)

        # 5. Stiffness: set Gref = E/(2(1+ν)) because Eref is cmd-read-only
        nu = poisson_ratio if poisson_ratio is not None else 0.3
        if youngs_modulus is not None:
            gref = youngs_modulus / (2.0 * (1.0 + nu))
            _set("Gref", round(gref, 4))
            log.append(f"  → Eref ≈ {youngs_modulus} kN/m² via Gref={round(gref,4)}")

        # 6. Poisson's ratio
        if poisson_ratio is not None:
            _set("nu", poisson_ratio)

        # 7. Strength parameters
        if cohesion is not None:
            _set("cref", cohesion)
        if friction_angle is not None:
            _set("phi", friction_angle)
        _set("psi", dilatancy_angle)

        return json.dumps({"status": "success", "name": name, "log": log})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "log": log})


# ═══════════════════════════════════════════════════════════════════════════════
# GEOMETRY TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_create_borehole(
    x: float = 0.0,
    layers: Optional[list[dict]] = None,
    water_head: float = 0.0,
) -> str:
    """Create a borehole with soil layers.

    Args:
        x: X coordinate of the borehole
        layers: List of layer dicts with keys:
                  "thickness" – layer thickness in metres (required)
                  "material"  – soil material name (optional)
                Example: [{"thickness": 5, "material": "Clay"},
                          {"thickness": 3, "material": "Sand"}]
        water_head: Phreatic level / water table elevation (default 0.0)
    """
    s, g = _require_connection()
    log: list[str] = []
    try:
        bh = s.call_and_handle_command(f"borehole {x}")
        bh_name = _describe_proxy(bh).get("name", f"Borehole_{x}")
        log.append(f"Created: {bh_name}")

        # Set water table
        s.call_and_handle_command(f"set {bh_name}.Head {water_head}")
        log.append(f"Head = {water_head}")

        if layers:
            for layer in layers:
                thickness = layer.get("thickness", 0)
                material = layer.get("material", "")
                if thickness <= 0:
                    log.append(f"Skipped layer with thickness={thickness}")
                    continue
                try:
                    s.call_and_handle_command(f"soillayer {thickness}")
                    log.append(f"Layer thickness={thickness}")
                except Exception as e:
                    log.append(f"Layer error: {e}")
                if material:
                    try:
                        s.call_and_handle_command(f"setmaterial {material}")
                        log.append(f"  material={material}")
                    except Exception as e:
                        log.append(f"  material error: {e}")

        return json.dumps({"status": "success", "borehole": bh_name, "log": log})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "log": log})


@mcp.tool()
def plaxis_set_fixities(
    x_min: float = 0.0,
    x_max: float = 40.0,
    y_min: float = -8.0,
    y_max: float = 0.0,
) -> str:
    """Apply standard boundary conditions to the model.

    Applies:
        - Bottom boundary (y=y_min): fully fixed (Ux=0, Uy=0)
        - Left boundary  (x=x_min): horizontally fixed (Ux=0, Uy free)
        - Right boundary (x=x_max): horizontally fixed (Ux=0, Uy free)
        - Top boundary   (y=y_max): free

    Uses PLAXIS 'linedisplacement' commands in Structures mode.

    Args:
        x_min, x_max: Horizontal model extent
        y_min, y_max: Vertical model extent
    """
    s, g = _require_connection()
    log: list[str] = []
    try:
        s.call_and_handle_command("gotostructures")
        log.append("Switched to Structures mode")

        def _line_fix(x1, y1, x2, y2, label, ux_fixed, uy_fixed):
            ux = "Fixed" if ux_fixed else "Free"
            uy = "Fixed" if uy_fixed else "Free"
            try:
                cmd = f"linedisplacement ({x1} {y1}) ({x2} {y2})"
                res = s.call_and_handle_command(cmd)
                ld_name = _describe_proxy(res).get("name", "LineDisplacement")
                s.call_and_handle_command(f"set {ld_name}.Displacement_x {ux}")
                s.call_and_handle_command(f"set {ld_name}.Displacement_y {uy}")
                log.append(f"{label}: Ux={ux}, Uy={uy}")
            except Exception as e:
                log.append(f"{label} error: {e}")

        _line_fix(x_min, y_min, x_max, y_min, "Bottom", True, True)   # fully fixed
        _line_fix(x_min, y_min, x_min, y_max, "Left",   True, False)  # roller
        _line_fix(x_max, y_min, x_max, y_max, "Right",  True, False)  # roller

        return json.dumps({"status": "success", "log": log})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "log": log})


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS TOOL
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def plaxis_get_results(
    phase_name: str,
    result_type: str,
    object_name: Optional[str] = None,
) -> str:
    """Get calculation results for a phase.

    Args:
        phase_name: Phase name (e.g., "Phase_1", "InitialPhase")
        result_type: Type of result (e.g., "Utot", "SigmaXX", "PExcess", "MStage")
        object_name: Optional specific object to get results for
    """
    s, g = _require_connection()
    try:
        parts = [phase_name]
        if object_name:
            parts.append(object_name)
        parts.append(result_type)
        cmd = "tabulate " + " ".join(parts)
        result = s.call_and_handle_command(cmd)
        return json.dumps({"status": "success", "result": _serialize_result(result)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    mcp.run()
