import matplotlib.pyplot as plt
import pandas as pd

from registrationViewer.registrationViewerLib import log_evaluation


def plot_duration_by_task_and_transform(df: pd.DataFrame) -> None:
    """
    Plot mean duration_seconds grouped by task_id and transform_type as grouped bar chart,
    with standard deviation as error bars. Excludes task_ids containing 'training',
    and orders transform types as NONE, LINEAR, NONLINEAR.
    """

    df_duration = log_evaluation.compute_task_duration_by_index_v2(df)
    df_filtered = df_duration[~df_duration['task_id'].str.contains('training')]

    grouped_mean = df_filtered.groupby(['task_id', 'transform_type'], as_index=False)[
        'duration_seconds'].mean()
    grouped_std = df_filtered.groupby(['task_id', 'transform_type'], as_index=False)[
        'duration_seconds'].std()

    mean_pivot = grouped_mean.pivot(
        index='task_id', columns='transform_type', values='duration_seconds')
    std_pivot = grouped_std.pivot(
        index='task_id', columns='transform_type', values='duration_seconds')

    transform_order = ['TransformType.NONE',
                       'TransformType.LINEAR', 'TransformType.NONLINEAR']
    mean_pivot = mean_pivot[transform_order]
    std_pivot = std_pivot[transform_order]

    ax = mean_pivot.plot(
        kind='bar',
        yerr=std_pivot.values.T,
        capsize=4,
        figsize=(10, 6)
    )

    plt.ylabel('Mean Duration (seconds)')
    plt.title('Mean Duration by Task and Transform Type (Excluding Training Tasks)')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Transform Type')
    plt.tight_layout()
    plt.show()
