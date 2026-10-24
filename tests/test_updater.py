import io
import json

from vacances import updater


def test_parse_version():
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("1.10") == (1, 10, 0)
    assert updater.parse_version("v1.10.0") > updater.parse_version("1.9.9")


def test_analyser_release():
    rel = updater.analyser_release({
        "tag_name": "v1.1.0",
        "html_url": "https://github.com/x/y/releases/tag/v1.1.0",
        "body": "Notes",
        "assets": [
            {"name": "autre.zip", "browser_download_url": "https://a/autre.zip"},
            {"name": "CalculateurVacances.exe", "browser_download_url": "https://a/CalculateurVacances.exe"},
        ],
    })
    assert rel.version == "1.1.0"
    assert rel.url_exe == "https://a/CalculateurVacances.exe"


def _faux_urlopen(tag):
    def urlopen(req, timeout=None):
        return io.BytesIO(json.dumps({"tag_name": tag, "assets": []}).encode())
    return urlopen


def test_verifier(monkeypatch):
    monkeypatch.setattr(updater.urllib.request, "urlopen", _faux_urlopen("v1.1.0"))
    assert updater.verifier("1.0.0").version == "1.1.0"
    assert updater.verifier("1.1.0") is None
    assert updater.verifier("2.0.0") is None


def test_peut_installer_hors_exe():
    rel = updater.Release("9.9.9", "https://a/x.exe", "https://a", "")
    assert not updater.peut_installer(rel)  # en développement : pas un .exe gelé


def test_environnement_propre():
    env = updater.environnement_propre({
        "PATH": "C:\\Windows",
        "_PYI_APPLICATION_HOME_DIR": "C:\\Temp\\_MEI123",
        "_PYI_PARENT_PROCESS_LEVEL": "1",
        "_MEIPASS2": "C:\\Temp\\_MEI123",
    })
    assert env == {"PATH": "C:\\Windows", "PYINSTALLER_RESET_ENVIRONMENT": "1"}
