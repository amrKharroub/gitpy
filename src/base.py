import sys, os
import string
import data as d
import operator
import re
import stat
from collections import namedtuple
from typing import Generator


def check_oid(oid: str) -> str:
    """checks if the oid is a valid sha1"""
    is_hex = all(c in string.hexdigits for c in oid)
    if is_hex and 2 < len(oid) <= 40:
        return oid
    assert False, "Invalid object id"


def get_oid(ref_name: str) -> str:
    refs_to_try = [
        ref_name,
        os.path.join("refs", "tags", ref_name),
        os.path.join("refs", "heads", ref_name),
    ]
    for ref in refs_to_try:
        if os.path.exists(os.path.join(d.GIT_DIR, ref)):
            return d.get_ref_value(ref)
    return check_oid(ref_name)


def check_atts(attributes: str) -> tuple[str, str]:
    key1, key2 = attributes.split(".", 1)
    match key1:
        case "user":
            if key2 in ["name", "email"]:
                return (key1, key2)
        case "core":
            if key2 == "editor":
                return (key1, key2)
        case "remote":
            if key2 == "url":
                return (key1, key2)
        case _:
            raise ValueError("Incorrect fields, subfields or pattern")


def read_tree(
    sha1: str = None, data: bytes = None, recursive: bool = False
) -> list[tuple[int, str, str]]:
    """Read tree object with given SHA-1 (hex string) or data, and return list
    of (mode, path, sha1) tuples.
    """
    if sha1 is not None:
        obj_type, data = d.read_object(sha1)
        assert obj_type == "tree"
    elif data is None:
        raise TypeError('must specify "sha1" or "data"')
    i = 0
    entries = []
    while True:
        end = data.find(b"\x00", i)
        if end == -1:
            break
        mode_str, path = data[i:end].decode().split()
        mode = int(mode_str, 8)
        digest = data[end + 1 : end + 21]
        if recursive:
            if stat.S_ISDIR(mode):
                entries.extend(read_tree(digest.hex(), recursive=True))
        entries.append((mode, path, digest.hex()))
        i = end + 1 + 20
    return entries


Commit = namedtuple("Commit", ["author_time", "tree", "parents", "message"])


def read_commit(oid: str) -> Commit:
    """reads a commit file and returns it as Commit object"""
    type, commit_data = d.read_object(oid)
    assert type == "commit", f"expected commit oid but {type} where found"
    commit_lines = commit_data.decode().split("\n")
    return Commit(
        author_time=commit_lines[2],
        tree=commit_lines[0].split(maxsplit=1)[1],
        parents=commit_lines[1],
        message=commit_lines[5],
    )


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
            for mode, path, sha1 in read_tree(data=data):
                type_str = "tree" if stat.S_ISDIR(mode) else "blob"
                print("{:06o} {} {}\t{}".format(mode, type_str, sha1, path))
        else:
            assert False, "unhandled object type {!r}".format(obj_type)
    else:
        raise ValueError("unexpected mode {!r}".format(mode))


def restore_files(tree_lines: list):
    for _, path, oid in tree_lines:
        if os.path.exists(path):
            continue
        if os.path.isdir(path):
            os.mkdir(path, exit_ok=True)
        else:
            _type, data = d.read_object(oid)
            if _type == "blob":
                d.write_file(path, data)


def restore_index(tree_lines: list):
    entries = []
    for mode, path, oid in tree_lines:
        st = os.stat(path)
        flags = len(path.encode())
        assert flags < (1 << 12)
        entry = d.IndexEntry(
            int(st.st_ctime),
            int(st.st_ctime_ns) % (2**32),
            int(st.st_mtime),
            int(st.st_mtime_ns) % (2**32),
            st.st_dev,
            st.st_ino % (2**32),
            mode,
            st.st_uid,
            st.st_gid,
            st.st_size,
            bytes.fromhex(oid),
            flags,
            path,
        )
        entries.append(entry)
    entries.sort(key=operator.attrgetter("path"))
    d.write_index(entries)


def empty_dir(tree_lines: list) -> None:
    """deletes changed, new files / directories in compare to the old state in a tree

    Args:
        tree_lines (list): list of files/dirs in tree

    Returns:
        None
    """
    oid_by_path = {tree_line[1]: tree_line[2] for tree_line in tree_lines}
    for root, dirs, files in os.walk(os.getcwd(), topdown=False):
        for filename in files:
            path = os.path.relpath(os.path.join(root, filename))
            if is_ignored(path) or not os.path.isfile(path):
                continue
            if path in oid_by_path:
                if oid_by_path[path] != d.hash_object(d.read_file(path), "blob", False):
                    os.remove(path)
            else:
                os.remove(path)
        for dirname in dirs:
            path = os.path.relpath(os.path.join(root, dirname))
            if is_ignored(path):
                continue
            if path in oid_by_path:
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                # Deletion might fail if the directory contains ignored files
                # so it's ok
                pass


def checkout(name):
    oid = get_oid(name)
    commit = read_commit(oid)
    tree_lines = read_tree(commit.tree, recursive=True)
    empty_dir(tree_lines)
    restore_files(tree_lines)
    restore_index(tree_lines)
    d.update_ref("HEAD", f"ref: {oid}", False)


def is_ignored(filename: str) -> bool:

    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            ignored_files = f.readlines()
        ignored = re.search(d.GIT_DIR, filename) or re.search(filename, ignored_files)
        return bool(ignored)
    ignored = re.search(d.GIT_DIR, filename)
    return bool(ignored)


def flatten_dir(dir: str) -> Generator[str, None, None]:
    "flatten a directory"
    for root, _, filenames in os.walk(dir):
        for filename in filenames:
            yield os.path.relpath(os.path.join(root, filename))


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
            int(st.st_ctime_ns) % (2**32),
            int(st.st_mtime),
            int(st.st_mtime_ns) % (2**32),
            st.st_dev,
            st.st_ino % (2**32),
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


def create_branch(name: str, oid: str):
    """creates a branch starting from provided commit id"""
    d.update_ref(os.path.join("refs", "heads", name), oid)


def get_branch_name():
    head = d.get_ref_name("HEAD")
    if head == "HEAD":
        return None
    assert head.startswith(os.path.join("refs", "heads"))
    return os.path.relpath(head, os.path.join("refs", "heads"))


def iter_branch_names():
    for entry in os.scandir(os.path.join(d.GIT_DIR, "refs", "heads")):
        if entry.is_file():
            yield entry.name


def get_status():
    """Get status of working copy, return tuple of (changed_paths, new_paths,
    deleted_paths).
    """
    paths = set()
    for root, _, files in os.walk(os.getcwd()):
        if is_ignored(root):
            continue
        for file in files:
            path = os.path.join(root, file)
            path = os.path.relpath(path)
            paths.add(path)
    entries_by_path = {e.path: e for e in d.read_index()}
    entry_paths = set(entries_by_path)
    commit_oid = get_oid("HEAD")
    if commit_oid:
        commited_by_paths = {
            line[1]: line[2]
            for line in read_tree(read_commit(commit_oid).tree, recursive=True)
        }
        commited_paths = set(commited_by_paths)
    else:
        commited_paths = set()
    commited_files = paths & commited_paths
    modified_staged = {
        p
        for p in (paths & entry_paths)
        if p in commited_files
        and d.hash_object(d.read_file(p), "blob", write=False)
        == entries_by_path[p].sha1.hex()
        != commited_by_paths.get(p)
    }
    modified_unstaged = {
        p
        for p in (paths & entry_paths)
        if d.hash_object(d.read_file(p), "blob", write=False)
        != entries_by_path[p].sha1.hex()
    }
    new_staged = (paths & entry_paths) - commited_paths
    new_unstaged = paths - entry_paths
    deleted = entry_paths - paths
    return (
        sorted(modified_staged),
        sorted(new_staged),
        sorted(modified_unstaged),
        sorted(new_unstaged),
        sorted(deleted),
    )


def status():
    """Show status of working copy."""
    modified_staged, new_staged, modified_unstaged, new_unstaged, deleted = get_status()
    clean = True
    if modified_staged or new_staged:
        clean = False
        print("staged files: ")
        if modified_staged:
            for path in modified_staged:
                print("   modified ", path)
        if new_staged:
            for path in new_staged:
                print("   new file ", path)

    if modified_unstaged or new_unstaged:
        clean = False
        print("unstaged files: ")
        if new_unstaged:
            for path in new_unstaged:
                print("   new file ", path)
        if modified_unstaged:
            for path in modified_unstaged:
                print("   modified ", path)
    if deleted:
        clean = False
        print("deleted files:")
        for path in deleted:
            print("   ", path)
    if clean:
        print("your working directory is clean")


def create_tage(name, oid):
    d.update_ref(os.path.join("refs", "tags", name), oid)
