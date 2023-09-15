#!/usr/bin/bash
set -euf -o pipefail

infile="$1"
outfile="$2"

hash=$(md5sum "${infile}" | cut -d" " -f1)

tmpdir=${PWD}/tmp-${hash}
workdir=${PWD}
mkdir -p ${tmpdir}

cp "${infile}" ${tmpdir}/in.pdf
cd ${tmpdir}

# Crop all pages of the input PDF.
pdfcrop --hires in.pdf
mv in-crop.pdf in.pdf

# Create a book, i.e. merge two pages in a way that they could be bound as a book.
pdfbook2 --resolution=600 in.pdf --short-edge --inner-margin=100 --outer-margin=30

# Obtain the number of pages in the book.
book_pages=$(pdfinfo in-book.pdf | grep "Pages:" | grep -Po "[0-9]+$")

# Create a PDF containing every odd page of the book. These will be printed on
# on the front sides of our two-sided print.
pdfjam --nup "2x4" --a4paper --frame true -o odd.pdf in-book.pdf "$(seq -s, 1 2 ${book_pages})"

# Create a PDF containing every even page of the book. These will be printed on
# on the back sides of our two-sided print.
pdfjam --nup "2x4" --a4paper --frame true -o even.pdf in-book.pdf "{},$(seq -s, 2 2 ${book_pages})"

# Fetch the number of pages in odd.pdf.
num_odd=$(pdfinfo odd.pdf | grep "Pages:" | grep -Po "[0-9]+$")

# Fetch the number of pages in even.pdf.
num_even=$(pdfinfo even.pdf | grep "Pages:" | grep -Po "[0-9]+$")

# Calculate the total number of pages.
num_total=$(( ${num_odd} + ${num_even} ))

# Crop both even.pdf and odd.pdf.
pdfcrop --hires odd.pdf
pdfcrop --hires even.pdf

pdfseparate odd.pdf "odd%d.pdf"
pdfseparate even.pdf "even%d.pdf"

for num in $(seq 1 2 ${num_even}); do
  mv -v even${num}.pdf bak.pdf
  mv -v even$(( ${num} + 1 )).pdf even${num}.pdf
  mv -v bak.pdf even$(( ${num} + 1 )).pdf
done

for num in $(seq 1 ${num_odd}); do
  mv -v odd${num}.pdf p$(( 2 * ${num} - 1 )).pdf
done
for num in $(seq 1 ${num_even}); do
  mv -v even${num}.pdf p$(( 2 * ${num})).pdf
done

pdfunite $(seq -f "p%g.pdf" 1 ${num_total}) out.pdf

cd ${workdir}
cp ${tmpdir}/out.pdf "${outfile}"
rm -rf ${tmpdir}
