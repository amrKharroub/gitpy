import os, sys
import hashlib, zlib

GIT_DIR: str = ".gitpie"


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
