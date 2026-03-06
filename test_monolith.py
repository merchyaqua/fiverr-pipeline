import builtins
import gzip
import os
import time
import xml.etree.ElementTree as ET

import pytest

import monolith

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
TEMPLATE_XML = open(os.path.join(FIXTURES_DIR, "template.xml"), "rb").read()

EMPTY_XML = b'<?xml version="1.0"?><Ableton><LiveSet><Tracks></Tracks></LiveSet></Ableton>'

CLIP_XPATH = "DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events/AudioClip"
FILEREF_XPATH = CLIP_XPATH + "/SampleRef/FileRef"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_startfile(monkeypatch):
    """Prevent os.startfile from actually launching Ableton during tests."""
    monkeypatch.setattr(os, "startfile", lambda p: None)


def _make_als(tmp_dir, xml_bytes, name="template.als"):
    path = os.path.join(str(tmp_dir), name)
    with gzip.open(path, "wb") as f:
        f.write(xml_bytes)
    return path


def make_template(tmp_dir):
    return _make_als(tmp_dir, TEMPLATE_XML)


def make_multiclip_als(tmp_dir):
    """Create an .als whose first AudioTrack has two AudioClips (like a real project)."""
    root = ET.fromstring(TEMPLATE_XML)
    events = root.find(
        "./LiveSet/Tracks/AudioTrack"
        "/DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events"
    )
    # Duplicate the existing clip at a different time
    import copy
    clip2 = copy.deepcopy(events.find("AudioClip"))
    clip2.set("Time", "208")
    clip2.set("Id", "99")
    clip2.find("Name").set("Value", "OldClip2")
    clip2.find("SampleRef/FileRef/Path").set("Value", "D:/old/other.wav")
    events.append(clip2)
    xml_bytes = ET.tostring(root, xml_declaration=True)
    return _make_als(tmp_dir, xml_bytes)


def make_template_project(tmp_dir):
    proj = os.path.join(str(tmp_dir), "template_project")
    os.makedirs(os.path.join(proj, "Ableton Project Info"))
    os.makedirs(os.path.join(proj, "Backup"))
    os.makedirs(os.path.join(proj, "Samples", "Recorded"))
    with open(os.path.join(proj, "Ableton Project Info", "AProject.ico"), "wb") as f:
        f.write(b"ICON")
    with gzip.open(os.path.join(proj, "template.als"), "wb") as f:
        f.write(TEMPLATE_XML)
    return proj


def read_als(path):
    with gzip.open(path, "rb") as f:
        return ET.fromstring(f.read().decode("utf-8"))


def dummy_audio(tmp_path, name="Song.mp3"):
    path = os.path.join(str(tmp_path), name)
    open(path, "w").close()
    return path


# ---------------------------------------------------------------------------
# process_audio
# ---------------------------------------------------------------------------

class TestProcessAudio:
    def test_output_file_created(self, tmp_path):
        template = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "TestSong.mp3")
        out = str(tmp_path / "output")
        os.makedirs(out)

        result = monolith.process_audio(audio, template, out)

        assert result is not None
        assert os.path.exists(result)
        assert result.endswith("TestSong.als")

    def test_xml_path_patched(self, tmp_path):
        template = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "MyTrack.wav")
        out = str(tmp_path / "output")
        os.makedirs(out)

        result = monolith.process_audio(audio, template, out)
        root = read_als(result)

        path_val = root.find(monolith.XPATH).get("Value")
        assert "MyTrack.wav" in path_val
        assert "\\" not in path_val
        assert root.find(monolith.REL_PATH_TYPE_XPATH).get("Value") == "0"
        assert root.find(monolith.REL_PATH_XPATH).get("Value") == ""

    def test_track_and_clip_names_set(self, tmp_path):
        template = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "MyTrack.wav")
        out = str(tmp_path / "output")
        os.makedirs(out)

        result = monolith.process_audio(audio, template, out)
        root = read_als(result)
        track = root.find("./LiveSet/Tracks/AudioTrack")

        assert track.find("Name/EffectiveName").get("Value") == "MyTrack"
        assert track.find("Name/MemorizedFirstClipName").get("Value") == "MyTrack"
        assert track.find(CLIP_XPATH + "/Name").get("Value") == "MyTrack"

    def test_output_is_valid_gzip(self, tmp_path):
        template = make_template(tmp_path)
        audio = dummy_audio(tmp_path)
        out = str(tmp_path / "output")
        os.makedirs(out)

        result = monolith.process_audio(audio, template, out)
        with gzip.open(result, "rb") as f:
            data = f.read()
        assert b"<Ableton>" in data

    def test_no_audio_clips_returns_none(self, tmp_path):
        template_path = os.path.join(str(tmp_path), "empty.als")
        with gzip.open(template_path, "wb") as f:
            f.write(EMPTY_XML)

        audio = dummy_audio(tmp_path)
        out = str(tmp_path / "output")
        os.makedirs(out)

        assert monolith.process_audio(audio, template_path, out) is None


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------

class TestCreateProject:
    def test_folder_structure(self, tmp_path):
        tpl = make_template_project(tmp_path)
        audio = dummy_audio(tmp_path, "CoolSong.mp3")
        out = str(tmp_path / "output")
        os.makedirs(out)

        monolith.create_project(audio, tpl, out)

        proj = os.path.join(out, "CoolSong Project")
        assert os.path.isdir(proj)
        assert os.path.isdir(os.path.join(proj, "Ableton Project Info"))
        assert os.path.isdir(os.path.join(proj, "Backup"))
        assert os.path.isdir(os.path.join(proj, "Samples", "Recorded"))
        assert os.path.isfile(os.path.join(proj, "Ableton Project Info", "AProject.ico"))

    def test_als_renamed(self, tmp_path):
        tpl = make_template_project(tmp_path)
        audio = dummy_audio(tmp_path, "CoolSong.mp3")
        out = str(tmp_path / "output")
        os.makedirs(out)

        result = monolith.create_project(audio, tpl, out)

        assert result.endswith("CoolSong.als")
        assert os.path.isfile(result)
        assert not os.path.exists(os.path.join(out, "CoolSong Project", "template.als"))

    def test_audio_patched(self, tmp_path):
        tpl = make_template_project(tmp_path)
        audio = dummy_audio(tmp_path, "CoolSong.mp3")
        out = str(tmp_path / "output")
        os.makedirs(out)

        result = monolith.create_project(audio, tpl, out)
        root = read_als(result)

        assert "CoolSong.mp3" in root.find(monolith.XPATH).get("Value")
        track = root.find("./LiveSet/Tracks/AudioTrack")
        assert track.find("Name/EffectiveName").get("Value") == "CoolSong"


# ---------------------------------------------------------------------------
# add_track
# ---------------------------------------------------------------------------

class TestAddTrack:
    def test_two_audio_tracks(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        root = read_als(als)

        assert len(root.findall("./LiveSet/Tracks/AudioTrack")) == 2

    def test_unique_track_ids(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        root = read_als(als)

        ids = [t.get("Id") for t in root.findall("./LiveSet/Tracks/AudioTrack")]
        assert len(ids) == len(set(ids))

    def test_correct_names(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        new_track = read_als(als).findall("./LiveSet/Tracks/AudioTrack")[1]

        assert new_track.find("Name/EffectiveName").get("Value") == "NewTrack"
        assert new_track.find("Name/MemorizedFirstClipName").get("Value") == "NewTrack"
        assert new_track.find(CLIP_XPATH + "/Name").get("Value") == "NewTrack"

    def test_correct_audio_path(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        fileref = read_als(als).findall("./LiveSet/Tracks/AudioTrack")[1].find(FILEREF_XPATH)

        assert "NewTrack.wav" in fileref.find("Path").get("Value")
        assert fileref.find("RelativePathType").get("Value") == "0"
        assert fileref.find("RelativePath").get("Value") == ""

    def test_original_fileref_also_patched(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        clip = read_als(als).findall("./LiveSet/Tracks/AudioTrack")[1].find(CLIP_XPATH)
        orig_fileref = clip.find("SampleRef/SourceContext/SourceContext/OriginalFileRef/FileRef")

        assert "NewTrack.wav" in orig_fileref.find("Path").get("Value")
        assert orig_fileref.find("RelativePathType").get("Value") == "0"

    def test_multiclip_track_only_keeps_one_clip(self, tmp_path):
        als = make_multiclip_als(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        new_track = read_als(als).findall("./LiveSet/Tracks/AudioTrack")[1]
        clips = new_track.findall(CLIP_XPATH)

        assert len(clips) == 1
        assert "NewTrack.wav" in clips[0].find("SampleRef/FileRef/Path").get("Value")

    def test_inserted_before_return_track(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        tracks = list(read_als(als).find("./LiveSet/Tracks"))

        assert [c.tag for c in tracks] == ["AudioTrack", "AudioTrack", "ReturnTrack"]


class TestAddTrackPointeeIds:
    def test_next_pointee_id_incremented(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        next_id = int(read_als(als).find("./LiveSet/NextPointeeId").get("Value"))

        assert next_id > 100

    def test_all_ids_unique(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        root = read_als(als)

        all_ids = [e.get("Id") for e in root.iter() if "Id" in e.attrib]
        assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs: {all_ids}"

    def test_pointee_ids_unique(self, tmp_path):
        als = make_template(tmp_path)
        audio = dummy_audio(tmp_path, "NewTrack.wav")

        monolith.add_track(als, audio)
        root = read_als(als)

        ids = [e.get("Id") for e in root.iter("Pointee")]
        assert len(ids) == len(set(ids)), f"Duplicate Pointee IDs: {ids}"


# ---------------------------------------------------------------------------
# wait_for_unlock
# ---------------------------------------------------------------------------

class TestWaitForUnlock:
    def test_unlocked_file_returns_immediately(self, tmp_path):
        f = dummy_audio(tmp_path, "test.als")
        start = time.time()
        monolith.wait_for_unlock(f, poll_interval=0.1)
        assert time.time() - start < 1.0

    def test_locked_file_waits(self, tmp_path, monkeypatch):
        f = dummy_audio(tmp_path, "test.als")
        call_count = 0
        real_open = builtins.open

        def mock_open(path, *args, **kwargs):
            nonlocal call_count
            if path == f and "b" in (args[0] if args else ""):
                call_count += 1
                if call_count <= 2:
                    raise PermissionError("File is locked")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)
        start = time.time()
        monolith.wait_for_unlock(f, poll_interval=0.1)

        assert time.time() - start >= 0.15
        assert call_count >= 3


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monolith, "CONFIG_PATH", str(tmp_path / "config.json"))
        monolith.save_config({"template_path": "/some/path.als"})
        assert monolith.load_config()["template_path"] == "/some/path.als"

    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monolith, "CONFIG_PATH", str(tmp_path / "nope.json"))
        assert monolith.load_config() == {}
