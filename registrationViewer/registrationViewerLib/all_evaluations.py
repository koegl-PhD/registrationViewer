import glob
import json
import os

from typing import Dict, List, Literal, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
import seaborn as sns
from statannotations.Annotator import Annotator
from statsmodels.stats.multitest import multipletests


from registrationViewer.registrationViewerLib import log_evaluation


# mean durations
def plot_duration_by_task_and_transform(df: pd.DataFrame, type: Literal['bar', 'violin'], significance: bool = False) -> Optional[pd.DataFrame]:
    """
    Plot duration_seconds grouped by task_id and transform_type.
    Supports 'bar' (mean ± std) and 'violin' plots.
    Excludes task_ids containing 'training' and orders transform types.
    """
    df_duration = log_evaluation.compute_task_duration_by_index_v2(df)
    df_filtered = df_duration[~df_duration['patient_id'].str.contains(
        'training')]
    transform_order = ['TransformType.NONE',
                       'TransformType.LINEAR', 'TransformType.NONLINEAR']
    df_filtered['transform_type'] = pd.Categorical(
        df_filtered['transform_type'],
        categories=transform_order,
        ordered=True
    )

    plt.figure(figsize=(12, 6))
    if type == 'bar':
        ax = sns.barplot(
            data=df_filtered,
            x='task_id',
            y='duration_seconds',
            hue='transform_type',
            # hue_order=transform_order,
            errorbar='sd'
        )

        plt.ylabel('Mean Duration (seconds)')
        plt.title(
            'Mean Duration by Task and Transform Type')

    elif type == 'violin':
        ax = sns.violinplot(
            data=df_filtered,
            x='task_id',
            y='duration_seconds',
            hue='transform_type',
            hue_order=transform_order,
            split=False,
            scale='width'
        )
        plt.ylabel('Duration (seconds)')
        plt.title('Duration by Task and Transform Type')

    if significance:
        test_results = statistical_significance_duration(df)
        pairs = []
        pvalues = []
        for _, row in test_results.iterrows():
            if row['significant']:
                t_id = row['task_id']
                t1, t2 = row['pair'].split(' vs ')
                idx1 = transform_order.index(t1)
                idx2 = transform_order.index(t2)
                if idx1 > idx2:
                    t1, t2 = t2, t1
                pairs.append(((t_id, t1), (t_id, t2)))
                pvalues.append(row['pval_corrected'])

        annotator = Annotator(ax, pairs, data=df_filtered,
                              x='task_id', y='duration_seconds', hue='transform_type')

        line_height = .02 if type == 'bar' else .2

        annotator.configure(
            test=None,
            text_format='star',
            line_height=line_height,
        )
        annotator.set_pvalues_and_annotate(pvalues)

        return test_results

    plt.legend(title='Transform Type')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

    return None


def statistical_significance_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each task_id, do pairwise t-tests comparing transform types on duration_seconds.
    Apply Bonferroni correction.
    """
    df_duration = log_evaluation.compute_task_duration_by_index_v2(df)
    df_filtered = df_duration[~df_duration['patient_id'].str.contains(
        'training')]
    results = []

    for task_id, group in df_filtered.groupby('task_id'):
        types = group['transform_type'].unique()
        pairs = [(a, b) for i, a in enumerate(types) for b in types[i+1:]]
        for a, b in pairs:
            data_a = group[group['transform_type'] == a]['duration_seconds']
            data_b = group[group['transform_type'] == b]['duration_seconds']
            stat, pval = ttest_ind(data_a, data_b)
            results.append({
                'task_id': task_id,
                'pair': f"{a} vs {b}",
                'pval_raw': pval
            })

    df_results = pd.DataFrame(results)
    corrected = multipletests(df_results['pval_raw'], method='bonferroni')
    df_results['pval_corrected'] = corrected[1]
    df_results['significant'] = corrected[0]
    return df_results


def is_point_inside_roi(
    point: np.ndarray,
    center: list[float],
    size: list[float]
) -> bool:
    """
    Check if a point is inside an axis-aligned ROI box.
    """
    size_np = np.array(size) / 2.0
    local_point = point - np.array(center)
    return np.all(np.abs(local_point) <= size_np)


def get_recurrence_gt():

    path_neg = "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/negative"
    path_pos = "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/positive"

    # all folders in path_neg
    folders_neg = [f for f in os.listdir(
        path_neg) if os.path.isdir(os.path.join(path_neg, f))]
    folders_pos = [f for f in os.listdir(
        path_pos) if os.path.isdir(os.path.join(path_pos, f))]

    gt = {}

    for neg in folders_neg:
        gt[neg] = None

    for pos in folders_pos:
        path_pat = path_pos + "/" + pos + "/preprocessed"

        folders_studies = [f for f in os.listdir(
            path_pat) if os.path.isdir(os.path.join(path_pat, f))]
        folders_studies.sort()

        study_b = folders_studies[1]

        path_annotations = path_pat + "/" + study_b + "/annotations"

        # list all files in path_annotations
        recurrence = [f for f in os.listdir(
            path_annotations) if "roi_recurrence" in f]
        if len(recurrence) == 0:
            raise FileNotFoundError(
                f"No recurrence annotation found in {path_annotations}")

        if len(recurrence) > 1:
            raise FileExistsError(
                f"Multiple recurrence annotations found in {path_annotations}")

        path_roi = path_annotations + "/" + recurrence[0]

        with open(path_roi, 'r') as f:
            lines = f.read()
            data = json.loads(lines)

            roi = data['markups'][0]

            center = np.array(roi['center'])
            size = np.array(roi['size'])

            gt[pos] = {'center': center,
                       'size': size}

    return gt


def get_rad_recurrence(path_rad: str):

    # list all folders in path_rad using glob
    folders = glob.glob(os.path.join(path_rad, '*/'))

    folders = [f for f in folders if os.path.isdir(
        f) and "training" not in f.split('/')[-2]]

    # list all files

    rt = {}

    for f in folders:
        files = glob.glob(os.path.join(f, '*/*'))

        files = [f for f in files if "recurrence_" in f.split(
            '/')[-1] and f.endswith('.mrk.json')]

        if len(files) == 0:
            rt[f.split('/')[-2]] = None
            continue

        if len(files) > 1:
            raise FileExistsError(
                f"Multiple recurrence annotations found in {f}")

        with open(files[0], 'r') as file:
            lines = file.read()
            data = json.loads(lines)

            position = data['markups'][0]['controlPoints'][0]["position"]

            rt[f.split('/')[-2]] = {'position': position}

    return rt


def get_recurrence_present_values(gt: Dict[str, None | Dict[str, np.ndarray]], rt: Dict[str, None | Dict[str, np.ndarray]]) -> Tuple[int, int, int, int]:

    # calculate true positive rate

    tpr = 0
    fpr = 0
    tnr = 0
    fnr = 0

    correct = 0

    result = {}

    for pat, val in gt.items():

        gt_val = val is not None
        rt_val = rt.get(pat) is not None

        if gt_val and rt_val:
            tpr += 1
            correct += 1
        elif gt_val and not rt_val:
            fnr += 1
        elif not gt_val and rt_val:
            fpr += 1
        elif not gt_val and not rt_val:
            tnr += 1
            correct += 1

        result[pat] = gt_val == rt_val

    return tpr/18, 1 - tnr/18, tnr/18, 1 - tpr/18, correct/36, result
