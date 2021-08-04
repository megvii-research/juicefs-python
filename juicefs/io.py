import errno
import os
from io import DEFAULT_BUFFER_SIZE
from io import BufferedRandom as _BufferedRandom
from io import BufferedReader
from io import BufferedWriter as _BufferedWriter
from io import RawIOBase, TextIOWrapper, UnsupportedOperation
from typing import Optional


class BufferedWriter(_BufferedWriter):
    def flush(self):
        super().flush()
        self.raw.flush()


class BufferedRandom(_BufferedRandom):
    def flush(self):
        super().flush()
        self.raw.flush()


class FileIO(RawIOBase):
    _fd = -1
    _created = False
    _readable = False
    _writable = False
    _appending = False
    _seekable = None

    def __init__(self, jfs, fd: int):
        path, flags, jfs_flags = jfs._fetch_path_by_fd(fd)
        self._jfs = jfs
        self._fd = fd
        self.name = path
        self._flags = flags
        self._created = flags & os.O_EXCL != 0
        self._readable = jfs_flags & os.R_OK != 0
        self._writable = jfs_flags & os.W_OK != 0
        self._appending = flags & os.O_APPEND != 0

    def __del__(self):
        if self._fd >= 0 and not self.closed:
            import warnings

            warnings.warn(
                "unclosed file %r" % (self,), ResourceWarning, stacklevel=2, source=self
            )
            self.close()

    def __getstate__(self):
        raise TypeError(f"cannot pickle {self.__class__.__name__!r} object")

    def __repr__(self) -> str:
        class_name = "%s.%s" % (self.__class__.__module__, self.__class__.__qualname__)
        if self.closed:
            return "<%s [closed]>" % class_name
        try:
            name = self.name
        except AttributeError:
            return "<%s fd=%d mode=%r>" % (class_name, self._fd, self.mode)
        else:
            return "<%s name=%r mode=%r>" % (class_name, name, self.mode)

    def _checkReadable(self):
        if not self._readable:
            raise UnsupportedOperation("File not open for reading")

    def _checkWritable(self, msg=None):
        if not self._writable:
            raise UnsupportedOperation("File not open for writing")

    def read(self, size: Optional[int] = None) -> Optional[bytes]:
        """Read at most *size* bytes, returned as bytes.
        Only makes one system call, so less data may be returned than requested
        In non-blocking mode, returns None if no data is available.
        Return an empty bytes object at EOF.
        """
        self._checkClosed()
        self._checkReadable()
        if size is None or size < 0:
            return self.readall()
        try:
            return self._jfs.read(self._fd, size)
        except BlockingIOError:
            return None

    def readall(self) -> Optional[bytes]:
        """Read all data from the file, returned as bytes.
        In non-blocking mode, returns as much as is immediately available,
        or None if no data is available.  Return an empty bytes object at EOF.
        """
        self._checkClosed()
        self._checkReadable()
        bufsize = DEFAULT_BUFFER_SIZE
        try:
            pos = self._jfs.lseek(self._fd, 0, os.SEEK_CUR)
            end = self._jfs.fstat(self._fd).st_size
            if end >= pos:
                bufsize = end - pos + 1
        except OSError:
            pass

        result = bytearray()
        while True:
            if len(result) >= bufsize:
                bufsize = len(result)
                bufsize += max(bufsize, DEFAULT_BUFFER_SIZE)
            n = bufsize - len(result)
            try:
                chunk = self._jfs.read(self._fd, n)
            except BlockingIOError:
                if result:
                    break
                return None
            if not chunk:  # reached the end of the file
                break
            result += chunk

        return bytes(result)

    def readinto(self, b):
        """Same as RawIOBase.readinto()."""
        m = memoryview(b).cast("B")  # pytype: disable=attribute-error
        data = self.read(len(m))
        n = len(data)
        m[:n] = data
        return n

    def write(self, b: bytes) -> Optional[int]:
        """Write bytes *b* to file, return number written.
        Only makes one system call, so not all of the data may be written.
        The number of bytes actually written is returned.  In non-blocking mode,
        returns None if the write would block.
        """
        self._checkClosed()
        self._checkWritable()
        try:
            if isinstance(b, memoryview):
                b = bytes(b)
            if self._appending:
                self._jfs.lseek(self._fd, 0, os.SEEK_END)
            return self._jfs.write(self._fd, b)
        except BlockingIOError:
            return None

    def seek(self, pos: int, whence: int = os.SEEK_SET) -> int:
        """Move to new file position.
        Argument *offset* is a byte count.  Optional argument *whence* defaults to
        SEEK_SET or 0 (offset from start of file, offset should be >= 0); other values
        are SEEK_CUR or 1 (move relative to current position, positive or negative),
        and SEEK_END or 2 (move relative to end of file, usually negative, although
        many platforms allow seeking beyond the end of a file).
        Note that not all file objects are seekable.
        """
        if isinstance(pos, float):
            raise TypeError("an integer is required")
        self._checkClosed()
        return self._jfs.lseek(self._fd, pos, whence)

    def tell(self) -> int:
        """tell() -> int.  Current file position.
        Can raise OSError for non seekable files."""
        self._checkClosed()
        return self._jfs.lseek(self._fd, 0, os.SEEK_CUR)

    def truncate(self, size: Optional[int] = None) -> int:
        """Truncate the file to at most *size* bytes.
        *size* defaults to the current file position, as returned by tell().
        The current file position is changed to the value of size.
        """
        self._checkClosed()
        self._checkWritable()
        if size is None:
            size = self.tell()
        self._jfs.ftruncate(self._fd, size)
        return size

    def flush(self):
        """Flush write buffers, if applicable.
        This is not implemented for read-only and non-blocking streams.
        """
        self._checkClosed()
        self._jfs.flush(self._fd)

    def close(self):
        """Close the file.
        A closed file cannot be used for further I/O operations.  close() may be
        called more than once without error.
        """
        if not self.closed:
            try:
                super().close()
            finally:
                self._jfs.close(self._fd)

    def seekable(self) -> bool:
        """True if file supports random-access."""
        self._checkClosed()
        if self._seekable is None:
            try:
                self.tell()
            except OSError:
                self._seekable = False
            else:
                self._seekable = True
        return self._seekable

    def readable(self) -> bool:
        """True if file was opened in a read mode."""
        self._checkClosed()
        return self._readable

    def writable(self) -> bool:
        """True if file was opened in a write mode."""
        self._checkClosed()
        return self._writable

    def fileno(self) -> int:
        """Return the underlying file descriptor (an integer)."""
        self._checkClosed()
        return self._fd

    def isatty(self) -> bool:
        """True if the file is connected to a TTY device."""
        self._checkClosed()
        return False

    @property
    def mode(self) -> str:
        """String giving the file mode"""
        if self._created:
            if self._readable:
                return "xb+"
            else:
                return "xb"
        elif self._appending:
            if self._readable:
                return "ab+"
            else:
                return "ab"
        elif self._readable:
            if self._writable:
                return "rb+"
            else:
                return "rb"
        else:
            return "wb"


def open(
    jfs,
    path: str,
    mode: str = "r",
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
):
    """Open a juicefs file.

    The *mode* can be 'r' (default), 'w', 'x' or 'a' for reading, writing,
    exclusive creation or appending.

    The file will be created if it doesn't exist when opened for writing or
    appending; it will be truncated when opened for writing.

    A FileExistsError will be raised if it already exists when opened for
    creating. Opening a file for creating implies writing so this mode behaves
    in a similar way to 'w'. Add a '+' to the mode to allow simultaneous
    reading and writing.
    """

    if not isinstance(path, str):
        raise TypeError("invalid path: %r" % path)
    if not isinstance(mode, str):
        raise TypeError("invalid mode: %r" % mode)
    if not isinstance(buffering, int):
        raise TypeError("invalid buffering: %r" % buffering)
    if encoding is not None and not isinstance(encoding, str):
        raise TypeError("invalid encoding: %r" % encoding)
    if errors is not None and not isinstance(errors, str):
        raise TypeError("invalid errors: %r" % errors)
    modes = set(mode)
    if modes - set("axrwb+tU") or len(mode) > len(modes):
        raise ValueError("invalid mode: %r" % mode)
    creating = "x" in modes
    reading = "r" in modes
    writing = "w" in modes
    appending = "a" in modes
    updating = "+" in modes
    text = "t" in modes
    binary = "b" in modes

    if "U" in modes:
        if creating or writing or appending or updating:
            raise ValueError("mode U cannot be combined with 'x', 'w', 'a', or '+'")
        import warnings

        warnings.warn("'U' mode is deprecated", DeprecationWarning, 2)
        reading = True
    if text and binary:
        raise ValueError("can't have text and binary mode at once")
    if creating + reading + writing + appending > 1:
        raise ValueError("can't have read/write/append mode at once")
    if not (creating or reading or writing or appending):
        raise ValueError("must have exactly one of read/write/append mode")
    if binary and encoding is not None:
        raise ValueError("binary mode doesn't take an encoding argument")
    if binary and errors is not None:
        raise ValueError("binary mode doesn't take an errors argument")
    if binary and newline is not None:
        raise ValueError("binary mode doesn't take a newline argument")

    readable = False
    writable = False
    if creating:
        writable = True
        flags = os.O_EXCL | os.O_CREAT
    elif reading:
        readable = True
        flags = 0
    elif writing:
        writable = True
        flags = os.O_CREAT | os.O_TRUNC
    elif appending:
        writable = True
        flags = os.O_APPEND | os.O_CREAT

    if updating:
        readable = True
        writable = True

    if readable and writable:
        flags |= os.O_RDWR
    elif readable:
        flags |= os.O_RDONLY
    else:
        flags |= os.O_WRONLY

    flags |= getattr(os, "O_BINARY", 0)

    fd = None
    try:
        fd = jfs.open(path, flags)

        if appending:
            # For consistent behaviour, we explicitly seek to the
            # end of file (otherwise, it might be done only on the
            # first write()).
            try:
                jfs.lseek(fd, 0, os.SEEK_END)
            except OSError as e:
                if e.errno != errno.ESPIPE:
                    raise
    except:
        if fd is not None:
            jfs.close(fd)
        raise

    raw = FileIO(jfs, fd)
    result = raw
    try:
        line_buffering = False
        if buffering == 1 or buffering < 0 and raw.isatty():
            buffering = -1
            line_buffering = True
        if buffering < 0:
            buffering = DEFAULT_BUFFER_SIZE
            try:
                bs = os.fstat(raw.fileno()).st_blksize
            except (OSError, AttributeError):
                pass
            else:
                if bs > 1:
                    buffering = bs
        if buffering < 0:
            raise ValueError("invalid buffering size")
        if buffering == 0:
            if binary:
                return result
            raise ValueError("can't have unbuffered text I/O")
        if updating:
            buffer = BufferedRandom(raw, buffering)
        elif creating or writing or appending:
            buffer = BufferedWriter(raw, buffering)
        elif reading:
            buffer = BufferedReader(raw, buffering)
        else:
            raise ValueError("unknown mode: %r" % mode)
        result = buffer
        if binary:
            return result
        text = TextIOWrapper(buffer, encoding, errors, newline, line_buffering)
        result = text
        text.mode = mode
        return result
    except:
        result.close()
        raise
