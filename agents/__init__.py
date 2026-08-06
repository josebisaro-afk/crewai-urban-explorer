"""Agents are organised by crew, one subpackage each:
  discovery/   — 4 agents, fast first pass (POIs, events, businesses, weather)
  enrichment/  — 5 agents, deepens Discovery's output
  content/     — 5 agents, final narrative + quality + translation + routes
  hiker/       — 5 agents, only run when Hiker Mode is requested
  director/    — 1 agent, the only one that writes to Supabase

crew.py imports each agent module directly (e.g.
`from agents.discovery import buscador_pois`) rather than through a single
flat registry here — see crew.py's five Crew classes for how each
subpackage's agents/tasks are wired together.
"""
