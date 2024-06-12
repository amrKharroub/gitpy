import sys
import string
import data as d


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
