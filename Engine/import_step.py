import sys
import os

if "CONDA_PREFIX" not in os.environ:
    os.environ["CONDA_PREFIX"] = "/home/uli/squashfs-root/usr"

import FreeCAD
import Part
import PartDesign


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
    import re
    names = []
    with open(step_path, 'r', errors='replace') as f:
        content = f.read()
    for m in re.finditer(r"MANIFOLD_SOLID_BREP\('([^']*)'", content):
        name = m.group(1)
        if name and name not in names:
            names.append(name)
    return names


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

        for i, solid in enumerate(solids):
            part_name = names[i] if i < len(names) and names[i] else f"Part{i+1}"
            body = doc.addObject("PartDesign::Body", f"Body_{i+1}")
            body.Label = part_name
            base_feat = body.newObject("PartDesign::FeatureBase", part_name)
            base_feat.Shape = solid
            body.Tip = base_feat

        doc.recompute()
        doc.Label = label

        doc.saveAs(fcstd_path)
        count = len(solids)
        if count == 1:
            print(f"Imported: {label} (Solid)")
        else:
            print(f"Imported: {label} ({count} solids)")
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
