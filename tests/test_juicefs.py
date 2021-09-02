import os
import random
import shutil
import sys
import time
from pathlib import Path

import pytest


def remove_os_file(path):
    if os.path.exists(path):
        os.chmod(path, 0o777)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    if os.path.lexists(path):
        os.remove(path)


def create_os_tempfile(path):
    remove_os_file(path)
    yield path
    remove_os_file(path)


def remove_file(jfs, path):
    if jfs.path.exists(path):
        jfs.chmod(path, 0o777)
    if jfs.path.lexists(path):
        jfs.rmtree(path)


def create_tempfile(jfs, path):
    remove_file(jfs, path)
    yield path
    remove_file(jfs, path)


@pytest.fixture()
def dirname(jfs):
    yield from create_tempfile(jfs, "/test.dir")


@pytest.fixture()
def dirname2(jfs):
    yield from create_tempfile(jfs, "/test.dir/dir2")


@pytest.fixture()
def dirname3(jfs):
    yield from create_tempfile(jfs, "/test.dir/dir2/dir3")


@pytest.fixture()
def filename(jfs):
    yield from create_tempfile(jfs, "/test.file")


@pytest.fixture()
def filename2(jfs):
    yield from create_tempfile(jfs, "/test.file.2")


@pytest.fixture()
def filename3(jfs):
    yield from create_tempfile(jfs, "/test.file.3")


@pytest.fixture()
def os_filename():
    yield from create_os_tempfile("./test.file")


@pytest.fixture()
def os_filename2():
    yield from create_os_tempfile("./test.file.2")


@pytest.fixture()
def os_dirname(jfs):
    yield from create_os_tempfile("./test.dir")


CONTENT = b"text"
CONTENT2 = b"text/text"


def test_rename(jfs, filename, filename2, dirname):
    jfs.mkdir(dirname)
    jfs.create(filename)
    with pytest.raises(FileExistsError):
        jfs.rename(filename, dirname)

    assert jfs.path.exists(filename2) is False
    assert jfs.path.exists(filename) is True
    jfs.rename(filename, filename2)
    assert jfs.path.exists(filename2) is True
    assert jfs.path.exists(filename) is False

    jfs.create(filename, 0o777)
    assert jfs.path.exists(filename) is True
    assert jfs.path.exists(filename2) is True
    with pytest.raises(FileExistsError):
        jfs.rename(filename, filename2)


def test_replace(jfs, filename, filename2, dirname):
    test_rename(jfs, filename, filename2, dirname)


def test_symlink(jfs, filename, filename2):
    assert jfs.path.islink(filename2) is False
    jfs.create(filename)
    jfs.symlink(filename, filename2)
    assert jfs.path.islink(filename2) is True
    assert jfs.stat(filename) == jfs.stat(filename2)


def test_unlink(jfs, filename, dirname):
    assert jfs.path.exists(filename) is False
    jfs.create(filename)
    assert jfs.path.exists(filename) is True
    jfs.unlink(filename)
    assert jfs.path.exists(filename) is False

    jfs.mkdir(dirname)
    with pytest.raises(IsADirectoryError):
        jfs.unlink(dirname)


def test_remove(jfs, filename, dirname):
    test_unlink(jfs, filename, dirname)


def test_makedirs(jfs, dirname, dirname2, dirname3):
    assert jfs.path.isdir(dirname) is False
    jfs.makedirs(dirname)

    assert jfs.path.isdir(dirname) is True
    jfs.makedirs(dirname, exist_ok=True)

    with pytest.raises(OSError):
        jfs.makedirs(dirname)

    assert jfs.path.isdir(dirname2) is False
    jfs.makedirs(dirname2)

    assert jfs.path.isdir(dirname2) is True
    jfs.makedirs(dirname2, exist_ok=True)

    with pytest.raises(OSError):
        jfs.makedirs(dirname2)

    assert jfs.path.isdir(dirname3) is False
    jfs.makedirs(dirname3)

    assert jfs.path.isdir(dirname3) is True
    jfs.makedirs(dirname3, exist_ok=True)

    with pytest.raises(OSError):
        jfs.makedirs(dirname3)


def test_removedirs(jfs, dirname, dirname2, dirname3, filename):
    jfs.makedirs(dirname2)
    with pytest.raises(OSError):
        jfs.removedirs(dirname)

    jfs.removedirs(dirname2)
    assert jfs.path.exists(dirname2) is False

    jfs.makedirs(dirname2)
    jfs.create(dirname + "/" + filename, 0o777)
    jfs.removedirs(dirname2)
    assert jfs.path.exists(dirname2) is False
    assert jfs.path.exists(dirname + "/" + filename) is True
    jfs.unlink(dirname + "/" + filename)


# def test_utime(jfs, filename):
#     jfs.create(filename)
#     start = int(time.time())
#     jfs.utime(filename)
#     stop = int(time.time())
#     assert jfs.path.getatime(filename) == jfs.path.getmtime(filename)
#     assert start <= int(jfs.path.getatime(filename)) <= stop
#     assert start <= int(jfs.path.getmtime(filename)) <= stop


def test_mkdir(jfs, dirname):
    jfs.mkdir(dirname)
    assert jfs.path.exists(dirname) is True

    with pytest.raises(FileExistsError):
        jfs.mkdir(dirname)

    jfs.chmod(dirname, 0o444)  # readonly
    with pytest.raises(PermissionError):
        jfs.mkdir(Path(os.path.join(dirname, "test")).as_posix())


def test_rmdir(jfs, filename, dirname):
    jfs.mkdir(dirname)
    assert jfs.path.exists(dirname) is True
    jfs.rmdir(dirname)
    assert jfs.path.exists(dirname) is False

    jfs.create(filename)
    with pytest.raises(NotADirectoryError):
        jfs.rmdir(filename)

    jfs.mkdir(dirname)
    jfs.create(dirname + "/test.file", 0o777)
    with pytest.raises(OSError):  # Directory not empty
        jfs.rmdir(dirname)
    jfs.unlink(dirname + "/test.file")


def test_exists(jfs, filename, dirname):
    assert jfs.path.exists(filename) is False
    jfs.create(filename)
    assert jfs.path.exists(filename) is True

    assert jfs.path.exists(dirname) is False
    jfs.mkdir(dirname)
    assert jfs.path.exists(dirname) is True


def test_lexists(jfs, filename, filename2, filename3, dirname):
    assert jfs.path.lexists(filename) is False
    jfs.create(filename)
    assert jfs.path.lexists(filename) is True
    jfs.symlink(filename, filename2)
    assert jfs.path.lexists(filename2) is True
    jfs.unlink(filename)
    assert jfs.path.lexists(filename2) is True
    jfs.unlink(filename2)
    assert jfs.path.lexists(filename2) is False

    assert jfs.path.lexists(dirname) is False
    jfs.mkdir(dirname)
    assert jfs.path.lexists(dirname) is True
    jfs.symlink(dirname, filename3)
    assert jfs.path.lexists(filename3) is True
    jfs.rmdir(dirname)
    assert jfs.path.lexists(filename3) is True
    jfs.unlink(filename3)
    assert jfs.path.lexists(filename3) is False


def test_access_dir(jfs, dirname):
    jfs.mkdir(dirname)
    assert jfs.access(dirname, os.R_OK) is True
    assert jfs.access(dirname, os.W_OK) is True
    assert jfs.access(dirname, os.X_OK) is True

    jfs.chmod(dirname, 0o444)  # readonly
    assert jfs.access(dirname, os.W_OK) is False
    assert jfs.access(dirname, os.X_OK) is False


def test_access_file(jfs, filename):
    jfs.create(filename)
    assert jfs.access(filename, os.R_OK) is True
    assert jfs.access(filename, os.W_OK) is True
    assert jfs.access(filename, os.X_OK) is True

    jfs.chmod(filename, 0o444)  # readonly
    assert jfs.access(filename, os.W_OK) is False
    assert jfs.access(filename, os.X_OK) is False


def test_access_follow_symlinks(jfs, filename, filename2):
    jfs.symlink(filename, filename2)
    assert jfs.access(filename2, os.R_OK) is False
    assert jfs.access(filename2, os.W_OK) is False
    assert jfs.access(filename2, os.X_OK) is False

    jfs.create(filename)
    assert jfs.access(filename2, os.R_OK) is True
    assert jfs.access(filename2, os.W_OK) is True
    assert jfs.access(filename2, os.X_OK) is True


def test_scandir(jfs, filename, filename2, dirname):
    jfs.symlink(filename, filename2)
    jfs.mkdir(dirname)

    entries = list(jfs.scandir("/"))
    assert len(entries) == 2

    for entry in entries:
        if entry.path == filename2:
            assert entry.is_file() is False
            assert entry.is_symlink() is True
        elif entry.path == dirname:
            assert entry.is_dir() is True
            assert entry.is_symlink() is False
        else:
            assert False, entry


def test_scandir_follow_symlinks(jfs, filename, filename2, dirname):
    jfs.create(filename)
    jfs.symlink(filename, filename2)
    jfs.mkdir(dirname)

    entries = list(jfs.scandir("/"))
    assert len(entries) == 3

    for entry in entries:
        if entry.path == filename:
            assert entry.is_file() is True
            assert entry.is_symlink() is False
        elif entry.path == filename2:
            assert entry.is_file() is False
            assert entry.is_symlink() is True
        elif entry.path == dirname:
            assert entry.is_dir() is True
            assert entry.is_symlink() is False
        else:
            assert False, entry


def test_listdir(jfs, filename, filename2, dirname):
    jfs.create(filename)
    jfs.symlink(filename, filename2)
    jfs.mkdir(dirname)

    names = list(jfs.listdir("/"))
    assert len(names) == 3
    assert set(names) == set(
        [
            filename[1:],
            filename2[1:],
            dirname[1:],
        ]
    )


def test_walk(jfs, dirname):
    jfs.mkdir(dirname)
    jfs.create(Path(os.path.join(dirname, "file")).as_posix())
    jfs.mkdir(Path(os.path.join(dirname, "dir")).as_posix())
    jfs.symlink(
        Path(os.path.join(dirname, "file")).as_posix(),
        Path(os.path.join(dirname, "dir", "link")).as_posix(),
    )

    assert list(jfs.walk(dirname)) == [
        (dirname, ["dir"], ["file"]),
        (Path(os.path.join(dirname, "dir")).as_posix(), [], ["link"]),
    ]

    assert list(jfs.walk(dirname, topdown=False)) == [
        (Path(os.path.join(dirname, "dir")).as_posix(), [], ["link"]),
        (dirname, ["dir"], ["file"]),
    ]


def test_isfile(jfs, filename, filename2, dirname):
    assert jfs.path.isfile(filename) is False
    assert jfs.path.isfile(filename2) is False
    assert jfs.path.isfile(dirname) is False

    jfs.symlink(filename, filename2)
    assert jfs.path.isfile(filename2) is False

    jfs.create(filename)
    assert jfs.path.isfile(filename) is True
    assert jfs.path.isfile(filename2) is True

    jfs.mkdir(dirname)
    assert jfs.path.isfile(dirname) is False


def test_isdir(jfs, filename, filename2, dirname):
    assert jfs.path.isdir(dirname) is False
    assert jfs.path.isdir(filename) is False
    assert jfs.path.isdir(filename2) is False

    jfs.symlink(dirname, filename2)
    assert jfs.path.isdir(filename2) is False
    jfs.mkdir(dirname)
    assert jfs.path.isdir(dirname) is True
    assert jfs.path.isdir(dirname + "/") is True
    assert jfs.path.isdir(filename2) is True


def test_islink(jfs, filename, filename2, filename3, dirname):
    assert jfs.path.islink(filename2) is False

    jfs.create(filename)
    jfs.symlink(filename, filename2)
    assert jfs.path.islink(filename2) is True

    jfs.unlink(filename2)
    assert jfs.path.islink(filename2) is False

    jfs.mkdir(dirname)
    jfs.symlink(dirname, filename2)
    assert jfs.path.islink(filename2) is True
    assert jfs.path.islink(filename3) is False

    jfs.symlink(filename2, filename3)
    assert jfs.path.islink(filename3) is True


def test_getatime(jfs, filename):
    start = int(time.time())
    jfs.create(filename)
    stop = int(time.time())
    assert start <= int(jfs.path.getatime(filename)) <= stop

    start = int(time.time())
    jfs.close(jfs.open(filename, os.O_RDONLY))
    stop = int(time.time())
    assert start <= int(jfs.path.getatime(filename)) <= stop


def test_getmtime(jfs, filename):
    start = int(time.time())
    jfs.create(filename)
    stop = int(time.time())
    assert start <= int(jfs.path.getmtime(filename)) <= stop

    start = int(time.time())
    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT)
    jfs.close(fd)
    stop = int(time.time())
    assert start <= int(jfs.path.getmtime(filename)) <= stop


def test_getsize(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT)
    jfs.close(fd)
    assert jfs.path.getsize(filename) == len(CONTENT)

    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT2)
    jfs.close(fd)
    assert jfs.path.getsize(filename) == len(CONTENT2)


def test_fdopen(jfs, filename):
    flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
    fd = jfs.open(filename, flags)
    with jfs.fdopen(fd) as fp:
        fp.write(b"text")

    flags = os.O_RDONLY
    fd = jfs.open(filename, flags)
    with jfs.fdopen(fd) as fp:
        assert fp.read() == b"text"

    flags = os.O_RDWR
    fd = jfs.open(filename, flags)
    with jfs.fdopen(fd) as fp:
        assert fp.read() == b"text"
        fp.write(b"/text")

    flags = os.O_RDONLY
    fd = jfs.open(filename, flags)
    with jfs.fdopen(fd) as fp:
        assert fp.read() == b"text/text"


def test_readlink(jfs, filename, filename2, dirname):
    jfs.mkdir(dirname)
    jfs.symlink("." + filename, filename2)

    assert jfs.readlink(filename2) == "." + filename


def test_truncate(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT)
    jfs.close(fd)
    length = int(random.random() * len(CONTENT))
    jfs.truncate(filename, length)
    assert jfs.path.getsize(filename) == length

    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT2)
    jfs.close(fd)
    length2 = int(random.random() * len(CONTENT2))
    jfs.truncate(filename, length2)
    assert jfs.path.getsize(filename) == length2


def test_ftruncate(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT)
    length = int(random.random() * len(CONTENT))
    jfs.flush(fd)
    jfs.ftruncate(fd, length)
    jfs.close(fd)
    assert jfs.path.getsize(filename) == length

    fd = jfs.open(filename, os.O_WRONLY)
    jfs.write(fd, CONTENT2)
    length2 = int(random.random() * len(CONTENT2))
    jfs.flush(fd)
    jfs.ftruncate(fd, length2)
    jfs.close(fd)
    assert jfs.path.getsize(filename) == length2


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows can't use os.chmod() to change any file mode we want",
)
def test_stat_file(jfs, filename, os_filename):
    jfs.create(filename, 0o644)

    with open(os_filename, "wb"):
        pass

    os.chmod(os_filename, 0o644)
    assert os.stat(os_filename).st_mode == jfs.stat(filename).st_mode

    os.chmod(os_filename, 0o755)
    jfs.chmod(filename, 0o755)
    assert os.stat(os_filename).st_mode == jfs.stat(filename).st_mode


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows can't use os.chmod() to change any file mode we want",
)
def test_stat_dir(jfs, dirname, os_dirname):
    jfs.mkdir(dirname)
    os.mkdir(os_dirname)
    os.chmod(os_dirname, 0o644)
    jfs.chmod(dirname, 0o644)
    assert os.stat(os_dirname).st_mode == jfs.stat(dirname).st_mode

    os.chmod(os_dirname, 0o755)
    jfs.chmod(dirname, 0o755)
    assert os.stat(os_dirname).st_mode == jfs.stat(dirname).st_mode


def test_stat_link(jfs, filename, filename2, filename3, dirname):
    jfs.create(filename, 0o644)
    jfs.symlink(filename, filename2)

    assert jfs.stat(filename2) == jfs.stat(filename)

    jfs.chmod(filename, 0o755)
    assert jfs.stat(filename2) == jfs.stat(filename)

    jfs.mkdir(dirname)
    jfs.symlink(dirname, filename3)
    assert jfs.stat(filename3) == jfs.stat(dirname)

    jfs.chmod(dirname, 0o644)
    assert jfs.stat(filename3) == jfs.stat(dirname)

    jfs.chmod(dirname, 0o755)
    assert jfs.stat(filename3) == jfs.stat(dirname)


def test_lstat_link(jfs, filename, filename2):
    jfs.symlink(filename, filename2)
    assert int(oct(jfs.lstat(filename2).st_mode)[-3:], 8) == 0o644


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows can't use os.chmod() to change any file mode we want",
)
def test_lstat_file(jfs, filename, os_filename):
    jfs.create(filename, 0o644)

    with open(os_filename, "wb"):
        pass

    os.chmod(os_filename, 0o644)
    assert os.lstat(os_filename).st_mode == jfs.lstat(filename).st_mode

    os.chmod(os_filename, 0o755)
    jfs.chmod(filename, 0o755)
    assert os.lstat(os_filename).st_mode == jfs.lstat(filename).st_mode


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows can't use os.chmod() to change any file mode we want",
)
def test_lstat_dir(jfs, dirname, os_dirname):
    jfs.mkdir(dirname)
    os.mkdir(os_dirname)
    os.chmod(os_dirname, 0o644)
    jfs.chmod(dirname, 0o644)
    assert os.lstat(os_dirname).st_mode == jfs.lstat(dirname).st_mode

    os.chmod(os_dirname, 0o755)
    jfs.chmod(dirname, 0o755)
    assert os.lstat(os_dirname).st_mode == jfs.lstat(dirname).st_mode


def test_chmod(jfs, filename, dirname, filename2):
    jfs.create(filename)
    for mode in range(1, 0o777 + 1):
        jfs.chmod(filename, mode)
        assert int(oct(jfs.stat(filename).st_mode)[-3:], 8) == mode

    jfs.mkdir(dirname)
    for mode in range(1, 0o777 + 1):
        jfs.chmod(dirname, mode)
        assert int(oct(jfs.stat(dirname).st_mode)[-3:], 8) == mode

    jfs.symlink(filename, filename2)
    link_mode = int(oct(jfs.lstat(filename2).st_mode)[-3:], 8)
    for mode in range(1, 0o777 + 1):
        jfs.chmod(filename2, mode)
        assert int(oct(jfs.stat(filename2).st_mode)[-3:], 8) == mode
        assert int(oct(jfs.lstat(filename2).st_mode)[-3:], 8) == link_mode


def test_lseek(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.O_WRONLY)
    l = jfs.write(fd, CONTENT)
    assert l == len(CONTENT)
    assert jfs.lseek(fd, 0, os.SEEK_CUR) == len(CONTENT)

    l = jfs.write(fd, CONTENT)
    assert l == len(CONTENT)
    assert jfs.lseek(fd, 0, os.SEEK_CUR) == len(2 * CONTENT)

    # test seek_set
    for i in range(len(3 * CONTENT)):
        pos = jfs.lseek(fd, i, os.SEEK_SET)
        assert jfs.lseek(fd, 0, os.SEEK_CUR) == pos
        assert jfs.lseek(fd, 0, os.SEEK_CUR) == i

    # test seek_cur
    jfs.lseek(fd, 0, os.SEEK_SET)
    pos = 0
    for i in range(10):
        offset = random.randint(-len(CONTENT), len(CONTENT))
        if offset + pos < 0:
            jfs.lseek(fd, 0, os.SEEK_SET)
            pos = 0
            continue

        pos_now = jfs.lseek(fd, offset, os.SEEK_CUR)
        assert jfs.lseek(fd, 0, os.SEEK_CUR) == pos_now
        assert pos + offset == pos_now
        pos = pos_now

    jfs.flush(fd)
    jfs.fsync(fd)

    l = jfs.lseek(fd, 0, os.SEEK_END)

    assert l == len(2 * CONTENT)
    assert jfs.lseek(fd, 0, os.SEEK_CUR) == len(2 * CONTENT)
    assert jfs.lseek(fd, 0, os.SEEK_END) == len(2 * CONTENT)


def test_flush(jfs, filename):
    jfs.create(filename)
    fdw = jfs.open(filename, os.O_WRONLY)
    jfs.write(fdw, CONTENT)
    jfs.flush(fdw)

    fdr = jfs.open(filename, os.O_RDONLY)
    assert jfs.read(fdr, len(CONTENT)) == CONTENT
    jfs.close(fdr)

    jfs.write(fdw, CONTENT[::-1])
    jfs.flush(fdw)

    fdr = jfs.open(filename, os.O_RDONLY)
    assert jfs.read(fdr, 2 * len(CONTENT)) == CONTENT + CONTENT[::-1]
    jfs.close(fdr)
    jfs.close(fdw)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="jfs.concat() will raise FileNotFoundError on Windows",
)
def test_concat(jfs, filename, filename2, filename3):
    jfs.create(filename)
    jfs.create(filename2)
    jfs.create(filename3)

    fdw = jfs.open(filename, os.O_WRONLY)
    jfs.write(fdw, CONTENT)
    jfs.close(fdw)

    fdw = jfs.open(filename2, os.O_WRONLY)
    jfs.write(fdw, CONTENT)
    jfs.close(fdw)

    jfs.concat(filename3, filename2, filename)

    fdr = jfs.open(filename3, os.O_RDONLY)
    size = jfs.path.getsize(filename3)
    assert jfs.read(fdr, size) == CONTENT * 2
    jfs.close(fdr)


def test_summary(jfs, dirname):
    jfs.mkdir(dirname)
    summary = jfs.summary(dirname)

    assert summary.size == 0
    assert summary.files == 0
    assert summary.dirs == 1

    jfs.mkdir(Path(os.path.join(dirname, "dir")).as_posix())
    jfs.create(Path(os.path.join(dirname, "dir", "file")).as_posix())
    jfs.create(Path(os.path.join(dirname, "file")).as_posix())

    fdw = jfs.open(Path(os.path.join(dirname, "file")).as_posix(), os.O_WRONLY)
    jfs.write(fdw, CONTENT)
    jfs.close(fdw)

    fdw = jfs.open(Path(os.path.join(dirname, "dir", "file")).as_posix(), os.O_WRONLY)
    jfs.write(fdw, CONTENT)
    jfs.close(fdw)

    summary = jfs.summary(dirname)

    assert summary.size == 8
    assert summary.files == 2
    assert summary.dirs == 2


def test_read_content_with_zero(jfs, filename):
    CONTENT_WITH_ZERO = b"\x05\x00\x00\x00\x00\x00\x00\x00\x98\x00\x00\x00\x00\x00\x00\x00-\x01\x00\x00\x00\x00\x00\x00\xc2\x01\x00\x00\x00\x00\x00\x00W\x02\x00\x00\x00\x00\x00\x00\xec\x02\x00\x00\x00\x00\x00\x00\x81\x03\x00\x00\x00\x00\x00\x00\x16\x04\x00\x00\x00\x00\x00\x00\xab\x04\x00\x00\x00\x00\x00\x00@\x05\x00\x00\x00\x00\x00\x00\xd5\x05\x00\x00\x00\x00\x00\x00j\x06\x00\x00\x00\x00\x00\x00\xff\x06\x00\x00\x00\x00\x00\x00\x94\x07\x00\x00\x00\x00\x00\x00)\x08\x00\x00\x00\x00\x00\x00\xbe\x08\x00\x00\x00\x00\x00\x00S\t\x00\x00\x00\x00\x00\x00\xe8\t\x00\x00\x00\x00\x00\x00}\n\x00\x00\x00\x00\x00\x00\x12\x0b\x00\x00\x00\x00\x00\x00\xa7\x0b\x00\x00\x00\x00\x00\x00<\x0c\x00\x00\x00\x00\x00\x00\xd1\x0c\x00\x00\x00\x00\x00\x00f\r\x00\x00\x00\x00\x00\x00\xfb\r\x00\x00\x00\x00\x00\x00\x90\x0e\x00\x00\x00\x00\x00\x00%\x0f\x00\x00\x00\x00\x00\x00\xba\x0f\x00\x00\x00\x00\x00\x00O\x10\x00\x00\x00\x00\x00\x00\xe4\x10\x00\x00\x00\x00\x00\x00y\x11\x00\x00\x00\x00\x00\x00\x0e\x12\x00\x00\x00\x00\x00\x00\xa1\x12\x00\x00\x00\x00\x00\x006\x13\x00\x00\x00\x00\x00\x00\xcb\x13\x00\x00\x00\x00\x00\x00`"
    jfs.create(filename)
    fdw = jfs.open(filename, os.O_WRONLY)
    content_len = jfs.write(fdw, CONTENT_WITH_ZERO)
    assert content_len == len(CONTENT_WITH_ZERO)
    jfs.close(fdw)

    fdr = jfs.open(filename, os.O_RDONLY)
    assert jfs.read(fdr, 7) == CONTENT_WITH_ZERO[:7]
    assert jfs.read(fdr, len(CONTENT_WITH_ZERO) + 10) == CONTENT_WITH_ZERO[7:]
    jfs.close(fdr)

    from juicefs.io import open as _jfs_open

    with _jfs_open(jfs, filename, "rb") as f:
        f.read() == CONTENT_WITH_ZERO


# TODO: read-write mode not supported in this version
# def test_read_write_wbp(jfs, filename):
#     TEXT = b"hello world"
#     jfs.create(filename)
#     fdw = jfs.open(filename, os.O_WRONLY)
#     jfs.write(fdw, TEXT)
#     jfs.close(fdw)

#     fd = jfs.open(filename, os.O_RDWR)
#     assert jfs.read(fd, 6) == TEXT[:6]
#     jfs.write(fd, TEXT[::-1])
#     jfs.flush(fd)

#     jfs.lseek(fd, 0, os.SEEK_SET)

#     assert jfs.read(fd, 2 * len(TEXT)) == TEXT[:6] + TEXT[::-1]


# TODO: chown() 目前无法使用，没搞懂它的行为，只会抛 Permission denied
# def test_chown(jfs, filename, dirname):
#     jfs.create(filename)

#     new_user = "new_user"
#     new_group = "new_group"
#     origin_user = jfs.stat(filename).st_uid
#     origin_group = jfs.stat(filename).st_gid

#     assert origin_user != new_user
#     assert origin_group != new_group

#     jfs.chown(filename, origin_user, new_group)
#     assert jfs.stat(filename).st_gid == new_group
#     assert jfs.stat(filename).st_uid == origin_user

#     jfs.chown(filename, origin_user, origin_group)
#     assert jfs.stat(filename).st_gid == origin_group
#     assert jfs.stat(filename).st_uid == origin_user

#     jfs.chown(filename, new_user, origin_group)
#     assert jfs.stat(filename).st_gid == origin_group
#     assert jfs.stat(filename).st_uid == new_user

#     jfs.chown(filename, origin_user, origin_group)
#     assert jfs.stat(filename).st_gid == origin_group
#     assert jfs.stat(filename).st_uid == origin_user

#     jfs.chown(filename, new_user, origin_group)
#     assert jfs.stat(filename).st_gid == origin_group
#     assert jfs.stat(filename).st_uid == new_user
