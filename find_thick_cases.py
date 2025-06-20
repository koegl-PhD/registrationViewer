import nibabel as nib
import numpy as np
from pathlib import Path
import tqdm

from typing import Tuple

# should have 'preprocessed' in the file path
# should have "_seg" in the file name
# should have 9 segmentations

path_files = r"/home/koeglf/Desktop/annotation_folder/done"

# find recursively all files in path_files
all_files = list(Path(path_files).rglob("*_seg.nii.gz"))
# filter files that have 'preprocessed' in the file path
all_files = [f for f in all_files if 'raw' in str(f)]


def get_spacing(path: str) -> Tuple[int, int, int]:

    im = nib.load(path)

    zooms = im.header.get_zooms()

    return zooms


def num_of_segmentations(file_path: Path) -> int:
    try:
        img = nib.load(file_path)
        data = img.get_fdata()
        unique_segments = np.unique(data)
        return len(unique_segments)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return 0


with_n = []
with_other = []
for f in tqdm.tqdm(all_files):
    # if all(a < 2.0 for a in get_spacing(f)):
    #     with_n.append(f)
    num = num_of_segmentations(f)
    if num == 10:
        with_n.append(f)
    else:
        with_other.append((num, f.as_posix().split('/')[-4]))


patients = {"positive": set(),
            "negativ": set()}

# print the number of files found
print(f"Number of files with 9 segmentations: {len(with_n)}")
# print the file paths
for file in with_n:
    patient_name = file.as_posix().split('/')[-4]
    exists = file.as_posix().split('/')[-5]

    patients[exists].add(patient_name)


x = 0
