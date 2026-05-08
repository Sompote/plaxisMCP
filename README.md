# PLAXIS MCP Server

Connect Claude to PLAXIS geotechnical FEM software via the Model Context Protocol (MCP). This allows Claude to directly create geometry, assign materials, generate meshes, run calculations, and extract results from PLAXIS 2D/3D.

## Prerequisites

- **PLAXIS 2D or 3D** installed and running with the scripting server enabled
- **Python 3.9+**
- **Claude Code** CLI

## Installation

### 1. Install Python dependencies

```bash
cd /Users/sompoteyouwai/env/plaxis_MCP
pip install mcp pycryptodome requests psutil
```

### 2. Install plxscripting

```bash
pip install -e plxscripting/
```

### 3. Enable the MCP server in Claude Code

There are three ways to configure the MCP server depending on your needs:

#### Option A: Project-level (recommended)

The `.mcp.json` file in this directory is already configured. When you start Claude Code from this directory, it will automatically detect the PLAXIS MCP server. No extra setup needed.

To use it from another project, copy `.mcp.json` to that project's root directory.

#### Option B: Global via `claude mcp add` command

This registers the server globally so it is available in all projects:

```bash
claude mcp add plaxis \
  -e PYTHONPATH=/Users/sompoteyouwai/env/plaxis_MCP/plxscripting/src \
  -- /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
  /Users/sompoteyouwai/env/plaxis_MCP/plaxis_mcp_server.py
```

You can verify it was added:

```bash
claude mcp list
```

To remove it later:

```bash
claude mcp remove plaxis
```

#### Option C: Manual `claude_desktop_config.json` (for Claude Desktop app)

If you are using the **Claude Desktop** app instead of Claude Code CLI, edit the config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following:

```json
{
  "mcpServers": {
    "plaxis": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "args": ["/Users/sompoteyouwai/env/plaxis_MCP/plaxis_mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/sompoteyouwai/env/plaxis_MCP/plxscripting/src"
      }
    }
  }
}
```

> **Windows example** (adjust Python and project paths):
> ```json
> {
>   "mcpServers": {
>     "plaxis": {
>       "command": "python",
>       "args": ["C:\\Users\\YourName\\plaxis_MCP\\plaxis_mcp_server.py"],
>       "env": {
>         "PYTHONPATH": "C:\\Users\\YourName\\plaxis_MCP\\plxscripting\\src"
>       }
>     }
>   }
> }
> ```

After editing, **restart Claude Desktop** for changes to take effect.

#### Option D: Project-level `.mcp.json` (manual)

Create a `.mcp.json` file in any project root:

```json
{
  "mcpServers": {
    "plaxis": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
      "args": ["/Users/sompoteyouwai/env/plaxis_MCP/plaxis_mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/sompoteyouwai/env/plaxis_MCP/plxscripting/src"
      }
    }
  }
}
```

Claude Code will prompt you to approve the server the first time it detects it.

## Enable PLAXIS Scripting Server

Before Claude can connect, you must start the scripting server inside PLAXIS:

1. Open PLAXIS 2D or 3D
2. Go to **Expert > Configure remote scripting server**
3. Set a **port** (default: `10000` for Input, `10001` for Output)
4. Set a **password**
5. Click **Start**

Note the port and password -- you will need them when connecting.

## Usage

### Start Claude Code

```bash
cd /Users/sompoteyouwai/env/plaxis_MCP
claude
```

Claude will show `plaxis` as an available MCP server. You can then ask Claude to interact with PLAXIS using natural language.

### Example Prompts

**Connect to PLAXIS:**
```
Connect to PLAXIS on port 10000 with password "abc123"
```

**Create a simple model:**
```
Create a new PLAXIS 2D project with a 10m x 5m soil block.
Use Mohr-Coulomb material with c=10 kPa, phi=30, E=20000 kPa.
Generate a medium mesh and calculate.
```

**Work with an existing project:**
```
Open the project at C:\Projects\excavation.p2dx and show me all the phases
```

**Get results:**
```
Show me the maximum displacement after Phase_2
```

## Available Tools

### Connection

| Tool | Description |
|------|-------------|
| `plaxis_connect` | Connect to a running PLAXIS instance |
| `plaxis_disconnect` | Disconnect from PLAXIS |
| `plaxis_server_status` | Check connection status |

### Project Management

| Tool | Description |
|------|-------------|
| `plaxis_new_project` | Create a new empty project |
| `plaxis_open_project` | Open a `.p2dx` or `.p3d` project file |
| `plaxis_close_project` | Close the current project |

### Commands

| Tool | Description |
|------|-------------|
| `plaxis_command` | Execute any single PLAXIS command |
| `plaxis_commands` | Execute multiple commands in sequence |

### Object Inspection

| Tool | Description |
|------|-------------|
| `plaxis_get_object` | Get an object and its properties |
| `plaxis_get_property` | Get a specific property value |
| `plaxis_set_property` | Set a property value |
| `plaxis_list_objects` | List all objects of a type |

### Shortcuts

| Tool | Description |
|------|-------------|
| `plaxis_create_soil` | Create a soil material with common parameters |
| `plaxis_create_borehole` | Create a borehole with soil layers |
| `plaxis_get_results` | Get calculation results for a phase |

## PLAXIS Command Reference

The `plaxis_command` tool accepts any valid PLAXIS command line string. Common commands:

### Geometry
```
point <x> <y>                    # Create a point
line <x1> <y1> <x2> <y2>        # Create a line
polygon <x1> <y1> ... <xn> <yn> # Create a polygon
```

### Materials
```
soilmat <name>                   # Create a soil material
set <Mat>.gammaUnsat <value>     # Set unsaturated unit weight
set <Mat>.gammaSat <value>       # Set saturated unit weight
set <Mat>.Eref <value>           # Set Young's modulus
set <Mat>.cref <value>           # Set cohesion
set <Mat>.phi <value>            # Set friction angle
```

### Mesh
```
gotomesh                         # Switch to mesh mode
mesh <coarseness>                # Generate mesh (0.01=very fine, 0.1=coarse)
```

### Staged Construction
```
gotostages                       # Switch to staged construction
phase <name>                     # Add a new phase
activate <object> <phase>        # Activate object in phase
deactivate <object> <phase>      # Deactivate object in phase
```

### Calculation
```
calculate                        # Run all calculations
selectmeshpoints                 # Select output points
```

### Mode Switching
```
gotosoil                         # Soil mode
gotostructures                   # Structures mode
gotomesh                         # Mesh mode
gotostages                       # Staged construction mode
gotoflow                         # Flow conditions mode
```

## Example Workflow

Here is a complete example of building a simple excavation model through Claude:

```
1. "Connect to PLAXIS on port 10000 with password mypass"
2. "Create a new project"
3. "Create a 40m wide, 20m deep soil body"
4. "Create two soil materials:
    - Clay: gamma=18, E=15000, c=5, phi=25
    - Sand: gamma=20, E=30000, c=0, phi=33"
5. "Create a borehole at x=0 with Clay from 0 to -8m and Sand from -8 to -20m"
6. "Add a 5m deep excavation in the center"
7. "Create phases: Initial, Excavation to -2.5m, Excavation to -5m"
8. "Generate a fine mesh and calculate all phases"
9. "Show me the total displacements for the final phase"
```

## Troubleshooting

### Cannot connect to PLAXIS
- Verify PLAXIS is running and the scripting server is started
- Check the port number matches what PLAXIS shows
- Ensure the password is correct
- Check that no firewall is blocking the connection

### Import errors
- Make sure `pycryptodome` is installed (`pip install pycryptodome`)
- Verify the `PYTHONPATH` in `.mcp.json` points to `plxscripting/src`

### MCP server not showing in Claude
- Restart Claude Code from within this directory
- Check `.mcp.json` exists and has valid JSON
- Run the server manually to check for errors:
  ```bash
  PYTHONPATH=plxscripting/src python3 plaxis_mcp_server.py
  ```

## Architecture

```
Claude Code  <-->  MCP Protocol  <-->  plaxis_mcp_server.py  <-->  PLAXIS HTTP API
                                            |
                                       plxscripting/
                                       (PLAXIS Python SDK)
```

The MCP server wraps the `plxscripting` library (official PLAXIS Python API by Seequent/Bentley) and exposes its functionality as MCP tools. Communication with PLAXIS happens over HTTP to the local scripting server.

## License

The `plxscripting` library is subject to the Plaxis Public License (PPL). See `plxscripting/LICENSE` for details.
