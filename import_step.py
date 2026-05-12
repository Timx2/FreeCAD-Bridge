import sys
import os

if "CONDA_PREFIX" not in os.environ:
    os.environ["CONDA_PREFIX"] = "/home/uli/squashfs-root/usr"

import FreeCAD
import Part


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
        part_obj = doc.addObject("Part::Feature", label)
        part_obj.Shape = shape
        doc.recompute()

        doc.Label = label

        doc.saveAs(fcstd_path)
        print(f"Imported: {label} ({part_obj.Shape.ShapeType})")
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
