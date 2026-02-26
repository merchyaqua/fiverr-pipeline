import gzip
import xml.etree.ElementTree as ET
import os
import sys
import json
import shutil
import tempfile
import argparse
import time

# Source - https://stackoverflow.com/a
# Posted by tomvodi, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-15, License - CC BY-SA 4.0

XPATH = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/Path"
REL_PATH_TYPE_XPATH = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/RelativePathType"
REL_PATH_XPATH = "./LiveSet/Tracks/AudioTrack/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip/SampleRef/FileRef/RelativePath"

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aif", ".aiff", ".ogg", ".m4a"}


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
    prompts = {
        "template_path": "Path to template .als file: ",
        "output_dir": "Output directory for generated .als files: ",
        "watch_dir": "Watch directory (where audio files are downloaded): ",
    }
    changed = False
    for key in keys:
        if key not in config or not config[key]:
            value = input(prompts[key]).strip().strip('"').strip("'")
            config[key] = value
            changed = True
    if changed:
        save_config(config)
    return config


def process_audio(audio_path, template_path, output_dir):
    """Replace the audio clip reference in the template .als and open the result in Ableton."""
    audio_path = os.path.abspath(audio_path)
    # Use forward slashes for Ableton compatibility
    audio_path_value = audio_path.replace("\\", "/")

    # Output .als named after the input audio
    audio_name = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = os.path.join(output_dir, f"{audio_name}.als")

    with gzip.open(template_path, "rb") as project:
        xml_bytes = project.read()
        xml_string = xml_bytes.decode("utf-8")
        root = ET.fromstring(xml_string)

    path_tag = root.find(XPATH)
    rel_path_type_tag = root.find(REL_PATH_TYPE_XPATH)
    rel_path_tag = root.find(REL_PATH_XPATH)

    if path_tag is None:
        print("No audio clips in template")
        return None

    path_tag.set("Value", audio_path_value)
    rel_path_type_tag.set("Value", "0")
    rel_path_tag.set("Value", "")

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

    print(f"Created: {output_path}")
    os.startfile(output_path)
    return output_path


def watch(watch_dir, template_path, output_dir):
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
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext not in AUDIO_EXTENSIONS:
                return
            # Brief delay to let the file finish writing
            time.sleep(1)
            print(f"Detected: {event.src_path}")
            try:
                process_audio(event.src_path, template_path, output_dir)
            except Exception as e:
                print(f"Error processing {event.src_path}: {e}")

    observer = Observer()
    observer.schedule(AudioHandler(), watch_dir, recursive=False)
    observer.start()
    print(f"Watching {watch_dir} for new audio files... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="Ableton audio clip pipeline")
    parser.add_argument("audio", nargs="?", help="Path to audio file (manual mode)")
    parser.add_argument("--watch", action="store_true", help="Watch dump folder for new audio files")
    parser.add_argument("--set-template", metavar="PATH", help="Set template .als path")
    parser.add_argument("--set-output-dir", metavar="PATH", help="Set output directory")
    parser.add_argument("--set-watch-dir", metavar="PATH", help="Set watch directory")
    args = parser.parse_args()

    config = load_config()

    # Handle --set-* flags
    if args.set_template:
        config["template_path"] = args.set_template
        save_config(config)
        print(f"template_path set to: {args.set_template}")
    if args.set_output_dir:
        config["output_dir"] = args.set_output_dir
        save_config(config)
        print(f"output_dir set to: {args.set_output_dir}")
    if args.set_watch_dir:
        config["watch_dir"] = args.set_watch_dir
        save_config(config)
        print(f"watch_dir set to: {args.set_watch_dir}")

    # If only --set-* flags were used, exit
    if not args.audio and not args.watch:
        if args.set_template or args.set_output_dir or args.set_watch_dir:
            return
        parser.print_help()
        return

    if args.watch:
        config = ensure_config(config, ["template_path", "output_dir", "watch_dir"])
        watch(config["watch_dir"], config["template_path"], config["output_dir"])
    elif args.audio:
        config = ensure_config(config, ["template_path", "output_dir"])
        process_audio(args.audio, config["template_path"], config["output_dir"])


if __name__ == "__main__":
    main()
