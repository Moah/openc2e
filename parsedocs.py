import json
import os
import re
import sys

FILENAME_TO_CATEGORY = {  # default category mappings
    "caosVM_agent.cpp": "Agents",
    "caosVM_camera.cpp": "Cameras",
    "caosVM_core.cpp": "Core functions",
    "caosVM_creatures.cpp": "Creatures",
    "caosVM_compound.cpp": "Compound agents",
    "caosVM_debug.cpp": "Debugging",
    "caosVM_files.cpp": "Files",
    "caosVM_flow.cpp": "Flow control",
    "caosVM_genetics.cpp": "Genetics",
    "caosVM_history.cpp": "History",
    "caosVM_input.cpp": "Input",
    "caosVM_map.cpp": "Map",
    "caosVM_motion.cpp": "Motion",
    "caosVM_net.cpp": "Networking",
    "caosVM_ports.cpp": "Ports",
    "caosVM_resources.cpp": "Resources",
    "caosVM_scripts.cpp": "Scripts",
    "caosVM_sounds.cpp": "Sound",
    "caosVM_time.cpp": "Time",
    "caosVM_variables.cpp": "Variables",
    "caosVM_vectors.cpp": "Vectors",
    "caosVM_vehicles.cpp": "Vehicles",
    "caosVM_world.cpp": "World",
}


def parse_syntaxstring(syntaxstring):
    m = re.match(
        r"([A-Z0-9x#_:*!$+]+(\s+[A-Z0-9x#_:*!$+]+)?)\s+\(([^\)]+)\)", syntaxstring
    )
    name = m.groups()[0]
    type = m.groups()[2]
    arguments = []
    argline = syntaxstring[m.end() :].strip()
    while argline:
        m = re.match(r"(\w+)\s*\(([^\)]+)\)", argline)
        arguments.append({"name": m.groups()[0], "type": m.groups()[1]})
        argline = argline[m.end() :].strip()

    props = {
        "arguments": arguments,
        "name": name,
        "match": name.split(" ")[-1],
        "type": type,
        "syntaxstring": syntaxstring,
        "uniquename": ("c_" if type == "command" else "v_")
        + re.sub(r"[^A-Za-z0-9_]", "", re.sub(r"\s+", "_", name)),
    }
    if " " in name:
        props["namespace"] = name.split(" ")[0].lower()

    return props


objects = []

for filename in sys.argv[1:]:
    with open(filename) as f:
        lines = f.read().split("\n")

    p = 0

    def getline():
        return re.sub(r"^\s*\*(\s+|$)", "", lines[p]).strip()

    try:
        while p < len(lines):
            if not getline().startswith("/**"):
                p += 1
                continue
            p += 1

            syntaxstring = getline()
            p += 1

            directives = []
            comments = []

            while True:
                if not getline().strip():
                    p += 1
                    continue
                if not re.match(r"^\s*%[^%]", getline()):
                    break
                directives.append(getline())
                p += 1

            while True:
                if getline().startswith("*/"):
                    break
                comments.append(getline())
                p += 1

            def getdirective(prefix):
                result = None
                for d in directives:
                    m = re.match(r"%\s*{}\s+(.*)".format(prefix), d)
                    if not m:
                        continue
                    if result is not None:
                        raise Exception("%{} defined multiple times".format(prefix))
                    # print(m.groups())
                    result = m.groups()[0].strip()
                return result

            obj = {
                "filename": os.path.basename(filename),
                "category": FILENAME_TO_CATEGORY.get(
                    os.path.basename(filename), "unknown"
                ).lower(),
            }
            if "".join(comments).strip():
                obj["description"] = "\n".join(comments).strip() + "\n"
            obj.update(parse_syntaxstring(syntaxstring))

            obj["evalcost"] = {"default": 1 if obj["type"] == "command" else 0}
            cost = getdirective("cost")
            if cost:
                if " " in cost:
                    variants, cost = re.split(r"\s+", cost.strip())
                    for v in variants.split(","):
                        obj["evalcost"][v] = int(cost)
                else:
                    obj["evalcost"]["default"] = int(cost)

            # TODO: figure out implementation by parsing C++ ?
            obj["implementation"] = (
                getdirective("pragma implementation") or "caosVM::" + obj["uniquename"]
            )

            if any(d.startswith("%pragma") for d in directives):
                obj["pragma"] = {}
                for d in directives:
                    if not d.startswith("%pragma"):
                        continue
                    obj["pragma"][d.replace("%pragma ", "").split(" ")[0]] = d.replace(
                        "%pragma ", ""
                    ).split(" ", 1)[1]

            if getdirective("status"):
                obj["status"] = getdirective("status")

            if getdirective("pragma saveimpl"):
                obj["saveimpl"] = getdirective("pragma saveimpl")
            elif obj["type"] == "variable":
                obj["saveimpl"] = obj["implementation"].replace("v_", "s_")
            else:
                obj["saveimpl"] = "caosVM::dummy_cmd"

            if getdirective("pragma stackdelta"):
                obj["stackdelta"] = getdirective("pragma stackdelta")
                if obj["stackdelta"] == "any":
                    obj["stackdelta"] = "INT_MAX"
                else:
                    obj["stackdelta"] = int(obj["stackdelta"])
            else:
                obj["stackdelta"] = 0 if obj["type"] == "command" else 1
                for a in obj["arguments"]:
                    if a["type"] != "variable":
                        obj["stackdelta"] -= 1

            for d in directives:
                d = d.replace("%", "").strip()
                if d.split(" ")[0] not in ("pragma", "status", "cost",):
                    raise Exception("Unknown directive: {}".format(d))
                if d.startswith("pragma"):
                    d = d.split(" ", 1)[1].strip()
                    if d.split(" ")[0] not in (
                        "implementation",
                        "variants",
                        "parser",
                        "stackdelta",
                        "saveimpl",
                    ):
                        raise Exception("Unknown pragma: {}".format(d))

            objects.append(obj)
    except Exception as e:
        sys.stderr.write("{} at {} line {}\n".format(type(e).__name__, filename, p))
        raise

variants = {
    "c1": {},
    "c2": {},
    "c3": {},
    "cv": {},
    "sm": {},
}

for obj in objects:
    if obj.get("pragma", {}).get("variants"):
        if obj["pragma"]["variants"] == "all":
            for key in variants:
                variants[key][obj["uniquename"]] = obj
        else:
            for v in obj["pragma"]["variants"].split(" "):
                variants[v][obj["uniquename"]] = obj
    else:
        for key in ("c3", "cv", "sm"):
            variants[key][obj["uniquename"]] = obj


print(json.dumps({"namespaces": [], "variants": variants},))
