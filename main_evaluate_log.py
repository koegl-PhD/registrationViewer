from typing import Tuple, List
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from registrationViewer.registrationViewerLib import log_evaluation, all_evaluations

path = r"/home/fryderyk/Downloads/rad_test.log"

df = log_evaluation.load_log_v2_to_df(path)

all_evaluations.plot_duration_by_task_and_transform(
    df, type='bar', significance=True)
all_evaluations.plot_duration_by_task_and_transform(
    df, type='violin', significance=True)
# print 5th and 5th last row from the df

stats = all_evaluations.statistical_significance_duration(df)

# save stats to .csv
path = "/home/fryderyk/Documents/code/registrationViewer/stats.csv"
# stats.to_csv(path, index=False)


x = 0
