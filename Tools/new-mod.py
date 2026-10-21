#!/usr/bin/env python3
"""Turns a fresh copy of the mod template into a new mod.

    python3 Tools/new-mod.py <packid> "<Title>" [<package name>] [--empty]

Renames the embedded package Packages/org.mhkose.mod.example (folder and package name), the pack id 'example' in
every id, file and asset name, and the title 'Example Mod'. Every .meta file under the package gets a new GUID and
every reference inside the package is rewritten to it, so two mods made from the template never share a GUID (both
can then be open in one project, e.g. the game project). A mod has no version number: each build stamps the commit of
the mod repository into the pack. --empty also removes the sample content and leaves an empty pack. Run it before the
first time Unity opens the copy, or close Unity first.
"""
import argparse
import json
import os
import re
import shutil
import sys
import uuid

TEMPLATE_PACKAGE = "org.mhkose.mod.example"
TEMPLATE_PACK_ID = "example"
TEMPLATE_TITLE = "Example Mod"
TEMPLATE_ASSET_NAME = "Example"
SAMPLE_FOLDERS = ["Characters", "Cups", "Effects", "Powerups", "Shared", "Tracks"]
TEXT_SUFFIXES = {".asset", ".prefab", ".unity", ".mat", ".meta", ".json", ".controller", ".anim", ".lighting",
                 ".physicMaterial", ".overrideController", ".mixer", ".playable", ".mask", ".preset", ".uss", ".uxml"}
PROJECT_TEXT_FILES = ["Packages/packages-lock.json"]
GUID_LINE = re.compile(r"^guid: ([0-9a-f]{32})\s*$", re.M)
PACK_ID_RULE = re.compile(r"^[a-z][a-z0-9_]*$")
PACKAGE_RULE = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)+$")


def word(token):
    """Matches token as a name part: not inside a longer word ('examples', 'ExampleX' with lowercase x stay)."""
    return re.compile(r"(?<![A-Za-z0-9])" + token + r"(?![a-z0-9])")


def parse_args():
    p = argparse.ArgumentParser(description="Turn the mod template into a new mod.")
    p.add_argument("pack_id", help="pack id, lowercase letters, digits and _ (prefix of every content id)")
    p.add_argument("title", help="title shown in the game's Mods screen")
    p.add_argument("package", nargs="?", help="package name (default org.mhkose.mod.<packid>)")
    p.add_argument("--empty", action="store_true", help="remove the sample content, keep an empty pack")
    return p.parse_args()


def asset_name(title):
    name = "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", title) if part)
    return name if name and name[0].isalpha() else "Mod" + name


def core_pack_ids(project):
    """Pack ids of the game and its base content, from the SDK's core index next to this project."""
    manifest = json.load(open(os.path.join(project, "Packages", "manifest.json")))
    sdk = manifest["dependencies"].get("org.mhkose.sdk", "")
    if not sdk.startswith("file:"):
        return set()
    index = os.path.normpath(os.path.join(project, "Packages", sdk[5:], "CoreIndex", "core-content.json"))
    if not os.path.exists(index):
        print(f"note: no core index at {index}, pack id not checked against the game")
        return set()
    return {p["packId"] for p in json.load(open(index))["packs"]}


def check(args, project):
    if not PACK_ID_RULE.match(args.pack_id) or args.pack_id == TEMPLATE_PACK_ID:
        sys.exit(f"pack id '{args.pack_id}': use lowercase letters, digits and _, starting with a letter, not '{TEMPLATE_PACK_ID}'")
    if args.pack_id in core_pack_ids(project):
        sys.exit(f"pack id '{args.pack_id}' belongs to the game")
    if not PACKAGE_RULE.match(args.package):
        sys.exit(f"package name '{args.package}': use lowercase reverse domain notation, e.g. com.yourname.mod.{args.pack_id}")
    if not os.path.isdir(os.path.join(project, "Packages", TEMPLATE_PACKAGE)):
        sys.exit(f"Packages/{TEMPLATE_PACKAGE} not found: run this once, on a fresh copy of the template")
    if os.path.exists(os.path.join(project, "Temp", "UnityLockfile")):
        sys.exit("Unity has this project open: close it first")


def remove_sample(package):
    for folder in SAMPLE_FOLDERS:
        shutil.rmtree(os.path.join(package, folder), ignore_errors=True)
        meta = os.path.join(package, folder + ".meta")
        if os.path.exists(meta):
            os.remove(meta)
    pack = os.path.join(package, TEMPLATE_ASSET_NAME + ".asset")
    text = open(pack, encoding="utf-8").read()
    text = re.sub(r"^(  content:)\n(  - .*\n)+", r"\1 []\n", text, flags=re.M)
    text = re.sub(r"^(  description:).*$", r"\1 ", text, flags=re.M)
    open(pack, "w", encoding="utf-8", newline="\n").write(text)


def files_under(root):
    for folder, _, names in os.walk(root):
        for name in names:
            yield os.path.join(folder, name)


def new_guids(package):
    guids = {}
    for path in files_under(package):
        if path.endswith(".meta"):
            m = GUID_LINE.search(open(path, encoding="utf-8").read())
            if m:
                guids[m.group(1)] = uuid.uuid4().hex
    return guids


def rewrite(text, args, name, guids):
    for old, new in guids.items():
        text = text.replace(old, new)
    text = text.replace(TEMPLATE_PACKAGE, "\0package\0").replace(TEMPLATE_TITLE, args.title)
    text = word(TEMPLATE_PACK_ID).sub(args.pack_id, text)
    text = word(TEMPLATE_ASSET_NAME).sub(name, text)
    return text.replace("\0package\0", args.package)


def rewrite_project_text(text, args, name):
    """The lock file outside the package: only the package name and the pack asset path change."""
    text = text.replace(f"{TEMPLATE_PACKAGE}/{TEMPLATE_ASSET_NAME}.asset", f"{args.package}/{name}.asset")
    return text.replace(TEMPLATE_PACKAGE, args.package)


def rewrite_file(path, transform):
    with open(path, "rb") as f:
        raw = f.read()
    if b"\0" in raw:
        return
    text = raw.decode("utf-8")
    new = transform(text)
    if new != text:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)


def rename_tree(root, args, name):
    for folder, dirs, names in os.walk(root, topdown=False):
        for entry in names + dirs:
            renamed = word(TEMPLATE_ASSET_NAME).sub(name, word(TEMPLATE_PACK_ID).sub(args.pack_id, entry))
            if renamed != entry:
                os.rename(os.path.join(folder, entry), os.path.join(folder, renamed))


def project_settings(project):
    path = os.path.join(project, "ProjectSettings", "ProjectSettings.asset")
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"^(  productName:).*$", r"\g<1> " + os.path.basename(os.path.abspath(project)), text, flags=re.M)
    text = re.sub(r"^(  productGUID:) [0-9a-f]{32}$", r"\g<1> " + uuid.uuid4().hex, text, flags=re.M)
    open(path, "w", encoding="utf-8", newline="\n").write(text)


def main():
    args = parse_args()
    args.package = args.package or f"org.mhkose.mod.{args.pack_id}"
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    check(args, project)
    name = asset_name(args.title)
    package = os.path.join(project, "Packages", TEMPLATE_PACKAGE)
    if args.empty:
        remove_sample(package)
    guids = new_guids(package)
    for path in files_under(package):
        if os.path.splitext(path)[1] in TEXT_SUFFIXES:
            rewrite_file(path, lambda text: rewrite(text, args, name, guids))
    for rel in PROJECT_TEXT_FILES:
        if os.path.exists(os.path.join(project, rel)):
            rewrite_file(os.path.join(project, rel), lambda text: rewrite_project_text(text, args, name))
    rename_tree(package, args, name)
    os.rename(package, os.path.join(project, "Packages", args.package))
    project_settings(project)
    print(f"Mod '{args.pack_id}' ({args.title}) in Packages/{args.package}, pack asset {name}.asset, {len(guids)} new GUIDs.")
    print("Next: open the project in Unity Hub, select the pack asset, MHK > Modding > Build Selected Packs as Mods.")


if __name__ == "__main__":
    main()
