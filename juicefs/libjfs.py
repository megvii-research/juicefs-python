import getpass
import json
import os
import stat
import struct
from ctypes import CDLL
from io import BytesIO
from threading import current_thread
from typing import Callable, List, Optional

from juicefs.utils import check_juicefs_error


def read_cstring(buffer: BytesIO) -> bytearray:
    res = bytearray()
    while True:
        b = buffer.read(1)
        if not b:
            return res
        c = ord(b)
        if c == 0:
            break
        res.append(c)
    return res


def parse_stat_mode(mode: int) -> int:
    # https://github.com/juicedata/juicefs/blob/main/pkg/fs/fs.go#L78
    #   func (fs *FileStat) Mode() os.FileMode
    # https://golang.org/pkg/io/fs/#FileMode
    res = mode & 0o777
    if mode & (1 << 31):  # ModeDir
        res |= stat.S_IFDIR
    elif mode & (1 << 27):  # ModeSymlink
        res |= stat.S_IFLNK
    else:
        res |= stat.S_IFREG
    if mode & (1 << 23):  # ModeSetuid
        res |= stat.S_ISUID
    if mode & (1 << 22):  # ModeSetgid
        res |= stat.S_ISGID
    if mode & (1 << 20):  # ModeSticky
        res |= stat.S_ISVTX
    return res


def parse_xattrs(data: bytes, length: int) -> List[str]:
    res = []
    buffer = BytesIO(data)
    while buffer.tell() < length:
        res.append(read_cstring(buffer).decode())
    return res


def create_stat_result(data: bytes, length: int) -> os.stat_result:
    buffer = BytesIO(data)
    mode, size, mtime, atime = struct.unpack("<LQQQ", buffer.read(28))
    mtime = mtime / 1000
    atime = atime / 1000
    mode = parse_stat_mode(mode)
    user = read_cstring(buffer).decode()
    group = read_cstring(buffer).decode()
    inode, dev, nlink, ctime = 0, 0, 0, 0
    if buffer.tell() != length:
        raise ValueError("unknown stat result format: %r" % data)
    return os.stat_result(
        (
            mode,
            inode,
            dev,
            nlink,
            user,
            group,
            size,
            atime,
            mtime,
            ctime,  # pytype: disable=wrong-arg-types
        )
    )


def create_statvfs_result(data: bytes) -> os.statvfs_result:
    blocks, bavail = struct.unpack("<QQ", data)
    bfree = blocks - bavail
    # bsize = 4096 * 2**10  # 4MB in default
    bsize, frsize, files, ffree, favail, flag, namemax = 1, 0, 0, 0, 0, 0, 255
    return os.statvfs_result(
        (
            bsize,
            frsize,
            blocks,
            bfree,
            bavail,
            files,
            ffree,
            favail,
            flag,
            namemax,
        )
    )


def create_summary(data: bytes):
    size, files, dirs = struct.unpack("<QQQ", data)
    return DirSummary(size, files, dirs)


class DirEntry:

    _stat: os.stat_result
    root: str
    name: str

    def __init__(self, name: str, root: str, stat: os.stat_result):
        self.name = name
        self.root = root
        self._stat = stat

    def __repr__(self):
        return "<DirEntry %r>" % self.name

    @property
    def path(self):
        return os.path.join(self.root, self.name)

    def inode(self):
        return self._stat.st_ino

    def is_dir(self):
        return stat.S_ISDIR(self._stat.st_mode)

    def is_file(self):
        return stat.S_ISREG(self._stat.st_mode)

    def is_symlink(self):
        return stat.S_ISLNK(self._stat.st_mode)

    def stat(self):
        return self._stat


class DirSummary:

    size: int
    files: int
    dirs: int

    def __init__(self, size: int, files: int, dirs: int):
        self.size = size
        self.files = files
        self.dirs = dirs

    def __repr__(self):
        return "<DirSummary size=%d files=%d dirs=%d>" % (
            self.size,
            self.files,
            self.dirs,
        )


class LibJuiceFSFunction:
    def __init__(self, func: Callable, handle: int, nargs: Optional[int] = None):
        self._func = func
        self._handle = handle
        self._nargs = nargs

    @property
    def _ident(self) -> int:
        return current_thread().ident

    def __call__(self, *args):
        jfs_func = self._func
        jfs_args = [self._ident, self._handle]
        for arg in args:
            if isinstance(arg, str):
                arg = arg.encode()
            jfs_args.append(arg)
        code = jfs_func(*jfs_args)
        if self._nargs is not None:
            check_juicefs_error(code, *args[: self._nargs])
        return code

    def __getitem__(self, nargs: int):
        return LibJuiceFSFunction(self._func, self._handle, nargs)


class LibJuiceFSHandle:
    def __init__(self, lib, handle: int):
        self._lib = lib
        self._handle = handle

    def __getattr__(self, name: str):
        func = getattr(self._lib, "jfs_%s" % name)
        return LibJuiceFSFunction(func, self._handle)


class LibJuiceFS(LibJuiceFSHandle):
    def __init__(self, path, name: str, config: dict):
        self._lib = CDLL(path)
        self._handle = self.init(name, config)

    def init(self, name: str, config: dict):
        handle = self._lib.jfs_init(
            name.encode(),  # name
            json.dumps(config).encode(),  # conf
            getpass.getuser().encode(),  # user
            b"nogroup",  # group
            b"root",  # superuser
            b"nogroup",  # supergroup
        )
        if handle <= 0:
            raise IOError("JuiceFS initialized failed for jfs://%s" % name)
        return handle

    def __getitem__(self, handle: int):
        return LibJuiceFSHandle(self._lib, handle)

    def __del__(self):
        if hasattr(self, "_handle"):
            self.term()
