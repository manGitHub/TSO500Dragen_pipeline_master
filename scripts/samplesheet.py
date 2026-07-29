#!/usr/bin/env python3
"""
Parse a TSO500 SampleSheet.csv and write Sample_IDs and Pair_IDs from
[TSO500S_Data] to sample_ids.txt and pair_ids.txt (one ID per line).
Usage:
    python3 samplesheet.py <path/to/SampleSheet.csv> [output_dir]
If output_dir is provided, both files are written there in addition
to the current working directory.
"""
import sys
import os

def parse(sample_sheet, output_dir=None):
    in_section = False
    header     = []
    sid_idx    = None
    pid_idx    = None
    ids        = []
    pair_ids   = []

    with open(sample_sheet) as fh:
        for raw in fh:
            line = raw.strip()
            if line.startswith("[TSO500S_Data]"):
                in_section = True
                continue
            if line.startswith("[") and in_section:
                break
            if not in_section or not line.replace(",", "").strip():
                continue
            cols = [c.strip() for c in line.split(",")]
            if not header:
                header  = cols
                sid_idx = header.index("Sample_ID")
                pid_idx = header.index("Pair_ID")
                continue
            sid = cols[sid_idx] if sid_idx < len(cols) else ""
            pid = cols[pid_idx] if pid_idx < len(cols) else ""
            if sid:
                ids.append(sid)
                pair_ids.append(pid)

    if not ids:
        sys.exit(f"ERROR: No Sample_IDs found in [TSO500S_Data] in {sample_sheet}")

    sid_content = "\n".join(ids) + "\n"
    pid_content = "\n".join(pair_ids) + "\n"

    # Always write to cwd (Nextflow work dir) for downstream steps
    with open("sample_ids.txt", "w") as out:
        out.write(sid_content)
    with open("pair_ids.txt", "w") as out:
        out.write(pid_content)

    # Also write to output_dir if provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for fname, content in [("sample_ids.txt", sid_content), ("pair_ids.txt", pid_content)]:
            out_path = os.path.join(output_dir, fname)
            with open(out_path, "w") as out:
                out.write(content)
            print(f"Written to: {out_path}")

    print(f"Parsed {len(ids)} sample(s): {', '.join(ids)}")
    print(f"Parsed {len(pair_ids)} pair(s): {', '.join(pair_ids)}")

if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(f"Usage: {sys.argv[0]} <SampleSheet.csv> [output_dir]")
    parse(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
