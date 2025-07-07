import pandas as pd
import numpy as np


def parse_log_line_v2(line):
    parts = line.strip().split(" ~ ")
    if len(parts) < 10:
        return None

    timestamp = parts[0]
    module = parts[1]
    log_level = parts[2]
    event_type = parts[3]
    task_index = parts[4]
    user_id = parts[5]
    patient_id = parts[6]
    transform_type = parts[7]
    task_id = parts[8]
    action = parts[9]
    detail = " ~ ".join(parts[10:]) if len(parts) > 10 else None

    return {
        "timestamp": timestamp,
        "module": module,
        "log_level": log_level,
        "event_type": event_type,
        "task_index": task_index,
        "user_id": user_id,
        "patient_id": patient_id,
        "transform_type": transform_type,
        "task_id": task_id,
        "action": action,
        "detail": detail
    }


def load_log_v2_to_df(file_path):
    with open(file_path, "r") as file:
        rows = []
        for line in file:
            parsed = parse_log_line_v2(line)
            if parsed:
                rows.append(parsed)
    return pd.DataFrame(rows)


def compute_scroll_stats_grouped_v2(df):
    # --- Slider Scroll ---
    slider_df = df[df['action'] == 'Slider_Scroll'].copy()
    slider_df = slider_df[slider_df['detail'].notnull()]
    slider_df['position'] = slider_df['detail'].str.extract(
        r'pos=([-+]?[0-9]*\.?[0-9]+)').astype(float)

    # Sort and compute pairwise distance per group
    slider_df.sort_values(by=['user_id', 'patient_id', 'transform_type',
                          'task_id', 'task_index', 'timestamp'], inplace=True)
    slider_df['position_shifted'] = slider_df.groupby(
        ['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'])['position'].shift(1)
    slider_df['distance_delta'] = (
        slider_df['position'] - slider_df['position_shifted']).abs()

    slider_stats = slider_df.groupby(['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index']).agg(
        slider_total_distance=('distance_delta', 'sum'),
        slider_usage_count=('position', 'count')
    ).reset_index()

    # --- Wheel Scroll ---
    wheel_df = df[df['action'] == 'Wheel_Scroll'].copy()
    wheel_df = wheel_df[wheel_df['detail'].notnull()]
    wheel_df['delta'] = wheel_df['detail'].str.extract(
        r'd=([-+]?[0-9]+)').astype(float)

    wheel_stats = wheel_df.groupby(['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'])[
        'delta'].value_counts().unstack(fill_value=0).reset_index()
    wheel_stats.rename(columns={-1.0: 'wheel_scroll_d_-1_count',
                       1.0: 'wheel_scroll_d_1_count'}, inplace=True)

    # Merge both stats
    combined_stats = pd.merge(slider_stats, wheel_stats, on=[
                              'user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'], how='outer')
    combined_stats.fillna(0, inplace=True)

    return combined_stats


def compute_task_scroll_stats_v2(df):
    # --- Helper to extract 2D coordinates from either format ---
    def extract_pos_2d(df):
        pos_xy = df['detail'].str.extract(r'\(([-+]?\d+),\s*([-+]?\d+)\)')
        return pos_xy.astype(float).rename(columns={0: 'x', 1: 'y'})

    # Extract d from detail field
    def extract_d(df):
        return df['detail'].str.extract(r'd=([-+]?[0-9]*\.?[0-9]+)').astype(float)

    # Filter for mouse events with usable detail or coordinate string
    base_df = df[df['event_type'] == 'U_MOUSE'].copy()
    base_df = base_df[base_df['detail'].notnull(
    ) | base_df['action'].str.contains(r'\(\d+,')]

    result_frames = []
    task_types = ['Pan', 'Zoom', 'Window_Level', 'Drag_Scroll']

    for task in task_types:
        task_df = base_df[base_df['action'].str.startswith(task)].copy()
        pos_df = extract_pos_2d(task_df)
        task_df = task_df.join(pos_df)

        task_df.sort_values(by=['user_id', 'patient_id', 'transform_type',
                            'task_id', 'task_index', 'timestamp'], inplace=True)
        task_df[['x_prev', 'y_prev']] = task_df.groupby(
            ['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'])[['x', 'y']].shift(1)
        task_df['distance'] = np.sqrt(
            (task_df['x'] - task_df['x_prev'])**2 + (task_df['y'] - task_df['y_prev'])**2)

        agg = task_df.groupby(['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index']).agg(
            **{f'{task.lower()}_total_distance': ('distance', 'sum'),
               f'{task.lower()}_usage_count': ('x', 'count')}
        ).reset_index()

        result_frames.append(agg)

    # --- Zoom-specific: sum of d and d-distance ---
    zoom_df = base_df[base_df['action'].str.startswith('Zoom')].copy()
    zoom_df['d_value'] = extract_d(zoom_df)
    zoom_df.sort_values(by=['user_id', 'patient_id', 'transform_type',
                        'task_id', 'task_index', 'timestamp'], inplace=True)
    zoom_df['d_prev'] = zoom_df.groupby(
        ['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'])['d_value'].shift(1)
    zoom_df['d_delta'] = zoom_df['d_value'] - zoom_df['d_prev']

    zoom_d_sum = zoom_df.groupby(['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'])[
        'd_value'].sum().reset_index()
    zoom_d_sum.rename(columns={'d_value': 'zoom_total_d_change'}, inplace=True)

    zoom_d_dist = zoom_df['d_delta'].abs().groupby([
        zoom_df['user_id'],
        zoom_df['patient_id'],
        zoom_df['transform_type'],
        zoom_df['task_id'],
        zoom_df['task_index']
    ]).sum().reset_index()
    zoom_d_dist.rename(
        columns={'d_delta': 'zoom_total_d_distance'}, inplace=True)

    # Merge all statistics
    from functools import reduce
    merged = reduce(lambda left, right: pd.merge(
        left, right, on=['user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'], how='outer'),
        result_frames)

    merged = pd.merge(merged, zoom_d_sum, on=[
                      'user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'], how='outer')
    merged = pd.merge(merged, zoom_d_dist, on=[
                      'user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'], how='outer')

    merged.fillna(0, inplace=True)
    return merged


def compute_task_duration_by_index_v2(df):
    # Ensure timestamp is in datetime format
    df['timestamp'] = pd.to_datetime(
        df['timestamp'], format="%Y-%m-%d %H:%M:%S,%f", errors='coerce')

    # Filter for U_BUTTON events with action markers
    task_control_df = df[(df['event_type'] == 'U_BUTTON') & (
        df['action'].isin(['User started task', 'Next task']))].copy()

    # Split start and end markers
    start_df = task_control_df[task_control_df['action']
                               == 'User started task'].copy()
    end_df = task_control_df[task_control_df['action'] == 'Next task'].copy()

    # Select relevant columns
    start_df = start_df[['user_id', 'patient_id',
                         'transform_type', 'task_id', 'task_index', 'timestamp']]
    end_df = end_df[['user_id', 'patient_id', 'transform_type',
                     'task_id', 'task_index', 'timestamp']]
    start_df.rename(columns={'timestamp': 'start_time'}, inplace=True)
    end_df.rename(columns={'timestamp': 'end_time'}, inplace=True)

    # Merge start and end rows by full task identity
    duration_df = pd.merge(start_df, end_df, on=[
                           'user_id', 'patient_id', 'transform_type', 'task_id', 'task_index'], how='inner')

    # Compute duration
    duration_df['duration_seconds'] = (
        duration_df['end_time'] - duration_df['start_time']).dt.total_seconds()

    return duration_df
