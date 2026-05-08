"""
PLAXIS MCP Server - Connect Claude to PLAXIS via the Model Context Protocol.

This server wraps the plxscripting library to expose PLAXIS operations
as MCP tools that Claude can call directly.
"""

import sys
import os
import json
import logging
from typing import Optional

# Add plxscripting to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plxscripting", "src"))

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

# Global state for the PLAXIS connection
_state = {
    "server": None,
    "global": None,
    "connected": False,
}


def _require_connection():
    """Raise an error if not connected to PLAXIS."""
    if not _state["connected"]:
        raise RuntimeError(
            "Not connected to PLAXIS. Call 'plaxis_connect' first "
            "with the correct host, port, and password."
        )
    return _state["server"], _state["global"]


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
    from plxscripting.server import new_server
    from plxscripting.plxproxyfactory import PlxProxyFactory
    from plxscripting.connection import HTTPConnection
    from plxscripting.server import InputProcessor, Server
    from plxscripting.image import TYPE_NAME_IMAGE, create_image
    from plxscripting.error_mode import ErrorMode

    try:
        error_mode = ErrorMode()
        conn = HTTPConnection(host, port, timeout, None, password, error_mode=error_mode)
        pf = PlxProxyFactory(conn)
        ip = InputProcessor()
        s = Server(conn, pf, ip)
        s.result_handler.register_json_constructor(TYPE_NAME_IMAGE, create_image)

        _state["server"] = s
        _state["global"] = s.plx_global
        _state["connected"] = True

        server_name = "Unknown"
        try:
            server_name = s.server_full_name
        except Exception:
            pass

        return json.dumps({
            "status": "connected",
            "server": server_name,
            "host": host,
            "port": port,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_disconnect() -> str:
    """Disconnect from the PLAXIS server."""
    _state["server"] = None
    _state["global"] = None
    _state["connected"] = False
    return json.dumps({"status": "disconnected"})


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
            results.append({"command": cmd, "status": "success", "result": _serialize_result(result)})
        except Exception as e:
            results.append({"command": cmd, "status": "error", "message": str(e)})
            break
    return json.dumps(results)


@mcp.tool()
def plaxis_new_project() -> str:
    """Create a new PLAXIS project."""
    s, g = _require_connection()
    try:
        result = s.new()
        return json.dumps({"status": "success", "result": str(result)})
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
        result = s.open(filepath)
        return json.dumps({"status": "success", "result": str(result)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_close_project() -> str:
    """Close the current PLAXIS project."""
    s, g = _require_connection()
    try:
        result = s.close()
        return json.dumps({"status": "success", "result": str(result)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


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
        info = {"name": name, "type": str(type(obj).__name__)}

        # If listable, get count
        try:
            length = len(obj)
            info["count"] = length
            if length > 0 and length <= 20:
                items = []
                for i in range(length):
                    item = obj[i]
                    items.append(_describe_proxy(item))
                info["items"] = items
        except (TypeError, AttributeError):
            pass

        # Get attributes
        try:
            attrs = s.get_object_attributes(obj)
            prop_names = list(attrs.keys())
            info["attributes"] = prop_names[:50]
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

        # If it's a proxy property, get the value
        value = prop
        try:
            value = prop.value
        except AttributeError:
            pass

        return json.dumps({
            "status": "success",
            "object": object_name,
            "property": property_name,
            "value": _serialize_result(value),
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_set_property(object_name: str, property_name: str, value: str) -> str:
    """Set a property value on a PLAXIS object.

    Args:
        object_name: Name of the object (e.g., "Point_1", "SoilMat_1")
        property_name: Name of the property to set
        value: New value (will be passed as a PLAXIS command: "set Object.Property value")
    """
    s, g = _require_connection()
    try:
        cmd = f"set {object_name}.{property_name} {value}"
        result = s.call_and_handle_command(cmd)
        return json.dumps({"status": "success", "result": _serialize_result(result)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_list_objects(object_type: str) -> str:
    """List all objects of a given type in the current project.

    Args:
        object_type: Type group name, e.g. "Points", "Lines", "Polygons",
                     "Soils", "Phases", "Boreholes", "FixedEndAnchors",
                     "Plates", "Geogrids", "EmbeddedBeams"
    """
    s, g = _require_connection()
    try:
        collection = g.__getattr__(object_type)
        items = []
        try:
            length = len(collection)
            for i in range(min(length, 100)):
                item = collection[i]
                items.append(_describe_proxy(item))
        except (TypeError, AttributeError):
            items.append(str(collection))

        return json.dumps({
            "status": "success",
            "type": object_type,
            "count": len(items),
            "items": items,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


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
) -> str:
    """Create a soil material with common parameters.

    For advanced material models or parameters, use plaxis_command with
    individual 'set' commands after creation.

    Args:
        name: Material name
        material_model: Model type (e.g., "MohrCoulomb", "HardeningSoil", "Linear")
        drainage_type: "Drained", "Undrained_A", "Undrained_B", "Undrained_C", "NonPorous"
        gamma_unsat: Unsaturated unit weight (kN/m3)
        gamma_sat: Saturated unit weight (kN/m3)
        youngs_modulus: Young's modulus E (kN/m2) - for Mohr-Coulomb
        poisson_ratio: Poisson's ratio
        cohesion: Cohesion c (kN/m2)
        friction_angle: Friction angle phi (degrees)
    """
    s, g = _require_connection()
    results = []
    try:
        # Create the material
        r = s.call_and_handle_command(f"soilmat {name}")
        results.append(f"Created material: {_serialize_result(r)}")

        # Set basic parameters via commands
        cmds = [
            f'set {name}.SoilModel "{material_model}"',
            f'set {name}.DrainageType "{drainage_type}"',
            f"set {name}.gammaUnsat {gamma_unsat}",
            f"set {name}.gammaSat {gamma_sat}",
        ]
        if youngs_modulus is not None:
            cmds.append(f"set {name}.Eref {youngs_modulus}")
        if poisson_ratio is not None:
            cmds.append(f"set {name}.nu {poisson_ratio}")
        if cohesion is not None:
            cmds.append(f"set {name}.cref {cohesion}")
        if friction_angle is not None:
            cmds.append(f"set {name}.phi {friction_angle}")

        for cmd in cmds:
            try:
                s.call_and_handle_command(cmd)
                results.append(f"OK: {cmd}")
            except Exception as e:
                results.append(f"WARN: {cmd} -> {e}")

        return json.dumps({"status": "success", "details": results})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "details": results})


@mcp.tool()
def plaxis_create_borehole(
    x: float = 0.0,
    layers: Optional[list[dict]] = None,
) -> str:
    """Create a borehole with soil layers.

    Args:
        x: X coordinate for the borehole (2D) or (x,y) position
        layers: List of layer dicts with keys: "top" (top level), "material" (soil name).
                Example: [{"top": 0, "material": "Clay"}, {"top": -5, "material": "Sand"}]
                The bottom of the model is defined by the lowest layer's top minus some depth.
    """
    s, g = _require_connection()
    results = []
    try:
        r = s.call_and_handle_command(f"borehole {x}")
        results.append(f"Created borehole: {_serialize_result(r)}")

        if layers:
            for layer in layers:
                top = layer.get("top", 0)
                material = layer.get("material", "")
                try:
                    s.call_and_handle_command(f"soillayer {top}")
                    results.append(f"Added layer at {top}")
                except Exception as e:
                    results.append(f"Layer at {top}: {e}")

                if material:
                    try:
                        s.call_and_handle_command(f"setmaterial {material}")
                        results.append(f"Set material: {material}")
                    except Exception as e:
                        results.append(f"Set material {material}: {e}")

        return json.dumps({"status": "success", "details": results})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "details": results})


@mcp.tool()
def plaxis_get_results(
    phase_name: str,
    result_type: str,
    object_name: Optional[str] = None,
) -> str:
    """Get calculation results for a phase.

    This uses the PLAXIS command to retrieve results. For complex result
    queries, use plaxis_command directly with the appropriate tabulate command.

    Args:
        phase_name: Phase name (e.g., "Phase_1", "InitialPhase")
        result_type: Type of result (e.g., "Utot", "SigmaXX", "PExcess")
        object_name: Optional specific object to get results for
    """
    s, g = _require_connection()
    try:
        if object_name:
            cmd = f"tabulate {phase_name} {object_name} {result_type}"
        else:
            cmd = f"tabulate {phase_name} {result_type}"
        result = s.call_and_handle_command(cmd)
        return json.dumps({"status": "success", "result": _serialize_result(result)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def plaxis_server_status() -> str:
    """Check the current connection status to PLAXIS."""
    if not _state["connected"]:
        return json.dumps({"status": "disconnected"})

    s = _state["server"]
    info = {"status": "connected"}
    try:
        info["active"] = s.active
        info["server_name"] = s.server_full_name
    except Exception as e:
        info["active"] = False
        info["error"] = str(e)

    return json.dumps(info)


# --- Helpers ---

def _serialize_result(result):
    """Convert a PLAXIS result to a JSON-serializable form."""
    if result is None:
        return None
    if isinstance(result, (bool, int, float, str)):
        return result
    if isinstance(result, (list, tuple)):
        return [_serialize_result(r) for r in result]
    # Proxy objects
    return _describe_proxy(result)


def _describe_proxy(obj):
    """Describe a PLAXIS proxy object as a dict."""
    info = {"repr": repr(obj)}
    try:
        info["type"] = obj._plx_type
    except AttributeError:
        pass
    try:
        info["guid"] = obj._guid
    except AttributeError:
        pass
    try:
        name = obj.Name
        info["name"] = name.value if hasattr(name, "value") else str(name)
    except (AttributeError, Exception):
        pass
    return info


if __name__ == "__main__":
    mcp.run()
