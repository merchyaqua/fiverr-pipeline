import gzip
import json
import os
import tempfile
import xml.etree.ElementTree as ET

import monolith


# Minimal Ableton-like XML structure with the expected XPath
TEMPLATE_XML = """\
<?xml version='1.0' encoding='us-ascii'?>
<Ableton>
<LiveSet>
<Tracks>
<AudioTrack>
<DeviceChain>
<MainSequencer>
<Sample>
<ArrangerAutomation>
<Events>
<AudioClip>
<SampleRef>
<FileRef>
<Path Value="D:/original/audio.wav" />
<RelativePathType Value="3" />
<RelativePath Value="../../audio.wav" />
</FileRef>
</SampleRef>
</AudioClip>
</Events>
</ArrangerAutomation>
</Sample>
</MainSequencer>
</DeviceChain>
</AudioTrack>
</Tracks>
</LiveSet>
</Ableton>
"""


def make_template(tmp_dir):
    """Create a fake gzip-compressed .als template and return its path."""
    template_path = os.path.join(tmp_dir, "template.als")
    with gzip.open(template_path, "wb") as f:
        f.write(TEMPLATE_XML.encode("utf-8"))
    return template_path


def read_output_als(path):
    """Decompress an output .als and return the XML root."""
    with gzip.open(path, "rb") as f:
        return ET.fromstring(f.read().decode("utf-8"))


class TestProcessAudio:
    def test_output_file_created(self, tmp_path):
        template = make_template(str(tmp_path))
        audio = os.path.join(str(tmp_path), "TestSong.mp3")
        open(audio, "w").close()  # dummy file
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir)

        # Patch os.startfile so it doesn't actually open Ableton
        original_startfile = os.startfile
        os.startfile = lambda p: None
        try:
            result = monolith.process_audio(audio, template, output_dir)
        finally:
            os.startfile = original_startfile

        assert result is not None
        assert os.path.exists(result)
        assert result.endswith("TestSong.als")

    def test_xml_path_patched(self, tmp_path):
        template = make_template(str(tmp_path))
        audio = os.path.join(str(tmp_path), "MyTrack.wav")
        open(audio, "w").close()
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir)

        os.startfile = lambda p: None
        try:
            result = monolith.process_audio(audio, template, output_dir)
        finally:
            os.startfile = getattr(os, "startfile", None)

        root = read_output_als(result)
        path_val = root.find(monolith.XPATH).get("Value")
        rel_type = root.find(monolith.REL_PATH_TYPE_XPATH).get("Value")
        rel_path = root.find(monolith.REL_PATH_XPATH).get("Value")

        # Path should point to our audio file with forward slashes
        assert "MyTrack.wav" in path_val
        assert "\\" not in path_val
        assert rel_type == "0"
        assert rel_path == ""

    def test_output_is_valid_gzip(self, tmp_path):
        template = make_template(str(tmp_path))
        audio = os.path.join(str(tmp_path), "Song.mp3")
        open(audio, "w").close()
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir)

        os.startfile = lambda p: None
        try:
            result = monolith.process_audio(audio, template, output_dir)
        finally:
            os.startfile = getattr(os, "startfile", None)

        # Should decompress without error
        with gzip.open(result, "rb") as f:
            data = f.read()
        assert len(data) > 0
        assert b"<Ableton>" in data

    def test_no_audio_clips_returns_none(self, tmp_path):
        """Template with no matching XPath should return None."""
        empty_xml = '<?xml version="1.0"?><Ableton><LiveSet></LiveSet></Ableton>'
        template_path = os.path.join(str(tmp_path), "empty.als")
        with gzip.open(template_path, "wb") as f:
            f.write(empty_xml.encode("utf-8"))

        audio = os.path.join(str(tmp_path), "Song.mp3")
        open(audio, "w").close()
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir)

        result = monolith.process_audio(audio, template_path, output_dir)
        assert result is None


class TestConfig:
    def test_save_and_load(self, tmp_path):
        config_path = os.path.join(str(tmp_path), "config.json")
        original = monolith.CONFIG_PATH
        monolith.CONFIG_PATH = config_path
        try:
            monolith.save_config({"template_path": "/some/path.als"})
            loaded = monolith.load_config()
            assert loaded["template_path"] == "/some/path.als"
        finally:
            monolith.CONFIG_PATH = original

    def test_load_missing_returns_empty(self, tmp_path):
        original = monolith.CONFIG_PATH
        monolith.CONFIG_PATH = os.path.join(str(tmp_path), "nonexistent.json")
        try:
            assert monolith.load_config() == {}
        finally:
            monolith.CONFIG_PATH = original
