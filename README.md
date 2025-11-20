# Thesis v3 - Agent Skill Induction

This repository contains the implementation and experiments for agent skill induction research using WebArena environments.

## Directory Structure

### `/agent-skill-induction/`
Main research project containing the Agent Skill Induction (ASI) system.

**Key subdirectories:**
- **`asi/`** - Core ASI implementation
  - Agent implementation with MCP server integration
  - Custom action sets and skill induction logic
  - WebArena task configs (shopping site only)
  - MCP servers for Magento database access
  - Development portal for experiment management
  - See `asi/CLAUDE.md` for detailed documentation

### `/browsergym/`
Local installation of the BrowserGym framework - the unified web navigation infrastructure used by ASI.

**Purpose:**
- Provides gym environment for browser-based task automation
- Wraps multiple benchmarks (WebArena, VisualWebArena, etc.) in unified framework
- Installed in editable mode for potential framework modifications

**Key packages:**
- `browsergym-core` - Core browser environment
- `browsergym-webarena` - WebArena benchmark wrapper
- `browsergym-experiments` - Experiment management utilities

### `/webarena/`
Original WebArena repository - canonical implementation of the WebArena benchmark.

**Purpose:**
- Provides evaluation harness and browser environment logic
- Required dependency for `browsergym-webarena` package
- Contains original task definitions and evaluators

**Note:** While this is the canonical WebArena implementation, the ASI project uses BrowserGym as the primary interface. This directory is kept because BrowserGym's WebArena wrapper imports from it (`webarena.evaluation_harness`, `webarena.browser_env`).

## Quick Start

See `agent-skill-induction/asi/CLAUDE.md` for:
- ASI system overview
- MCP server setup and testing
- Running WebArena tasks
- Development portal usage

## Dependencies

The three directories work together:
1. **`webarena/`** - Provides core WebArena evaluation logic
2. **`browsergym/`** - Wraps WebArena in modern gym interface
3. **`agent-skill-induction/asi/`** - Implements skill induction on top of BrowserGym