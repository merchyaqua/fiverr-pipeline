# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool for automating Ableton Live project file manipulation. It replaces audio clip references inside `.als` files (which are gzip-compressed XML) with new file paths — used for a Fiverr-based music production workflow.

## How It Works

1. Ableton `.als` files are gzip-compressed XML
2. The pipeline decompresses the template `.als`, parses the XML, modifies the audio file reference path in the first AudioTrack's first AudioClip, then re-compresses and writes a new `.als` file
3. `monolith.py` is the main script — it reads a template `.als`, patches the `FileRef/Path` to point to a new audio file, writes an intermediate XML file, gzip-compresses it to an output `.als`, and opens it in Ableton via `os.startfile`
4. `compression.py` is an earlier version with helper functions (`get_xml_text`, `write_xml_to_als`, `replace_sample_audio`) that do the same gzip/XML round-trip

## Key XML XPaths

The audio file reference lives at:
```
./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/Path
```
Related tags that get modified: `RelativePathType` (set to `0`) and `RelativePath` (cleared).

## Running

```bash
python monolith.py
```

File paths for input audio, template project, and output are hardcoded at the top of `monolith.py`. No external dependencies beyond the Python standard library.
