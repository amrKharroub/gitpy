import argparse
import data, base


def init(args):
    data.init(args.repo)
    print(f"Initialized empty ugit repository in {args.repo}/{data.GIT_DIR}")


def hash_object(args):
    sha1 = data.hash_object(data.read_file(args.path), args.type, write=args.write)
    print(sha1)


def cat_file(args):
    base.cat_file(args.mode, args.oid)


def add(args):
    files = base.get_all_non_ignored_files(args.paths)
    base.add(files)


def ls_files(args):
    data.ls_files(args.stage)


def parse_args():
    parser = argparse.ArgumentParser()

    oid = base.check_oid

    commands = parser.add_subparsers(dest="commands")
    commands.required = True

    init_parser = commands.add_parser("init", help="initialize a new repo")
    init_parser.add_argument("repo", help="directory name for new repo", nargs="?")
    init_parser.set_default(func=init)

    hash_object_parser = commands.add_parser(
        "hash_object",
        help="'hash contents of given path, optionally write to object store",
    )
    hash_object_parser.add_argument("path", help="path of file to hash")
    hash_object_parser.add_argument(
        "-t",
        choices=["commit", "tree", "blob"],
        default="blob",
        dest="type",
        help="type of object (default %(default)r)",
    )
    hash_object_parser.add_argument(
        "-w",
        action="store_true",
        dest="write",
        help="write object to object store (as well as printing hash)",
    )
    hash_object_parser.set_default(func=hash_object)

    cat_file_parser = commands.add_parser(
        "cat-file", help="display contents of an object"
    )
    valid_modes = ["commit", "tree", "blob", "size", "type", "pretty"]
    cat_file_parser.add_argument(
        "mode",
        choices=valid_modes,
        default="pretty",
        dest="mode",
        help="object type (commit, tree, blob) or display mode (size, type, pretty)",
    )
    cat_file_parser.add_argument(
        "object_id",
        type=oid,
        dest="oid",
        help="SHA-1 hash (or hash prefix) of object to display",
    )
    cat_file_parser.set_defaults(func=cat_file)

    add_parser = commands.add_parser("add", help="add file(s) to index")
    add_parser.add_argument(
        "paths", nargs="+", metavar="path", help="path(s) of files to add"
    )
    add_parser.set_defaults(func=add)

    ls_files_parser = commands.add_parser("ls-files", help="list files in index")
    ls_files_parser.add_argument(
        "-s",
        "--stage",
        action="store_true",
        help="show object details (mode, hash, and stage number) in addition to path",
    )
    ls_files_parser.set_defaults(func=ls_files)
