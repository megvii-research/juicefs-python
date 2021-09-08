import io
import os
import sys

import pytest

from juicefs.io import FileIO, open

CONTENT = b"block0\n block1\n block2"


def remove_file(jfs, path):
    if jfs.path.isfile(path):
        jfs.unlink(path)


def create_tempfile(jfs, path):
    remove_file(jfs, path)
    yield path
    remove_file(jfs, path)


@pytest.fixture()
def filename(jfs):
    yield from create_tempfile(jfs, "/test.file")


def test_fileio_close(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.W_OK)
    fio = FileIO(jfs, fd)
    assert fio.closed is False
    assert repr(fio) == "<juicefs.io.FileIO name='/test.file' mode='rb+'>"

    fio.close()

    assert fio.closed is True
    assert repr(fio) == '<juicefs.io.FileIO [closed]>'


def remove_local(path):
    if os.path.isfile(path):
        os.unlink(path)


def test_fileio_del(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.W_OK)
    fio = FileIO(jfs, fd)
    assert fio.closed is False

    with pytest.warns(ResourceWarning):
        del fio


def test_pickle(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.W_OK)
    fio = FileIO(jfs, fd)

    import pickle
    with pytest.raises(TypeError):
        pickle.dumps(fio)


@pytest.fixture()
def local_filename():
    path = "/tmp/test.file"
    if sys.platform == "win32":
        path = os.path.join(__file__, "..", "tmp", "test.file")
    remove_local(path)
    yield path
    remove_local(path)


def test_fileio_close_wb(jfs, filename):
    writer = open(jfs, filename, "wb")
    assert writer.closed is False
    assert repr(writer) == "<BufferedWriter name='/test.file'>"
    assert writer.mode == "wb"

    writer.close()

    assert writer.closed is True


def test_fileio_close_rb(jfs, filename):
    open(jfs, filename, "wb").close()
    reader = open(jfs, filename, "rb")
    assert reader.closed is False
    assert repr(reader) == "<_io.BufferedReader name='/test.file'>"
    assert reader.mode == "rb"

    reader.close()

    assert reader.closed is True


def test_fileio_read(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.W_OK)
    jfs.write(fd, CONTENT)
    jfs.close(fd)

    with open(jfs, filename, "rb") as reader:
        assert reader.readline() == b"block0\n"
        assert reader.read() == b" block1\n block2"

    with open(jfs, filename, "rb") as reader:
        assert reader.read(5) == CONTENT[:5]


def test_reader_unwritable(jfs, filename):
    jfs.create(filename)
    fd = jfs.open(filename, os.W_OK)
    jfs.close(fd)
    with open(jfs, filename, "rb") as reader:
        with pytest.raises(io.UnsupportedOperation):
            reader.write(b'test')


def test_fileio_write(jfs, filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(CONTENT)

    fd = jfs.open(filename, os.R_OK)
    content = jfs.read(fd, len(CONTENT))
    assert content == CONTENT

    with open(jfs, filename, "rb") as reader:
        assert reader.readline() == b"block0\n"
        assert reader.read() == b" block1\n block2"

    with open(jfs, filename, "rb") as reader:
        assert reader.read(5) == CONTENT[:5]


def test_writer_unreadable(jfs, filename):
    with open(jfs, filename, "wb") as writer:
        with pytest.raises(io.UnsupportedOperation):
            writer.read()


def test_mode(jfs, filename):
    with open(jfs, filename, "xb") as writer:
        assert writer.mode == "xb"
    remove_file(jfs, filename)
    with open(jfs, filename, "xb+") as writer:
        assert writer.mode == "xb+"
    with open(jfs, filename, "ab") as writer:
        assert writer.mode == "ab"
    with open(jfs, filename, "ab+") as writer:
        assert writer.mode == "ab+"


def test_open_pandora_box(jfs, filename):
    with pytest.raises(TypeError):
        open(jfs, 0xbad)
    with pytest.raises(TypeError):
        open(jfs, filename, mode=0xbad)
    with pytest.raises(TypeError):
        open(jfs, filename, buffering='bad')
    with pytest.raises(TypeError):
        open(jfs, filename, encoding=0xbad)
    with pytest.raises(TypeError):
        open(jfs, filename, errors=0xbad)
    with pytest.raises(ValueError):
        open(jfs, filename, mode="bad")
    with open(jfs, filename, "wb") as writer:
        pass
    with pytest.warns(DeprecationWarning):
        open(jfs, filename, mode="Urb")
    for mode in ["rrr", "Uw", "tb", "xrwa", "b"]:
        with pytest.raises(ValueError):
            open(jfs, filename, mode=mode)
    with pytest.raises(ValueError):
        open(jfs, filename, mode="wb", encoding="utf8")
    with pytest.raises(ValueError):
        open(jfs, filename, mode="wb", errors="ignore")
    with pytest.raises(ValueError):
        open(jfs, filename, mode="wb", newline="\r\n")


def test_open_text(jfs, filename):
    with open(jfs, filename, mode="tw", encoding="utf8") as writer:
        writer.write("hello")


def test_fileio_append(jfs, filename):
    with open(jfs, filename, "ab") as writer:
        writer.write(CONTENT)

    with open(jfs, filename, "ab") as writer:
        writer.write(CONTENT)

    with open(jfs, filename, "rb") as reader:
        assert reader.read() == CONTENT * 2

    with open(jfs, filename, "rb") as reader:
        assert reader.read(20) == (CONTENT * 2)[:20]


def test_fileio_flush(jfs, filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(CONTENT)
        writer.flush()
        with open(jfs, filename, "rb") as reader:
            assert reader.read() == CONTENT
        writer.write(CONTENT[::-1])
        writer.flush()
        with open(jfs, filename, "rb") as reader:
            assert reader.read() == CONTENT + CONTENT[::-1]


def test_truncate(jfs, filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(b"hello")

    with open(jfs, filename, "wb") as writer:
        writer.truncate()

    with open(jfs, filename, "rb") as reader:
        assert reader.read() == b""


def write_no_assert(fp1, fp2, buffer):
    fp1.write(buffer)
    fp2.write(buffer)


def test_seek_write(jfs, filename, local_filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "wb") as fp1, open(jfs, filename, "wb") as fp2:
        assert_ability(fp1, fp2)
        write_no_assert(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 0)
        write_no_assert(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 1)
        write_no_assert(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 2)
        write_no_assert(fp1, fp2, CONTENT)

    with io.open(local_filename, "rb") as fp1, open(jfs, filename, "rb") as fp2:
        assert fp1.read() == fp2.read()


def assert_ability(fp1, fp2):
    assert fp1.seekable() == fp2.seekable()
    assert fp1.readable() == fp2.readable()
    assert fp1.writable() == fp2.writable()


def assert_read(fp1, fp2, size):
    assert fp1.read(size) == fp2.read(size)


def assert_seek(fp1, fp2, cookie, whence):
    fp1.seek(cookie, whence)
    fp2.seek(cookie, whence)
    assert fp1.tell() == fp2.tell()


def load_content(fp):
    print("call flush in load_content")
    fp.flush()
    if isinstance(fp.raw, FileIO):
        with open(fp.raw._jfs, fp.name, "rb") as fpr:
            return fpr.read()
    with io.open(fp.name, "rb") as fpr:
        return fpr.read()


def assert_write(fp1, fp2, buffer):
    fp1.write(buffer)
    fp2.write(buffer)
    assert load_content(fp1) == load_content(fp2)


def test_fileio_mode_rb(jfs, filename, local_filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "rb") as fp1, open(jfs, filename, "rb") as fp2:
        assert_ability(fp1, fp2)
        assert_read(fp1, fp2, 5)
        assert_seek(fp1, fp2, 0, 0)
        assert_read(fp1, fp2, 5)
        assert_seek(fp1, fp2, 0, 1)
        assert_read(fp1, fp2, 5)
        assert_seek(fp1, fp2, 0, 2)
        assert_read(fp1, fp2, 5)

        fp2.seek(0)
        assert fp2.readline() == b"block0\n"
        assert list(fp2.readlines()) == [b" block1\n", b" block2"]

        with pytest.raises(IOError):
            fp2.write(b"")


def test_fileio_mode_wb(jfs, filename, local_filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "wb") as fp1, open(jfs, filename, "wb") as fp2:
        assert_ability(fp1, fp2)
        assert_write(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 0)
        assert_write(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 1)
        assert_write(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 2)
        assert_write(fp1, fp2, CONTENT)

        with pytest.raises(IOError):
            fp2.read()
        with pytest.raises(IOError):
            fp2.readline()
        with pytest.raises(IOError):
            fp2.readlines()


def test_fileio_mode_ab(jfs, filename, local_filename):
    with open(jfs, filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "wb") as writer:
        writer.write(CONTENT)

    with io.open(local_filename, "ab") as fp1, open(jfs, filename, "ab") as fp2:
        assert_ability(fp1, fp2)
        assert_write(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 0)
        assert_write(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 1)
        assert_write(fp1, fp2, CONTENT)
        assert_seek(fp1, fp2, 0, 2)
        assert_write(fp1, fp2, CONTENT)


# TODO: read-write mode not supported in this version
# def test_fileio_mode_rbp(jfs, filename, local_filename):
#     with open(jfs, filename, "wb") as writer:
#         writer.write(CONTENT)

#     with io.open(local_filename, "wb") as writer:
#         writer.write(CONTENT)

#     with io.open(local_filename, "rb+") as fp1, open(jfs, filename, "rb+") as fp2:
#         assert_ability(fp1, fp2)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 0)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 1)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 2)
#         assert_read(fp1, fp2, 5)


# TODO: read-write mode not supported in this version
# def test_fileio_mode_wbp(jfs, filename, local_filename):
#     with open(jfs, filename, "wb") as writer:
#         writer.write(CONTENT)

#     with io.open(local_filename, "wb") as writer:
#         writer.write(CONTENT)

#     with io.open(local_filename, "wb+") as fp1, open(jfs, filename, "wb+") as fp2:
#         assert_ability(fp1, fp2)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 0)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 1)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 2)
#         assert_read(fp1, fp2, 5)


# TODO: 'a' mode not implemented
# def test_s3_cached_handler_mode_abp(jfs, filename, local_filename):
#     with open(jfs, filename, "wb") as writer:
#         writer.write(CONTENT)

#     with io.open(local_filename, "wb") as writer:
#         writer.write(CONTENT)

#     with io.open(local_filename, "ab+") as fp1, open(jfs, filename, "ab+") as fp2:
#         assert_ability(fp1, fp2)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 0)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 1)
#         assert_read(fp1, fp2, 5)
#         assert_write(fp1, fp2, CONTENT)
#         assert_seek(fp1, fp2, 0, 2)
#         assert_read(fp1, fp2, 5)
