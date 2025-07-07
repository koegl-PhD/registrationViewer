import matplotlib.pyplot as plt
import pandas as pd

from registrationViewer.registrationViewerLib import log_evaluation


def plot_duration_by_task_and_transform(df: pd.DataFrame) -> None:
    """
    Plot mean duration_seconds grouped by task_id and transform_type as grouped bar chart,
    excluding task_ids containing 'training', and ordering transform types as NONE, LINEAR, NONLINEAR.
    """

    df_duration = log_evaluation.compute_task_duration_by_index_v2(df)

    df_filtered = df_duration[~df_duration['task_id'].str.contains('training')]
    grouped = df_filtered.groupby(['task_id', 'transform_type'], as_index=False)[
        'duration_seconds'].mean()
    pivot = grouped.pivot(
        index='task_id', columns='transform_type', values='duration_seconds')
    transform_order = ['TransformType.NONE',
                       'TransformType.LINEAR', 'TransformType.NONLINEAR']
    pivot = pivot[transform_order]
    pivot.plot(kind='bar', figsize=(10, 6))
    plt.ylabel('Mean Duration (seconds)')
    plt.title('Mean Duration by Task and Transform Type (Excluding Training Tasks)')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Transform Type')
    plt.tight_layout()
    plt.show()
