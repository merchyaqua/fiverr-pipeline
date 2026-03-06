import argparse
import copy
import gzip
import json
import os
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import pystray
from PIL import Image

# Source - https://stackoverflow.com/a
# Posted by tomvodi, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-15, License - CC BY-SA 4.0

FILEREF_XPATH = (
    "./LiveSet/Tracks/AudioTrack"
    "/DeviceChain/MainSequencer/Sample/ArrangerAutomation"
    "/Events/AudioClip/SampleRef/FileRef"
)
XPATH = FILEREF_XPATH + "/Path"
REL_PATH_TYPE_XPATH = FILEREF_XPATH + "/RelativePathType"
REL_PATH_XPATH = FILEREF_XPATH + "/RelativePath"

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aif", ".aiff", ".ogg", ".m4a"}

_icon = None  # tray icon instance, set in main()


def notify(title, message):
    if _icon is not None:
        _icon.notify(message, title)
    else:
        print(f"[{title}] {message}")

CONFIG_PROMPTS = {
    "template_path": "Path to template .als file: ",
    "template_project_dir": "Path to template project directory: ",
    "output_dir": "Output directory for generated .als files: ",
    "watch_dir": "Watch directory (where audio files are downloaded): ",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def ensure_config(config, keys):
    """Prompt user for any missing config keys. Returns updated config."""
    changed = False
    for key in keys:
        if key not in config or not config[key]:
            value = input(CONFIG_PROMPTS[key]).strip().strip('"').strip("'")
            config[key] = value
            changed = True
    if changed:
        save_config(config)
    return config


# ---------------------------------------------------------------------------
# .als I/O helpers
# ---------------------------------------------------------------------------

def _read_als(als_path):
    """Read a gzip-compressed .als file and return the XML root."""
    with gzip.open(als_path, "rb") as f:
        return ET.fromstring(f.read().decode("utf-8"))


def _write_als(root, output_path):
    """Write an XML root to a gzip-compressed .als file."""
    tree = ET.ElementTree(root)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        tmp_path = tmp.name
    try:
        tree.write(tmp_path, xml_declaration=True)
        with open(tmp_path, "rb") as f_in:
            with gzip.open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    finally:
        os.unlink(tmp_path)


def _audio_name(audio_path):
    """Return the stem of an audio filename (no extension)."""
    return os.path.splitext(os.path.basename(audio_path))[0]


# ---------------------------------------------------------------------------
# XML patching helpers
# ---------------------------------------------------------------------------

def _patch_fileref(fileref, audio_path_value):
    """Overwrite Path, RelativePathType, and RelativePath in a single FileRef element."""
    for tag, val in [("Path", audio_path_value),
                     ("RelativePathType", "0"),
                     ("RelativePath", "")]:
        elem = fileref.find(tag)
        if elem is not None:
            elem.set("Value", val)


def _patch_track_audio(track, audio_path_value, name):
    """Patch a single AudioTrack's file reference, track name, and clip name."""
    clip = track.find(
        "DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip"
    )
    if clip is None:
        return

    # Patch ALL FileRef elements (main SampleRef + OriginalFileRef in SourceContext)
    for fileref in clip.iter("FileRef"):
        _patch_fileref(fileref, audio_path_value)

    clip_name = clip.find("Name")
    if clip_name is not None:
        clip_name.set("Value", name)

    name_elem = track.find("Name")
    if name_elem is not None:
        for tag in ("EffectiveName", "MemorizedFirstClipName"):
            child = name_elem.find(tag)
            if child is not None:
                child.set("Value", name)


def _remap_ids(element, next_id):
    """Remap all Id attributes in element and its descendants. Returns new next_id."""
    if "Id" in element.attrib:
        element.set("Id", str(next_id))
        next_id += 1
    for child in element:
        next_id = _remap_ids(child, next_id)
    return next_id


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def process_audio(audio_path, template_path, output_dir):
    """Replace the audio clip reference in the template .als and open the result in Ableton."""
    audio_path = os.path.abspath(audio_path)
    name = _audio_name(audio_path)
    output_path = os.path.join(output_dir, f"{name}.als")

    root = _read_als(template_path)
    track = root.find("./LiveSet/Tracks/AudioTrack")
    if track is None:
        print("No audio clips in template")
        return None

    _patch_track_audio(track, audio_path.replace("\\", "/"), name)
    _write_als(root, output_path)

    print(f"Created: {output_path}")
    os.startfile(output_path)
    return output_path


def create_project(audio_path, template_project_dir, output_parent_dir):
    """Create a new Ableton project folder from the template, patched with the given audio."""
    audio_path = os.path.abspath(audio_path)
    name = _audio_name(audio_path)

    notify("Fiverr Pipeline", f"Creating new project for {name}...")

    project_dir = os.path.join(output_parent_dir, f"{name} Project")
    shutil.copytree(template_project_dir, project_dir)

    als_files = [f for f in os.listdir(project_dir) if f.endswith(".als")]
    if not als_files:
        notify("Error", f"No .als in template project: {template_project_dir}")
        return None

    old_als = os.path.join(project_dir, als_files[0])
    new_als = os.path.join(project_dir, f"{name}.als")
    os.rename(old_als, new_als)

    root = _read_als(new_als)
    track = root.find("./LiveSet/Tracks/AudioTrack")
    if track is None:
        notify("Error", "No AudioTrack in template")
        return None

    _patch_track_audio(track, audio_path.replace("\\", "/"), name)
    _write_als(root, new_als)

    notify("Fiverr Pipeline", f"{name} Project ready")
    os.startfile(new_als)
    return new_als


def add_track(als_path, audio_path):
    """Add a new AudioTrack to an existing .als file, cloned from the first AudioTrack."""
    audio_path = os.path.abspath(audio_path)
    name = _audio_name(audio_path)

    root = _read_als(als_path)
    tracks_elem = root.find("./LiveSet/Tracks")
    if tracks_elem is None:
        print("No Tracks element in .als")
        return None

    first_audio_track = tracks_elem.find("AudioTrack")
    if first_audio_track is None:
        print("No AudioTrack to clone")
        return None

    max_track_id = max(
        (int(t.get("Id")) for t in tracks_elem if t.get("Id") is not None),
        default=0,
    )

    next_pointee_elem = root.find("./LiveSet/NextPointeeId")
    next_id = int(next_pointee_elem.get("Value"))

    clone = copy.deepcopy(first_audio_track)
    clone.set("Id", str(max_track_id + 1))

    # Strip extra AudioClips — keep only the first as a structural template
    events = clone.find(
        "DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events"
    )
    if events is not None:
        clips = events.findall("AudioClip")
        for clip in clips[1:]:
            events.remove(clip)

    next_id = _remap_ids(clone, next_id)
    next_pointee_elem.set("Value", str(next_id))

    _patch_track_audio(clone, audio_path.replace("\\", "/"), name)

    # Insert before first ReturnTrack (or at end)
    insert_index = len(list(tracks_elem))
    for i, child in enumerate(tracks_elem):
        if child.tag == "ReturnTrack":
            insert_index = i
            break
    tracks_elem.insert(insert_index, clone)

    _write_als(root, als_path)
    notify("Fiverr Pipeline", f"Done — reopening in Ableton")
    os.startfile(als_path)
    return als_path


def wait_for_unlock(path, poll_interval=2):
    """Block until the file at path is not locked by another process."""
    warned = False
    while True:
        try:
            with open(path, "r+b"):
                return
        except PermissionError:
            if not warned:
                notify("Close Ableton", "Save & close to add the track")
                warned = True
            time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Watcher
# ---------------------------------------------------------------------------

def watch(watch_dir, template_project_dir, output_parent_dir):
    """Watch a directory for new audio files using watchdog."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("watchdog is required for --watch mode.")
        print("Install it with: pip install watchdog")
        sys.exit(1)

    class AudioHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            if os.path.splitext(event.src_path)[1].lower() not in AUDIO_EXTENSIONS:
                return
            time.sleep(1)  # let the file finish writing
            name = _audio_name(event.src_path)
            notify("Fiverr Pipeline", f"Detected: {name}")
            try:
                audio_dir = os.path.dirname(event.src_path)
                als_files = [f for f in os.listdir(audio_dir) if f.endswith(".als")]
                if als_files:
                    als_path = os.path.join(audio_dir, als_files[0])
                    wait_for_unlock(als_path)
                    notify("Fiverr Pipeline", f"Adding track to {os.path.basename(als_path)}...")
                    add_track(als_path, event.src_path)
                else:
                    create_project(event.src_path, template_project_dir, output_parent_dir)
            except Exception as e:
                notify("Error", str(e))

    observer = Observer()
    observer.schedule(AudioHandler(), watch_dir, recursive=True)
    observer.start()
    print(f"Watching {watch_dir} for new audio files... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ableton audio clip pipeline")
    parser.add_argument("audio", nargs="?", help="Path to audio file (manual mode)")
    parser.add_argument("--watch", action="store_true", help="Watch for new audio files")
    parser.add_argument("--set-template", metavar="PATH", help="Set template .als path")
    parser.add_argument("--set-template-project", metavar="PATH", help="Set template project directory")
    parser.add_argument("--set-output-dir", metavar="PATH", help="Set output directory")
    parser.add_argument("--set-watch-dir", metavar="PATH", help="Set watch directory")
    args = parser.parse_args()

    config = load_config()

    setters = {
        "set_template": "template_path",
        "set_template_project": "template_project_dir",
        "set_output_dir": "output_dir",
        "set_watch_dir": "watch_dir",
    }
    any_set = False
    for arg_name, config_key in setters.items():
        value = getattr(args, arg_name)
        if value:
            config[config_key] = value
            save_config(config)
            print(f"{config_key} set to: {value}")
            any_set = True

    if not args.audio and not args.watch:
        if any_set:
            return
        parser.print_help()
        return

    if args.watch:
        config = ensure_config(config, ["template_project_dir", "watch_dir"])

        global _icon
        image = Image.open(ICON_PATH)
        _icon = pystray.Icon(
            "Fiverr Pipeline",
            image,
            "Fiverr Pipeline",
            menu=pystray.Menu(pystray.MenuItem("Quit", lambda icon, item: icon.stop())),
        )
        _icon.run_detached()

        watch(config["watch_dir"], config["template_project_dir"], config["watch_dir"])
    elif args.audio:
        config = ensure_config(config, ["template_path", "output_dir"])
        process_audio(args.audio, config["template_path"], config["output_dir"])


if __name__ == "__main__":
    main()
