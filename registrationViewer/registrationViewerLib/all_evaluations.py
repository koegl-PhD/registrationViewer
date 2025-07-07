import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

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


def plot_duration_by_task_and_transform_violin(df: pd.DataFrame) -> None:
    """
    Plot duration_seconds as violin plots grouped by task_id and transform_type.
    Excludes task_ids containing 'training' and orders transform types.
    """
    df_duration = log_evaluation.compute_task_duration_by_index_v2(df)
    df_filtered = df_duration[~df_duration['task_id'].str.contains('training')]

    transform_order = ['TransformType.NONE',
                       'TransformType.LINEAR', 'TransformType.NONLINEAR']

    plt.figure(figsize=(12, 6))
    sns.violinplot(
        data=df_filtered,
        x='task_id',
        y='duration_seconds',
        hue='transform_type',
        order=sorted(df_filtered['task_id'].unique()),
        hue_order=transform_order,
        split=False,
        scale='width',      # keeps violins same width
        # bw=0.5,             # adjust for smoother violins
        # inner='quartile'    # clearer summary inside violins
    )

    plt.ylabel('Duration (seconds)')
    plt.title(
        'Duration by Task and Transform Type (Violin Plot, Excluding Training Tasks)')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Transform Type')
    plt.tight_layout()
    plt.show()
