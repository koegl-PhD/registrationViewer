from statannotations.Annotator import Annotator
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import ttest_ind
import seaborn as sns
from statsmodels.stats.multitest import multipletests

from typing import Literal

from registrationViewer.registrationViewerLib import log_evaluation


# mean durations
def plot_duration_by_task_and_transform(df: pd.DataFrame, type: Literal['bar', 'violin'], significance: bool = False) -> None:
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

    plt.legend(title='Transform Type')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()


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
