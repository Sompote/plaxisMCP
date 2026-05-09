# PLAXIS MCP Server

**Version:** v0.1.0

> Let **Claude AI** talk directly to **PLAXIS 2D** — create geometry, assign materials, run calculations, and read results using plain English.

This project wraps the official PLAXIS Python scripting library as a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server, so Claude Code can control PLAXIS like a geotechnical engineer.

---

## What it does

Instead of clicking through PLAXIS menus, you describe what you want in natural language and Claude does the work:

```
"Create an embankment on soft clay, 3m high with 1:2 slopes, run a stability analysis"
```

Claude will create the geometry, assign Mohr-Coulomb materials, generate the mesh, set up K0 + construction + safety phases, and run the calculation — all inside your running PLAXIS 2D instance.

---

## Prerequisites

- **PLAXIS 2D Connect Edition V20** installed on Windows
- **Python 3.9 or later** ([python.org](https://www.python.org/downloads/))
- **Claude Code** ([install guide](https://docs.anthropic.com/claude-code))

---

## Installation

### Step 1 — Clone this repository

```bat
git clone https://github.com/yourname/plaxisMCP.git
cd plaxisMCP
```

### Step 2 — Install Python dependencies

```bat
pip install -r requirements.txt
```

This installs:
- `mcp[cli]` — the MCP server framework
- `pycryptodome` — required for PLAXIS encrypted communication

### Step 3 — Find the `plxscripting` library

The PLAXIS Python scripting library (`plxscripting`) ships **inside your PLAXIS installation** — you do not need to install it separately.

#### Where to find it

Every PLAXIS version installs its own Python environment. The library is always at:

```
<PLAXIS install folder>\python\Lib\site-packages\plxscripting\
```

Common locations by version:

| PLAXIS version | Default path |
|----------------|-------------|
| **2D V20** (Connect Edition) | `C:\Program Files\Bentley\Geotechnical\PLAXIS 2D CONNECT Edition V20\python\Lib\site-packages` |
| **2D V21** | `C:\Program Files\Bentley\Geotechnical\PLAXIS 2D CONNECT Edition V21\python\Lib\site-packages` |
| **2D V22 / V23** | `C:\Program Files\Bentley\Geotechnical\PLAXIS 2D CONNECT Edition V22\python\Lib\site-packages` |
| **2D 2024 / 2025** (Seequent) | `C:\Program Files\Seequent\PLAXIS 2D 2024\python\Lib\site-packages` |
| **3D V20** | `C:\Program Files\Bentley\Geotechnical\PLAXIS 3D CONNECT Edition V20\python\Lib\site-packages` |
| **3D V21 / V22** | `C:\Program Files\Bentley\Geotechnical\PLAXIS 3D CONNECT Edition V21\python\Lib\site-packages` |

> Not sure where your version installed? Open Windows Explorer and search for `plxscripting` under `C:\Program Files\`.  
> Or run in a terminal:
> ```bat
> dir /s /b "C:\Program Files\plxscripting" 2>nul
> dir /s /b "C:\Program Files (x86)\plxscripting" 2>nul
> ```

#### Tell the MCP server which path to use

Open `plaxis_mcp_server.py` and update the `_OFFICIAL` variable near the top of the file:

```python
# ── Library paths ─────────────────────────────────────────────────────────────
# Set _OFFICIAL to the site-packages folder of YOUR PLAXIS version.

_OFFICIAL = (
    r"C:\Program Files\Bentley\Geotechnical"
    r"\PLAXIS 2D CONNECT Edition V20\python\Lib\site-packages"
)
```

Replace the path with the one that matches your installation from the table above.

> **The bundled fallback** — a copy of `plxscripting` is included in the `plxscripting\` folder.  
> If `_OFFICIAL` is not found at startup the server automatically uses this bundled copy.  
> The bundled version may be older than what ships with newer PLAXIS releases.

---

## Configure Claude Code

The `.mcp.json` file in this folder registers the server with Claude Code automatically.

Open Claude Code **from inside the `plaxisMCP` folder**:

```bat
cd plaxisMCP
claude
```

Claude will detect the MCP server and show `plaxis` as an available tool.

### Global install (use from any project)

To make PLAXIS available in every Claude Code session regardless of directory:

```bat
claude mcp add plaxis -- python C:\full\path\to\plaxisMCP\plaxis_mcp_server.py
```

Verify:

```bat
claude mcp list
```

---

## Bundled Claude skill (`SKILL.md`)

This repo ships with a Claude Code **skill** that teaches the agent how to drive PLAXIS correctly — connection workflow, the standard build order (materials → boreholes → structures → BCs → mesh → phases → calculate → results), and a long list of empirically-confirmed V20 quirks (Eref read-only, Undrained_C + K0 conflict, soillayer behavior, `linedispl` BC handling, Safety phase setup, polygon extension across boreholes, mesh sizing, the `plaxis_set_fixities` over-constraint bug, and more).

Two copies are provided:

- `.claude/skills/plaxis/SKILL.md` — auto-loaded by Claude Code when this repo is the working directory; the agent invokes it whenever the user mentions PLAXIS, embankments, soft clay, factor of safety, settlement, or any `mcp__plaxis__*` tool.
- `SKILL.md` (project root) — a convenience copy for browsing on GitHub.

You don't need to do anything to "enable" the skill — it activates automatically once Claude Code is launched from the `plaxisMCP` folder. To use it from any directory, see the *Global install* section above and the skill content will travel with the MCP tools.

If you hit a new V20 quirk, edit `.claude/skills/plaxis/SKILL.md` and add it under §4 — the next session will benefit.

---

## Enable the PLAXIS Scripting Server

Claude communicates with PLAXIS over a local HTTP server that you must start inside PLAXIS:

1. Open **PLAXIS 2D Connect Edition V20**
2. Go to **Expert → Configure remote scripting server**
3. Set **Port** = `10000` *(default — no need to change)*
4. Set a **Password** of your choice
5. Click **Start server**

The PLAXIS title bar will show:
```
PLAXIS 2D (Untitled) *** SERVER ACTIVE on port 10000 (SECURED) ***
```

---

## Usage

Start a Claude Code session and tell it to connect:

```
Connect to PLAXIS on port 10000 with password "yourpassword"
```

Then describe your model:

```
Create a new embankment on soft clay problem:
- Soft clay foundation: 40m wide, 8m deep, Su = 20 kPa
- Embankment: 3m high, 6m crest, 1V:2H slopes
- Run initial K0, construction, and safety analysis phases
```

---

## Example prompts

| Goal | Prompt |
|------|--------|
| New project | `Create a new PLAXIS project with 20m×10m soft clay` |
| Embankment stability | `Build an embankment on soft clay and find the factor of safety` |
| Open existing project | `Open the project at C:\Projects\retaining_wall.p2dx` |
| Get results | `What is the maximum settlement after Phase_2?` |
| Inspect model | `List all soil materials and their parameters` |

---

## Project structure

```
plaxisMCP/
├── plaxis_mcp_server.py            ← Main MCP server (edit this to customise)
├── .mcp.json                       ← Claude Code auto-configuration
├── requirements.txt                ← Python dependencies
├── plxscripting/                   ← Bundled fallback library (from PLAXIS PPL)
│   └── src/
│       └── plxscripting/
├── .claude/
│   └── skills/
│       └── plaxis/
│           └── SKILL.md            ← PLAXIS skill auto-loaded by Claude Code
├── SKILL.md                        ← Mirror of the skill for GitHub browsing
└── README.md
```

---

## Known limitations & workarounds

### `Eref` is read-only via command line

PLAXIS 2D V20 does not allow setting Young's modulus (`Eref`) through the command-line scripting interface. Use **`Gref`** instead — PLAXIS computes `Eref` automatically:

```
Gref = E / (2 × (1 + ν))
```

Example — E = 10 000 kN/m², ν = 0.495:

```
set Clay.Gref 3344
```

### Set unit weights before drainage type

`gammaSat` becomes read-only after `DrainageType 3` (Undrained C) is set. Always set `gammaUnsat` and `gammaSat` first:

```
set Clay.gammaUnsat 15     ← first
set Clay.gammaSat   16     ← second
set Clay.DrainageType 3    ← last
```

### `soillayer` takes thickness, not elevation

```
soillayer 8     ← creates an 8 m thick layer  ✓
soillayer -8    ← error (must be positive)    ✗
```

Only call `soillayer` for the **first** borehole. Additional boreholes inherit the same layers automatically.

### Undrained C + K0 procedure = error

The K0 procedure (InitialPhase default) is incompatible with Undrained C materials.  
Switch to gravity loading:

```
set InitialPhase.DeformCalcType "gravityloading"
```

### Boundary condition command

The correct command is `linedispl`, not `linedisplacement`:

```
linedispl (0 -8) (40 -8)
set LineDisplacement_1.Displacement_x 1    ← 1 = Fixed
set LineDisplacement_1.Displacement_y 1    ← 0 = Free
```

---

## Troubleshooting

**Cannot connect to PLAXIS**
- Make sure the scripting server is started inside PLAXIS (see above)
- Check the port (`10000`) and password match exactly
- Allow Python through Windows Firewall on port 10000

**`No module named 'distutils'` on Python 3.12+**
```bat
pip install setuptools
```

**MCP server not showing in Claude Code**
```bat
python plaxis_mcp_server.py    ← run manually to see errors
```
Then check `.mcp.json` exists in the current directory.

**`plxscripting` not found**
- Confirm PLAXIS 2D V20 is installed
- Update the path in `plaxis_mcp_server.py` (see Step 3 above)
- Or use the bundled fallback in `plxscripting\src\`

---

## How it works

```
You (natural language)
        ↓
   Claude Code
        ↓  MCP Protocol (stdio)
plaxis_mcp_server.py
        ↓  plxscripting (official PLAXIS Python library)
PLAXIS 2D Scripting Server  (localhost:10000, encrypted HTTP)
        ↓
   PLAXIS 2D
```

---

## Contributing

Pull requests welcome. When adding new tools, follow the pattern in `plaxis_mcp_server.py`:

1. Decorate with `@mcp.tool()`
2. Use `_best_set(s, g, name, prop, value)` to set properties (handles read-only cmd-line properties automatically)
3. Always return `json.dumps({"status": "success"|"error", ...})`

---

## License

The **`plxscripting`** library bundled in this repo is subject to the  
**Plaxis Public License (PPL) Version 1.0** — see `plxscripting\LICENSE`.

The MCP server code (`plaxis_mcp_server.py`) is released under the **MIT License**.
