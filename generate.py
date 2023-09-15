#!/usr/bin/env python
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
import os
import shutil
import subprocess
import contextlib
import hashlib


@contextlib.contextmanager
def WorkingDir(path: str | Path):
    old_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_cwd)


def crop(file: str | Path):
    f = Path(file)
    subprocess.run(["pdfcrop", "--hires", str(f)])
    shutil.move(f.with_name(f"{f.stem}-crop.pdf"), f)


def get_num_pages(file: str | Path) -> int:
    for line in subprocess.check_output(["pdfinfo", str(file)]).decode().splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise RuntimeError(f"Failed to determine number of pages of PDF: {file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", type=Path, help="Path of input PDF")
    parser.add_argument("outfile", type=Path, help="Path for output PDF")
    parser.add_argument(
        "--inner-margin", type=int, default=100, help="Margin between pages in booklet"
    )
    parser.add_argument(
        "--outer-margin", type=int, default=40, help="Outer margin of booklet"
    )
    args = parser.parse_args()

    with open(args.infile, "rb") as fptr:
        m = hashlib.md5()
        m.update(fptr.read())
        tmpdir = Path(f"tmp-{m.hexdigest()}").resolve()

    if tmpdir.exists():
        shutil.rmtree(tmpdir)

    tmpdir.mkdir(parents=True)

    inpath = args.infile.resolve()
    outpath = args.infile.resolve()

    with WorkingDir(tmpdir):
        shutil.copy2(inpath, "in.pdf")
        crop("in.pdf")

        subprocess.run(
            [
                "pdfbook2",
                "--resolution=600",
                "--short-edge",
                f"--inner-margin={args.inner_margin}",
                f"--outer-margin={args.outer_margin}",
                "in.pdf",
            ]
        )
        shutil.move("in-book.pdf", "book.pdf")
        book_pages = get_num_pages("book.pdf")

        pages = list(str(i) for i in range(1, book_pages + 1, 2))
        for i, page in enumerate(pages):
            if int(page) > book_pages:
                pages[i] = "\{\}"
        subprocess.run(
            [
                "pdfjam",
                "--nup",
                "2x4",
                "--a4paper",
                "--frame",
                "true",
                "-o",
                "front.pdf",
                "book.pdf",
                ",".join(pages),
            ]
        )

        pages = list(str(i) for i in range(2, book_pages + 1, 2))
        l = len(pages) & (~1)
        pages[:l:2], pages[1:l:2] = pages[1:l:2], pages[:l:2]
        for i, page in enumerate(pages):
            if int(page) > book_pages:
                pages[i] = "\{\}"
        if len(pages) % 2:
            pages.insert(-1, "\{\}")
        subprocess.run(
            [
                "pdfjam",
                "--nup",
                "2x4",
                "--a4paper",
                "--frame",
                "true",
                "-o",
                "back.pdf",
                "book.pdf",
                ",".join(pages),
            ]
        )

        subprocess.run(["pdfseparate", "front.pdf", "front%d.pdf"])
        subprocess.run(["pdfseparate", "back.pdf", "back%d.pdf"])

        num_front = get_num_pages("front.pdf")
        num_back = get_num_pages("back.pdf")
        pages_front = [f"front{i}.pdf" for i in range(1, num_front + 1)]
        pages_back = [f"back{i}.pdf" for i in range(1, num_back + 1)]
        pages = [""] * (num_front + num_back)
        pages[::2] = pages_front
        pages[1::2] = pages_back

        subprocess.run(
            [
                "pdfunite",
            ]
            + pages
            + [
                "out.pdf",
            ]
        )
        shutil.copy2("out.pdf", outpath)

    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
