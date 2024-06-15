import sys, os
import string
import data as d
import operator


def check_oid(oid: str) -> str:
    """checks if the oid is a valid sha1"""
    is_hex = all(c in string.hexdigits for c in oid)
    if is_hex and 2 < len(oid) <= 40:
        return oid
    assert False, "Invalid object id"


def cat_file(mode: str, sha1_prefix: str) -> None:
    """Write the contents of (or info about) object with given SHA-1 prefix to
    stdout. If mode is 'commit', 'tree', or 'blob', print raw data bytes of
    object. If mode is 'size', print the size of the object. If mode is
    'type', print the type of the object. If mode is 'pretty', print a
    prettified version of the object.
    """
    obj_type, data = d.read_object(sha1_prefix)
    if mode in ["commit", "tree", "blob"]:
        if obj_type != mode:
            raise ValueError("expected object type {}, got {}".format(mode, obj_type))
        sys.stdout.flush()
        sys.stdout.buffer.write(data)
    elif mode == "size":
        print(len(data))
    elif mode == "type":
        print(obj_type)
    elif mode == "pretty":
        if obj_type in ["commit", "blob"]:
            sys.stdout.flush()
            sys.stdout.buffer.write(data)
        elif obj_type == "tree":
            assert False, "Not Implemented"
            # for mode, path, sha1 in read_tree(data=data):
            #     type_str = 'tree' if stat.S_ISDIR(mode) else 'blob'
            #     print('{:06o} {} {}\t{}'.format(mode, type_str, sha1, path))
        else:
            assert False, "unhandled object type {!r}".format(obj_type)
    else:
        raise ValueError("unexpected mode {!r}".format(mode))


def is_ignored(filename: str) -> bool:

    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            ignored_files = f.readlines()
        return d.GIT_DIR in os.path.split(filename)
    return d.GIT_DIR in os.path.split(filename)


def flatten_dir(dir: str) -> iter[str]:
    "flatten a directory"
    for root, _, filenames in os.walk(dir):
        for filename in filenames:
            yield os.path.join(root, filename)


def get_all_non_ignored_files(names: list[str]) -> list[str]:
    """
    This function takes a list of paths (can be files or directories) and returns a list of
    all non-ignored files found within those paths. It flattens any subdirectories encountered.

    Args:
        paths (list[str]): A list containing file or directory paths.

    Returns:
        list[str]: A list containing the full paths of all non-ignored files found.

    Raises:
        ValueError: If any of the provided paths do not exist.
    """
    output = []
    for name in names:
        if os.path.isdir(name):
            for filename in flatten_dir(name):
                if not is_ignored(filename):
                    output.append(filename)
        elif os.path.isfile(name):
            if not is_ignored(name):
                output.append(os.path.relpath(name))
    return output


def add(filepaths: list[str]):
    """Add files indicated by filenames to index."""
    all_entries: list[d.IndexEntry] = d.read_index()
    entries = [
        e for e in all_entries if os.path.exists(e.path) and e.path not in filepaths
    ]
    for path in filepaths:
        sha1 = d.hash_object(d.read_file(path), "blob")
        st = os.stat(path)
        flags = len(path.encode())
        assert flags < (1 << 12)
        entry = d.IndexEntry(
            int(st.st_ctime),
            int(st.st_ctime_ns),
            int(st.st_mtime),
            int(st.st_mtime_ns),
            st.st_dev,
            st.st_ino,
            st.st_mode,
            st.st_uid,
            st.st_gid,
            st.st_size,
            bytes.fromhex(sha1),
            flags,
            path,
        )
        entries.append(entry)
    entries.sort(key=operator.attrgetter("path"))
    d.write_index(entries)
