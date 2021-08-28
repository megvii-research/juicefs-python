import os
import shutil

import pytest

import juicefs
from juicefs import JuiceFS

import sys
NAME = "test-jfs"
BUCKET = "/tmp"
META = "/tmp/test-jfs.db"
META_URL = "sqlite3:///tmp/test-jfs.db"

if sys.platform == "win32":
    BUCKET = os.path.join(__file__, "..","tmp")
    META = os.path.join(__file__, "..","test-jfs.db")
    META_URL = r"sqlite3:///{}".format(os.path.join(__file__,"..","test-jfs.db"))

@pytest.fixture(scope="session")
def jfs():
    return JuiceFS(NAME, {"meta": META_URL})


def format_juicefs():
    if os.path.exists(META):
        os.unlink(META)
    if os.path.exists(os.path.join(BUCKET, NAME)):
        shutil.rmtree(os.path.join(BUCKET, NAME))

    juicefs_binary = os.path.normpath(
        os.path.join(juicefs.__file__, "..", "lib", "juicefs")
    )

    commands = [
        juicefs_binary,
        "format",
        "--bucket=%s" % BUCKET,
        "--force",
        META_URL,
        NAME,
    ]

    command = " ".join(commands)
    print("run command:", command)
    os.system(command)


format_juicefs()
