# Changelog

## v0.1.0 (2026-04-15)

### Features

- add changelog generation and GitHub release to sync pipeline
- add Gitea-to-GitHub sync pipeline
- input routing and resample track tools
- live co-pilot — reactive Claude suggestions on Ableton DAW events
- add get_track_send tool to complete send query API
- save_project tool, get_tracks mix fields, browser device types
- track types, clip slot awareness, create returns index, preset listing
- browser device loading via AbleOscRack
- AbleOscRack remote script and rack chain traversal tools
- add session://tracks and session://device MCP resources
- Info View OCR reader and Ableton manual scraper
- Operator parameter descriptions database and population script
- Info View annotation for device parameter database
- musical intelligence layer and device parameter database
- real-time listener tools (subscribe/poll/unsubscribe)
- initial implementation with 46 MCP tools and integration tests

### Bug Fixes

- checkout main before changelog generation
- use correct git date format in changelog generation
- extract pipeline scripts to separate files for YAML compatibility
- dedent heredoc Python scripts in sync pipeline
- activate browser filter_type to populate lazy category children
- correct OSC response index prefix parsing for track/clip/scene/device levels

### Refactoring

- decouple copilot from Claude API, add project notes

### Documentation

- add README, LICENSE, and PyPI metadata

### Tests

- integration tests for MCP resources
- add 46 integration tests across all tool domains

### Chores

- bump version to 0.1.1
- add device description population scripts for all instruments/effects
- update GitHub URLs to real repo
