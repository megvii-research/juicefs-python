import errno
import os
import posixpath
import stat
import struct
import time
from ctypes import create_string_buffer
from io import BytesIO
from typing import Dict, Iterator, List, Optional, Tuple, Union

from juicefs.io import FileIO
from juicefs.libjfs import (
    DirEntry,
    LibJuiceFS,
    create_stat_result,
    create_statvfs_result,
    create_summary,
    parse_xattrs,
    read_cstring,
)
from juicefs.utils import check_juicefs_error, create_os_error

DEFAULT_FILE_MODE = 0o777
DEFAULT_DIRECOTRY_MODE = 0o777
DEFAULT_CONFIG = {
    "accessLog": "",
    "autoCreate": True,
    "cacheDir": "memory",
    "cacheFullBlock": True,
    "cacheSize": 100,
    "debug": True,
    "fastResolve": True,
    "freeSpace": "0.1",
    "getTimeout": 5,
    "maxUploads": 20,
    "memorySize": 300,
    "meta": "",
    "noUsageReport": True,
    "opencache": False,
    # "openCache": 0.0,  # v0.15.0 变成了 float
    "prefetch": 1,
    "pushAuth": "",
    "pushGateway": "",
    "pushInterval": 10,
    "putTimeout": 60,
    "readahead": 0,
    "readOnly": False,
    "uploadLimit": 0,
    "writeback": False,
}


def juicefs_stat(stat_func, path):
    buf = create_string_buffer(130)
    return buf, stat_func(path, buf)


def juicefs_stat_result(stat_func, path):
    buf, code = juicefs_stat(stat_func[1], path)
    return create_stat_result(buf.raw, code)


def juicefs_exist(stat_func, path, type_func=None):
    buf, code = juicefs_stat(stat_func, path)
    if code < 0:
        return False
    if type_func is None:
        return True
    st = create_stat_result(buf.raw, code)
    return type_func(st.st_mode)


class JuiceFS:
    def __init__(
        self,
        name: str,
        config: Dict[str, Union[str, bool, int, float]] = {},
    ):
        """JuiceFS Session

        :param str name: Redis URI used for this session
        :param dict config: JuiceFS configuration, available keys: https://github.com/juicedata/juicefs/blob/main/sdk/java/libjfs/main.go#L215
        """
        jfs_config = DEFAULT_CONFIG.copy()
        jfs_config.update(config)
        path = os.path.normpath(os.path.join(__file__, "..", "lib", "libjfs.so"))

        self._lib = LibJuiceFS(path, name, jfs_config)
        self._name = name
        self._config = config
        self._fds = {}  # type: Dict[int, Tuple[str, int, int]]
        self.path = JuiceFSPath(self._lib)

        # TODO: remove this
        # https://github.com/juicedata/juicefs/issues/646
        self._flens = {}  # type: Dict[int, int]

    def _fetch_path_by_fd(
        self, fd: int
    ) -> Tuple[str, int, int]:  # (name, py_flags, jfs_flags)
        if fd not in self._fds:
            raise create_os_error(errno.EBADF)
        return self._fds[fd]

    def statvfs(self) -> os.statvfs_result:
        """Return an os.statvfs_result object.

        The return value is an object whose attributes describe the filesystem
        on the given path, and correspond to the members of the statvfs structure,
        namely:

            f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail, f_flag, f_namemax.
        """
        buf = create_string_buffer(16)
        self._lib.statvfs(buf)
        return create_statvfs_result(buf.raw)

    def summary(self, path: str):
        """Returns a juicefs.libjfs.DirSummary object, which contains number of size,
        files and dirs on the path.
        """
        buf = create_string_buffer(24)
        self._lib.summary[1](path, buf)
        return create_summary(buf.raw)

    def mkdir(self, path: str, mode: int = DEFAULT_DIRECOTRY_MODE):
        """Create a directory named *path* with numeric mode *mode*.

        If the directory already exists, FileExistsError is raised.
        """
        self._lib.mkdir[1](path, mode)

    def makedirs(
        self, path: str, mode: int = DEFAULT_DIRECOTRY_MODE, exist_ok: bool = False
    ):
        """Recursive directory creation function. Like mkdir(), but makes all
        intermediate-level directories needed to contain the leaf directory.

        The *mode* parameter is passed to mkdir(); see the mkdir() description for
        how it is interpreted.
        If *exist_ok* is False (the default), an OSError is raised if the target
        directory already exists.
        """
        code = self._lib.mkdir(path, mode)
        if code == -errno.EEXIST and exist_ok:
            return 0
        if code == -errno.ENOENT:
            self.makedirs(os.path.dirname(path), mode, exist_ok)
            code = self._lib.mkdir(path, mode)
        check_juicefs_error(code)

    def rmdir(self, path: str):
        """Remove (delete) the directory *path*.

        Only works when the directory is empty, otherwise, OSError is raised.
        In order to remove whole directory trees, rmtree() can be used.
        """
        if not self.path.isdir(path):
            raise create_os_error(errno.ENOTDIR, path)
        self._lib.delete[1](path)

    def removedirs(self, path: str):
        """Remove directories recursively.

        Works like rmdir() except that, if the leaf directory is successfully
        removed, removedirs() tries to successively remove every parent directory
        mentioned in *path* until an error is raised (which is ignored, because it
        generally means that a parent directory is not empty).

        For example, ``JuiceFS.removedirs('/foo/bar/baz')`` will first remove the
        directory '/foo/bar/baz', and then remove '/foo/bar' and '/foo' if they
        are empty.

        Raises OSError if the leaf directory could not be successfully removed.
        """
        self.rmdir(path)
        head, tail = posixpath.split(path)
        if not tail:
            head, tail = posixpath.split(head)
        while head and tail:
            try:
                self.rmdir(head)
            except OSError:
                break
            head, tail = posixpath.split(head)

    def scandir(self, path: str) -> Iterator[DirEntry]:
        """Return an iterator of juicefs.libjfs.DirEntry objects corresponding to
        the entries in the directory given by *path*.

        The entries are yielded in arbitrary order, and the special entries '.' and
        '..' are not included.
        """
        bufsize = 32 << 10
        buf = create_string_buffer(bufsize)
        code = self._lib.listdir(path, 0, buf, bufsize)
        while code > 0:
            buffer = BytesIO(buf.raw)
            while buffer.tell() < code:
                name = buffer.read(ord(buffer.read(1))).decode()
                length = ord(buffer.read(1))
                stat = create_stat_result(buffer.read(length), length)
                yield DirEntry(name, path, stat)
            left = struct.unpack("<I", buffer.read(4))[0]
            if left == 0:
                break
            fd = struct.unpack("<I", buffer.read(4))[0]
            code = self._lib.listdir(path, 0, fd, bufsize)
        check_juicefs_error(code, path)

    def listdir(self, path: str) -> List[str]:
        """Return a list containing the names of the entries in the directory given
        by *path*.

        The list is in arbitrary order, and does not include the special entries '.'
        and '..' even if they are present in the directory.
        """
        return list(entry.name for entry in self.scandir(path))

    def symlink(self, src_path: str, dst_path: str):
        """Create a symbolic link pointing to *src_path* named *dst_path*."""
        self._lib.symlink[2](src_path, dst_path)

    def readlink(self, path: str) -> str:
        """Return a string representing the path to which the symbolic link points.

        The result will be a relative pathname to the path of symbolic link;
        it may be converted to an absolute pathname using ``os.path.join(os.path.dirname(path), result)``.
        """
        bufsize = 4096
        buf = create_string_buffer(bufsize)
        self._lib.readlink[1](path, buf, bufsize)
        return read_cstring(BytesIO(buf.raw)).decode()

    def open(self, path: str, flags: int, mode: int = DEFAULT_FILE_MODE) -> int:  # fd
        """Open the file *path* and set various flags according to *flags* and
        possibly its mode according to *mode*.

        When computing mode, the current umask value is first masked out.

        Return the file descriptor for the newly opened file.
        """
        buf, code = juicefs_stat(self._lib.stat1, path)
        if code > 0:  # self.path.exists
            st = create_stat_result(buf.raw, code)
            if stat.S_ISDIR(st.st_mode):  # self.path.isdir
                raise create_os_error(errno.EISDIR, path)
            if flags & os.O_EXCL:
                raise create_os_error(errno.EEXIST, path)
            if flags & os.O_TRUNC:
                self.truncate(path, 0)
        else:
            if flags & os.O_CREAT:
                self.create(path, mode)

        jfs_flags = os.R_OK
        if flags & os.O_WRONLY:
            jfs_flags = os.W_OK
        elif flags & os.O_RDWR:
            jfs_flags = os.R_OK | os.W_OK

        fd = self._lib.open[1](path, jfs_flags)
        self._fds[fd] = (path, flags, jfs_flags)
        self._flens[fd] = self.path.getsize(path)
        return fd

    def close(self, fd: int):
        """Close file descriptor *fd*."""
        self._lib[fd].close[0]()

    def flush(self, fd: int):
        """Flush the write buffers of the stream if applicable. This does nothing
        for read-only and non-blocking streams.
        """
        self._lib[fd].flush[0]()

    def fsync(self, fd: int):
        """Force write of *fd* to disk."""
        self._lib[fd].fsync[0]()

    def lseek(self, fd: int, offset: int, whence: int) -> int:
        """Set the current position of file descriptor *fd* to position pos,
        modified by *whence*:

            os.SEEK_SET or 0 to set the position relative to the beginning of the file;
            os.SEEK_CUR or 1 to set it relative to the current position;
            os.SEEK_END or 2 to set it relative to the end of the file.

        Return the new cursor position in bytes, starting from the beginning.
        """
        if whence == os.SEEK_END:
            whence = os.SEEK_SET
            offset += self._flens[fd]
        return self._lib[fd].lseek[0](offset, whence)

    def read(self, fd: int, size: int) -> bytes:
        """Read at most *size* bytes from file descriptor *fd*.

        Return a bytestring containing the bytes read.

        If the end of the file referred to by fd has been reached, an empty bytes object is returned.
        """
        buf = create_string_buffer(size)
        self._lib[fd].read[0](buf, size)
        return bytes(read_cstring(BytesIO(buf.raw)))

    def pread(self, fd: int, size: int, offset: int) -> bytes:
        """Read from a file descriptor, *fd*, at a position of *offset*.

        It will read up to *size* number of bytes. The file offset remains unchanged.
        """
        buf = create_string_buffer(size)
        self._lib[fd].pread[0](buf, size, offset)
        return bytes(read_cstring(BytesIO(buf.raw)))

    def write(self, fd: int, content: bytes) -> int:
        """Write the *content* to file descriptor *fd*.

        Return the number of bytes actually written.
        """
        buf = create_string_buffer(content)
        bufsize = len(content)
        length = min(self._flens[fd], self.lseek(fd, 0, os.SEEK_CUR))
        code = self._lib[fd].write[0](buf, bufsize)
        self._flens[fd] = max(self._flens[fd], length + code)
        return code

    def create(self, path: str, mode: int = DEFAULT_FILE_MODE):
        """Create a file with with numeric mode *mode*."""
        self._lib.create[1](path, mode)

    def remove(self, path: str):
        """Remove (delete) the file path. If *path* is a directory, OSError is
        raised. Use rmdir() to remove directories.

        This function is semantically identical to unlink().
        """
        if self.path.isdir(path):
            raise create_os_error(errno.EISDIR, path)
        self._lib.delete[1](path)

    unlink = remove

    def rename(self, src_path: str, dst_path: str):
        """Rename the file or directory *src_path* to *dst_path*.

        If *dst_path* is a directory or file, OSError will be raised.
        """
        self._lib.rename[2](src_path, dst_path)

    replace = rename

    def truncate(self, path: str, length: int):
        """Truncate the file corresponding to *path*, so that it is at most *length*
        bytes in size.
        """
        self._lib.truncate[1](path, length)

    def concat(self, path: str, *other_paths: str):
        """Concat the file content of *other_paths* with *path*'s."""
        content = b""
        for other_path in other_paths:
            if not self.path.exists(other_path):
                raise create_os_error(errno.ENOENT, other_path)
            content += other_path.encode() + b"\x00"
        buf = create_string_buffer(content)
        bufsize = len(content)
        self._lib.concat[1](path, buf, bufsize)

    def delete(self, path: str):
        """Delete a file, symbolic link or empty directory."""
        # 删除一个文件，一个 symlink，或者空目录
        self._lib.delete[1](path)

    def rmtree(self, path: str):
        """Delete a file, symbolic link or recursively delete a directory."""
        # 删除一个文件，一个 symlink，或者递归删除目录
        self._lib.rmr[1](path)

    def access(self, path: str, flags: int) -> bool:
        """Use the real uid/gid to test for access to *path*.

        The *flags* can be the inclusive OR of one or more of R_OK, W_OK, and X_OK
        to test permissions.

        Return True if access is allowed, False if not.
        """
        return self._lib.access(path, flags) == 0

    def lstat(self, path: str) -> os.stat_result:
        """Similar to stat(), but does not follow symbolic links.

        Return an os.stat_result object.
        """
        return juicefs_stat_result(self._lib.lstat1, path)

    def stat(self, path: str) -> os.stat_result:
        """Get the status of a file by *path*.

        This function normally follows symlinks.

        Return an os.stat_result object.
        """
        return juicefs_stat_result(self._lib.stat1, path)

    def chmod(self, path: str, mode: int):
        """Change the mode of *path* to the numeric mode.

        *mode* may take one of values defined in the stat module or bitwise ORed
        combinations of them.
        """
        self._lib.chmod[1](path, mode)

    def chown(self, path: str, user: str, group: str):
        """Change the user and group name of path to the user and group name."""
        self._lib.setOwner[1](path, user, group)

    def utime(self, path: str, times: Optional[Tuple[float, float]] = None):
        """Set the access and modified times of the file specified by path.

        *times* should be a tuple like (atime, mtime) or None.
        if *times* is None, atime = mtime = time.time()
        """
        if times is None:
            atime = mtime = time.time()
        else:
            atime, mtime = times

        atime, mtime = int(atime * 1000), int(mtime * 1000)
        self._lib.utime[1](path, mtime, atime)

    def getxattr(self, path: str, attribute: str) -> Optional[bytes]:
        """Return the value of the extended filesystem attribute attribute for *path*.

        Return a bytes object.
        """
        bufsize = 16 << 10
        while True:
            bufsize *= 2
            buf = create_string_buffer(bufsize)
            code = self._lib.getXattr[2](path, attribute, buf, bufsize)
            if code != bufsize:
                break
        if code == -errno.EPROTONOSUPPORT or code == -errno.ENODATA:
            return None  # attr not found
        return buf.raw[:code]

    def setxattr(self, path: str, attribute: str, value: bytes, flags: int = 0):
        """Set the extended filesystem attribute *attribute* on *path* to *value*.

        *attribute* must be a *str* encoded with the filesystem encoding.
        *flags* may be XATTR_REPLACE or XATTR_CREATE.

        If XATTR_REPLACE is given and the *attribute* does not exist, EEXISTS will be raised.
        If XATTR_CREATE is given and the *attribute* already exists, the *attribute* will not be created and ENODATA will be raised.
        """
        buf = create_string_buffer(value)
        bufsize = len(value)
        self._lib.setXattr[2](path, attribute, buf, bufsize, flags)

    def removexattr(self, path: str, attribute: str):
        """Removes the extended filesystem attribute *attribute* from *path*."""
        self._lib.removeXattr[2](path, attribute)

    def listxattr(self, path: str) -> List[str]:
        """Return a list of the extended filesystem attributes on *path*."""
        bufsize = 1024
        res = []
        while True:
            bufsize *= 2
            buf = create_string_buffer(bufsize)
            code = self._lib.listXattr[1](path, buf, bufsize)
            res.extend(parse_xattrs(buf.raw, code))
            if code != bufsize:
                break
        return res

    def walk(self, top, topdown: bool = True):
        """Directory tree generator.

        For each directory in the directory tree rooted at top (including top
        itself, but excluding '.' and '..'), yields a 3-tuple (dirpath, dirnames, filenames)

        dirpath is a string, the path to the directory.  dirnames is a list of
        the names of the subdirectories in dirpath (excluding '.' and '..').
        filenames is a list of the names of the non-directory files in dirpath.
        Note that the names in the lists are just names, with no path components.
        To get a full path (which begins with top) to a file or directory in
        dirpath, do os.path.join(dirpath, name).

        If optional arg 'topdown' is true or not specified, the triple for a
        directory is generated before the triples for any of its subdirectories
        (directories are generated top down).  If topdown is false, the triple
        for a directory is generated after the triples for all of its
        subdirectories (directories are generated bottom up).

        When topdown is true, the caller can modify the dirnames list in-place
        (e.g., via del or slice assignment), and walk will only recurse into the
        subdirectories whose names remain in dirnames; this can be used to prune the
        search, or to impose a specific order of visiting.  Modifying dirnames when
        topdown is false is ineffective, since the directories in dirnames have
        already been generated by the time dirnames itself is generated. No matter
        the value of topdown, the list of subdirectories is retrieved before the
        tuples for the directory and its subdirectories are generated.

        Caution:  if you pass a relative pathname for top, don't change the
        current working directory between resumptions of walk.  walk never
        changes the current directory, and assumes that the client doesn't
        either.

        Example:
        ::

            from juicefs import JuiceFS
            jfs = JuiceFS("test")
            for root, dirs, files in jfs.walk('/python/Lib/email'):
                # do somthing
                pass

        """
        dirs = []
        files = []
        walk_dirs = []

        # We may not have read permission for top, in which case we can't
        # get a list of the files the directory contains.  os.walk
        # always suppressed the exception then, rather than blow up for a
        # minor reason when (say) a thousand readable directories are still
        # left to visit.  That logic is copied here.
        for entry in self.scandir(top):
            is_dir = entry.is_dir()

            if is_dir:
                dirs.append(entry.name)
            else:
                files.append(entry.name)

            if not topdown and is_dir:
                walk_dirs.append(entry.path)

        # Yield before recursion if going top down
        if topdown:
            yield top, dirs, files
            # Recurse into sub-directories
            for dirname in dirs:
                new_path = os.path.join(top, dirname)
                if not self.path.islink(new_path):
                    yield from self.walk(new_path, topdown)
        else:
            # Recurse into sub-directories
            for new_path in walk_dirs:
                yield from self.walk(new_path, topdown)
            # Yield after recursion if going bottom up
            yield top, dirs, files

    def fstat(self, fd: int) -> os.stat_result:
        """Get the status of the file descriptor *fd*.

        Return a stat_result object.
        """
        path = self._fetch_path_by_fd(fd)[0]
        return self.stat(path)

    def ftruncate(self, fd: int, length: int):
        """Truncate the file corresponding to file descriptor *fd*, so that it is at
        most *length* bytes in size.
        """
        path = self._fetch_path_by_fd(fd)[0]
        self._lib.truncate[1](path, length)
        self._flens[fd] = min(self._flens[fd], length)

    def fdopen(self, fd: int) -> FileIO:
        """Return an open file object connected to the file descriptor *fd*.

        This is an alias of the juicefs.io.open() function and accepts the same arguments.
        The only difference is that the first argument of fdopen() must always be an integer.
        """
        return FileIO(self, fd)


class JuiceFSPath:
    def __init__(self, lib: LibJuiceFS):
        self._lib = lib

    def lexists(self, path: str) -> bool:
        """Return True if *path* refers to an existing path.

        Returns True for broken symbolic links.
        """
        return juicefs_exist(self._lib.lstat1, path)

    def exists(self, path: str) -> bool:
        """Return True if *path* refers to an existing path or an open file
        descriptor.

        Returns False for broken symbolic links.
        """
        return juicefs_exist(self._lib.stat1, path)

    def isdir(self, path: str) -> bool:
        """Return True if *path* is an existing directory.

        This follows symbolic links, so both islink() and isdir() can be true for the same path.
        """
        return juicefs_exist(self._lib.stat1, path, stat.S_ISDIR)

    def isfile(self, path: str) -> bool:
        """Return True if *path* is an existing regular file.

        This follows symbolic links, so both islink() and isfile() can be true for the same path.
        """
        return juicefs_exist(self._lib.stat1, path, stat.S_ISREG)

    def islink(self, path: str) -> bool:
        """Return True if *path* refers to an existing directory entry that is a
        symbolic link.
        """
        return juicefs_exist(self._lib.lstat1, path, stat.S_ISLNK)

    def getatime(self, path) -> float:
        """Return the time of last access of *path*.

        The return value is a number giving the number of seconds since the epoch (see the time module).

        Raise OSError if the file does not exist or is inaccessible.
        """
        return juicefs_stat_result(self._lib.stat1, path).st_atime

    def getmtime(self, path) -> float:
        """Return the time of last modification of *path*.

        The return value is a number giving the number of seconds since the epoch (see the time module).

        Raise OSError if the file does not exist or is inaccessible.
        """
        return juicefs_stat_result(self._lib.stat1, path).st_mtime

    def getsize(self, path) -> int:
        """Return the size, in bytes, of *path*.

        Raise OSError if the file does not exist or is inaccessible.
        """
        return juicefs_stat_result(self._lib.stat1, path).st_size
