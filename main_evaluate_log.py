from typing import Tuple, List
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from registrationViewer.registrationViewerLib import log_evaluation, all_evaluations

path = r"/home/koeglf/Downloads/rad_test.log"

df = log_evaluation.load_log_v2_to_df(path)

# all_evaluations.plot_duration_by_task_and_transform(
#     df, type='bar', significance=True)
# all_evaluations.plot_duration_by_task_and_transform(
#     df, type='violin', significance=True)
# print 5th and 5th last row from the df

stats = all_evaluations.statistical_significance_duration(df)

gt = all_evaluations.get_recurrence_gt()

rt = all_evaluations.get_rad_recurrence(
    r"/home/koeglf/data/registrationStudy/study_output/rad_ihssan_20250704/")


tpr, fpr, tnr, fnr, accuracy, result = all_evaluations.get_recurrence_present_values(
    gt, rt)

# save stats to .csv
path = "/home/fryderyk/Documents/code/registrationViewer/stats.csv"
# stats.to_csv(path, index=False)


x = 0


"""
incorrcet recurrence:
a9ebcF7RKU4 (linear)
6vkfAvGWUPg (none)
I307KZkh1VM (nonlinear)
JlS0Cl1K0 (nonlinear)
7sp2FiVa4WI (none)
2pO8AtRxHAg (none)
TwU508CCA9Y (linear)
"""
