import os
import hashlib, zlib, struct
from collections import namedtuple

VERSION: int = 2
GIT_DIR: str = ".gitpie"
IndexEntry = namedtuple(
    "IndexEntry",
    [
        "ctime_s",  # File creation time in seconds
        "ctime_n",  # File creation time in nanoseconds
        "mtime_s",  # File modification time in seconds
        "mtime_n",  # File modification time in nanoseconds
        "dev",  # Device number the file resides on
        "ino",  # Inode number of the file
        "mode",  # File access permissions
        "uid",  # User ID of the file owner
        "gid",  # Group ID of the file owner
        "size",  # File size in bytes
        "sha1",  # SHA-1 hash of the file content
        "flags",  # Optional flags associated with the file
        "path",  # Path to the file on the filesystem
    ],
)


def read_file(path: str) -> bytes:
    """Read content of a file at a given path as bytes"""
    with open(path, "rb") as f:
        return f.read()


def write_file(path: str, data: bytes) -> None:
    """Write data bytes to file at given path."""
    with open(path, "wb") as f:
        f.write(data)


def init(repo: str) -> None:
    """Create directory for repo and initialize .gitpie directory."""
    os.makedirs(os.path.join(repo, GIT_DIR))
    for name in ["objects", "refs", "refs/heads"]:
        os.mkdir(os.path.join(repo, GIT_DIR, name))
    write_file(
        os.path.join(repo, GIT_DIR, "HEAD"),
        b"ref: " + os.path.join("refs", "heads", "master").encode(),
    )


def hash_object(data: bytes, obj_type: str, write: bool = True) -> str:
    """Compute hash of object data of given type and write to object store if
    "write" is True. Return SHA-1 object hash as hex string.
    """
    header = "{} {}".format(obj_type, len(data)).encode()
    full_data = header + b"\x00" + data
    sha1 = hashlib.sha1(full_data).hexdigest()
    if write:
        path = os.path.join(".git", "objects", sha1[:2], sha1[2:])
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_file(path, zlib.compress(full_data))
    return sha1


def find_object(sha1_prefix: str) -> str:
    """Find object with given SHA-1 prefix and return path to object in object
    store, or raise ValueError if there are no objects or multiple objects
    with this prefix.
    """
    if len(sha1_prefix) < 2:
        raise ValueError("hash prefix must be 2 or more characters")
    obj_dir = os.path.join(".git", "objects", sha1_prefix[:2])
    rest = sha1_prefix[2:]
    objects = [name for name in os.listdir(obj_dir) if name.startswith(rest)]
    if not objects:
        raise ValueError("object {!r} not found".format(sha1_prefix))
    if len(objects) >= 2:
        raise ValueError(
            "multiple objects ({}) with prefix {!r}".format(len(objects), sha1_prefix)
        )
    return os.path.join(obj_dir, objects[0])


def read_object(sha1_prefix: str) -> tuple[str, bytes]:
    """Read object with given SHA-1 prefix and return tuple of
    (object_type, data_bytes), or raise ValueError if not found.
    """
    path = find_object(sha1_prefix)
    full_data = zlib.decompress(read_file(path))
    nul_index = full_data.index(b"\x00")
    header = full_data[:nul_index]
    obj_type, size_str = header.decode().split()
    size = int(size_str)
    data = full_data[nul_index + 1 :]
    assert size == len(data), "expected size {}, got {} bytes".format(size, len(data))
    return (obj_type, data)


def read_index():
    """Read git index file and return list of IndexEntry objects."""
    try:
        data = read_file(os.path.join(GIT_DIR, "index"))
    except:
        return []
    digest = hashlib.sha1(data[:-20]).digest()
    assert digest == data[-20:], "invalid index checksum"
    signature, version, num_entries = struct.unpack("!4sLL", data[:12])
    assert signature == b"DIRC", "invalid index signature {}".format(signature)
    assert version == VERSION, "unknown index version {}".format(version)
    entry_data = data[12:-20]
    entries = []
    i = 0
    while i + 62 < len(entry_data):
        fields_end = i + 62
        fields = struct.unpack("!LLLLLLLLLL20sH", entry_data[i:fields_end])
        path_end = entry_data.index(b"\x00", fields_end)  # starting from fields_end
        path = entry_data[fields_end:path_end]
        entry = IndexEntry(*(fields + (path.decode(),)))
        entries.append(entry)
        entry_len = ((62 + len(path) + 8) // 8) * 8
        i += entry_len
    assert len(entries) == num_entries
    return entries


def write_index(entries: list[IndexEntry]) -> None:
    """Write list of IndexEntry objects to git index file."""
    packed_entries = []
    for entry in entries:
        entry_head = struct.pack(
            "!LLLLLLLLLL20sH",
            entry.ctime_s,
            entry.ctime_n,
            entry.mtime_s,
            entry.mtime_n,
            entry.dev,
            entry.ino,
            entry.mode,
            entry.uid,
            entry.gid,
            entry.size,
            entry.sha1,
            entry.flags,
        )
        path = entry.path.encode()
        length = (
            (62 + len(path) + 8) // 8
        ) * 8  # Calculate the padded length, a multiple of 8 bytes
        packed_entry = entry_head + path + b"\x00" * (length - 62 - len(path))
        packed_entries.append(packed_entry)
    header = struct.pack("!4sLL", b"DIRC", VERSION, len(entries))
    all_data = header + b"".join(packed_entries)
    digest = hashlib.sha1(all_data).digest()
    write_file(os.path.join(".git", "index"), all_data + digest)


def ls_files(details=False):
    """Print list of files in index (including mode, SHA-1, and stage number
    if "details" is True).
    """
    for entry in read_index():
        if details:
            stage = (entry.flags >> 12) & 3
            print(
                "{:6o} {} {:}\t{}".format(
                    entry.mode, entry.sha1.hex(), stage, entry.path
                )
            )
        else:
            print(entry.path)
