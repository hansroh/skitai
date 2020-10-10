from atila import collectors as mc
import pytest

header = (
    'Content-Disposition: image/jpg; name="file"; filename="{}"\r\n'
    'Content-Type: image/jpg\r\n'
    'Content-Length: {}'
)

def test_name_securing ():
    part = mc.Part (header.format ("/../home/.very|:;&good", 100), 101)
    fw = mc.FileWrapper (part)
    assert fw.name == "very_good"

    part = mc.Part (header.format ("../.../../", 100), 101)
    assert part.get_remote_filename () == "../.../../"
    assert part.get_content_type () == "image/jpg"

    fw = mc.FileWrapper (part)
    assert fw.name == "noname"

    part = mc.Part (header.format ("very_good", 100), 101)
    fw = mc.FileWrapper (part)
    assert fw.name == "very_good"

    part = mc.Part (header.format ("..very_good", 100), 101)
    fw = mc.FileWrapper (part)
    assert fw.name == "very_good"

    part = mc.Part (header.format ("/../home/.very good", 100), 101)
    fw = mc.FileWrapper (part)
    assert fw.name == "very_good"

    part = mc.Part (header.format ("/../home/.very|:&good'", 100), 101)
    fw = mc.FileWrapper (part)
    assert fw.name == "very_good_"

    with pytest.raises (ValueError):
        part = mc.Part (header.format ("../.../../", 100), 99)

