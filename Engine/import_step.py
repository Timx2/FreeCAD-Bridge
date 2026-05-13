import sys
import os
import re

if "CONDA_PREFIX" not in os.environ:
    os.environ["CONDA_PREFIX"] = "/home/uli/squashfs-root/usr"

import FreeCAD
import Part


def _collect_solids(shape):
    solids = []
    if shape.ShapeType == 'Solid':
        solids.append(shape)
    elif shape.ShapeType == 'Compound':
        for s in shape.SubShapes:
            solids.extend(_collect_solids(s))
    elif shape.ShapeType in ('CompSolid', 'Shell'):
        for s in shape.SubShapes:
            solids.extend(_collect_solids(s))
    return solids


def _extract_step_names(step_path):
    names = []
    with open(step_path, 'r', errors='replace') as f:
        content = f.read()
    for m in re.finditer(r"MANIFOLD_SOLID_BREP\('([^']*)'", content):
        name = m.group(1)
        if name and name not in names:
            names.append(name)
    return names


def _is_default_name(name):
    return bool(re.match(r'^(Solid|Sheet|Curve|Group)\s+\d+$', name))


def step_to_fcstd(step_path, fcstd_path):
    if not os.path.exists(step_path):
        print(f"ERROR: STEP file not found: {step_path}", file=sys.stderr)
        sys.exit(1)

    basename = os.path.basename(step_path)
    label = os.path.splitext(basename)[0]
    doc_name = label.replace(" ", "_").replace("-", "_").replace(".", "_")

    doc = None
    try:
        doc = FreeCAD.newDocument(doc_name)

        shape = Part.read(step_path)
        solids = _collect_solids(shape)

        if not solids:
            print(f"ERROR: No solids found in {basename}", file=sys.stderr)
            sys.exit(4)

        names = _extract_step_names(step_path)

        # Filter: only renamed solids — skip default names like "Solid 1", "Sheet 3"
        pairs = []
        for i, solid in enumerate(solids):
            part_name = names[i] if i < len(names) and names[i] else f"Part{i+1}"
            if not _is_default_name(part_name):
                pairs.append((part_name, solid))

        if not pairs:
            print(f"Skipped: {basename} — all solids have default names, none selected.")
            sys.exit(0)

        for part_name, solid in pairs:
            part_obj = doc.addObject("Part::Feature", part_name)
            part_obj.Shape = solid
            part_obj.Label = part_name

        doc.recompute()
        doc.Label = label

        doc.saveAs(fcstd_path)
        skipped = len(solids) - len(pairs)
        msg = f"Imported: {label} ({len(pairs)} solid"
        msg += "s" if len(pairs) != 1 else ""
        msg += ")"
        if skipped:
            msg += f", {skipped} default names skipped"
        print(msg)
        print(f"Saved: {os.path.basename(fcstd_path)}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(3)
    finally:
        try:
            if doc and doc.Name in FreeCAD.listDocuments():
                FreeCAD.closeDocument(doc.Name)
        except:
            pass


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file.step> <file.FCStd>", file=sys.stderr)
        sys.exit(1)

    step_to_fcstd(sys.argv[1], sys.argv[2])
