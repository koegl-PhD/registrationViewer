from typing import Tuple, List
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from registrationViewer.registrationViewerLib import log_evaluation, all_evaluations

path = r"/home/fryderyk/Downloads/rad_test.log"

df = log_evaluation.load_log_v2_to_df(path)


# print 5th and 5th last row from the df

df_duration = log_evaluation.compute_task_duration_by_index_v2(df)

all_evaluations.plot_duration_by_task_and_transform_violin(df)


def get_recurrence_durations(df: pd.DataFrame) -> Tuple[List[float], List[float], List[float]]:
    """
    Return three lists of duration_seconds for 'recurrence' tasks,
    split by transform_type in order: NONE, LINEAR, NONLINEAR.
    """
    df_recurrence = df[df['task_id'] == 'recurrence']
    none = df_recurrence[df_recurrence['transform_type']
                         == 'TransformType.NONE']['duration_seconds'].tolist()
    linear = df_recurrence[df_recurrence['transform_type']
                           == 'TransformType.LINEAR']['duration_seconds'].tolist()
    nonlinear = df_recurrence[df_recurrence['transform_type']
                              == 'TransformType.NONLINEAR']['duration_seconds'].tolist()
    return none, linear, nonlinear


rec = get_recurrence_durations(df_duration)

print(f"none: {rec[0]}")
print(f"linear: {rec[1]}")
print(f"nonlinear: {rec[2]}")

x = 0

'09:39:35,218'
'09:40:06,188'
'09:40:24,199'
'09:41:19,450'
