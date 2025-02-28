import argparse
import data, base
import os
from math import ceil
from collections import deque


def init(args):
    data.init(args.repo)
    print(f"Initialized empty gitpy repository in {args.repo}/{data.GIT_DIR}")


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


def commit(args):
    data.commit(args.message, args.author)


def congif(args):
    key1, key2 = args.atts
    if args.g:
        old_config = data.get_config(1)
        print(old_config)
        path = os.path.join(os.path.expanduser("~"), ".gitpyconfig")
    else:
        old_config = data.get_config(0)
        print(old_config)
        path = os.path.join(data.GIT_DIR, ".gitpyconfig")
    conf = old_config.copy()
    if key1 in conf:
        conf[key1].update({key2: args.value})
    else:
        conf[key1] = {key2: args.value}
    data.set_config(conf, path)


def checkout(args):
    base.checkout(args.commit_oid)


def status(args):
    head = base.get_oid("HEAD")
    branch = base.get_branch_name()
    if branch:
        print(f"On branch {branch}")
    else:
        print(f"HEAD  detached at {head[:10]}")
    print()
    base.status()


def tag(args):
    if not args.name:
        for _tag in base.iter_tag_names():
            print(_tag)
    else:
        base.create_tag(args.name, args.oid)


def branch(args):
    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = "*" if branch == current else " "
            print(f"{prefix} {branch}")
    else:
        base.create_branch(args.name, args.start_point)
        print(f"Branch {args.name} create at {args.start_point[:10]}")


def switch(args):
    if args.name in base.iter_branch_names():
        base.switch(args.name)
    else:
        raise ValueError(f"No branch with the name {args.name}")


def lev_dist_loop(input, target):
    # plus one is for empty strings
    cache = [["-"] * (len(target) + 1) for _ in range(len(input) + 1)]
    cache[0][0] = 0

    for n2 in range(1, len(target) + 1):
        n1 = 0
        cache[n1][n2] = n2

    for n1 in range(1, len(input) + 1):
        n2 = 0
        cache[n1][n2] = n1

    for n1 in range(1, len(input) + 1):
        for n2 in range(1, len(target) + 1):
            if input[n1 - 1] == target[n2 - 1]:
                cache[n1][n2] = cache[n1 - 1][n2 - 1]
                continue

            remove = cache[n1 - 1][n2]
            add = cache[n1][n2 - 1]
            subst = cache[n1 - 1][n2 - 1]

            cache[n1][n2] = remove

            if cache[n1][n2] > add:
                cache[n1][n2] = add

            if cache[n1][n2] > subst:
                cache[n1][n2] = subst

            cache[n1][n2] += 1
    return cache[len(input)][len(target)]


def closestMatch(InputArg: str, arguments: list) -> str | None:
    min_global = 12
    potential_commands = deque()
    for arg in arguments:
        minimum = ceil(len(arg) / 2)
        distance = lev_dist_loop(InputArg, arg)
        print(f"distance = {distance} at {arg} with min = {minimum}")
        if distance <= minimum:
            if distance < min_global:
                potential_commands.appendleft(arg)
            else:
                potential_commands.append(arg)
    return potential_commands[0] if potential_commands else None


class customArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.valid_commands = [
            "config",
            "init",
            "hash-object",
            "cat-file",
            "add",
            "ls-files",
            "commit",
            "checkout",
            "status",
            "tag",
            "branch",
            "switch",
        ]
        super().__init__(*args, **kwargs)

    def error(self, message):
        if "invalid choice:" in message:
            invalid_choice = (
                message.split("invalid choice: ")[1].split(" ")[0].replace("'", "")
            )
            closest_command = closestMatch(invalid_choice, self.valid_commands)
            if closest_command:
                message = f"Unknown command: '{invalid_choice}'. Did you mean '{closest_command}'?\n"
            else:
                message = f"Unknown command: '{invalid_choice}'.\n"

        super().error(message)


def parse_args():
    parser = customArgParser()

    oid = base.get_oid
    atts = base.check_atts

    commands = parser.add_subparsers(dest="commands")
    commands.required = True

    config_parser = commands.add_parser(
        "config", help="set config settings for the current repo or globally [--global]"
    )
    config_parser.add_argument(
        "--global",
        dest="g",
        action="store_true",
        help="set config to global (effects every repo)",
    )
    config_parser.add_argument(
        "atts",
        type=atts,
        help="thing you want to set format [field].[subfield]",
    )
    config_parser.add_argument("value", help="value of the atts you want to set")
    config_parser.set_defaults(func=congif)

    init_parser = commands.add_parser("init", help="initialize a new repo")
    init_parser.add_argument(
        "repo", default=".", help="directory name for new repo", nargs="?"
    )
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser(
        "hash-object",
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
    hash_object_parser.set_defaults(func=hash_object)

    cat_file_parser = commands.add_parser(
        "cat-file", help="display contents of an object"
    )
    valid_modes = ["commit", "tree", "blob", "size", "type", "pretty"]
    cat_file_parser.add_argument(
        "mode",
        choices=valid_modes,
        default="pretty",
        help="object type (commit, tree, blob) or display mode (size, type, pretty)",
    )
    cat_file_parser.add_argument(
        "object_id",
        type=oid,
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

    commit_parser = commands.add_parser(
        "commit", help="commit current state of index to master branch"
    )
    commit_parser.add_argument(
        "-a",
        "--author",
        help='commit author in format "A U Thor <author@example.com>" '
        "(uses GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL environment "
        "variables by default)",
    )
    commit_parser.add_argument(
        "-m", "--message", required=True, help="text of commit message"
    )
    commit_parser.set_defaults(func=commit)

    checkout_parse = commands.add_parser(
        "checkout", help="returns the working directory state of the commit provided"
    )
    checkout_parse.add_argument(
        "commit_oid", help="commit oid that you want to checkout"
    )
    checkout_parse.set_defaults(func=checkout)

    status_parser = commands.add_parser("status", help="show status of working copy")
    status_parser.set_defaults(func=status)

    tag_parser = commands.add_parser("tag")
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument("name", nargs="?")
    tag_parser.add_argument("oid", default="HEAD", nargs="?", type=oid)

    branch_parser = commands.add_parser("branch")
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument("name", nargs="?")
    branch_parser.add_argument("start_point", default="HEAD", type=oid, nargs="?")

    switch_parser = commands.add_parser("switch")
    switch_parser.add_argument("name", help="branch name to be switch to")
    switch_parser.set_defaults(func=switch)

    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
