import matplotlib.pyplot as plt
import math
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate, translate
import geopandas as gpd
from pyproj import Transformer

import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point

def plot_four_sequences(projected_polygon, flight_lines, seq_A, seq_B, seq_C, seq_D, epsg_code):
    sequences = {'A: 原始顺序': seq_A,
                 'B: 整体逆序': seq_B,
                 'C: 分段内反': seq_C,
                 'D: 段序+内反': seq_D}

    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    axes = axes.flatten()

    for idx, (title, seq) in enumerate(sequences.items()):
        ax = axes[idx]

        # 绘制区域和航线
        gpd.GeoSeries([projected_polygon]).plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1)
        flight_lines.plot(ax=ax, color='blue', linewidth=1)

        # 获取点和时间
        all_points = [pt for pt, _ in seq]
        all_times = [t for _, t in seq]

        # 绘制曝光点
        gdf_points = gpd.GeoDataFrame({'timestamp': all_times}, geometry=all_points, crs=f"EPSG:{epsg_code}")
        gdf_points.plot(ax=ax, color='red', markersize=8)

        # 标注序号和时间
        for i, (pt, t) in enumerate(zip(all_points, all_times)):
            ax.text(pt.x, pt.y, f"{i+1}\n{t:.1f}s", fontsize=6, ha='center', va='center', color='darkred')

        ax.set_title(title)
        ax.set_aspect('equal')

    plt.tight_layout()
    plt.show()

def plot_best_plan(result):
    fig, ax = plt.subplots(figsize=(10, 10))

    # 绘制区域边界
    gpd.GeoSeries([result['projected_polygon']]).plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1)

    # 绘制航迹线
    result['flight_lines'].plot(ax=ax, color='blue', linewidth=1)

    # 绘制最佳航迹点
    best_plan = result['best_plan_projected']  # [(Point, time), ...]
    points = [pt for pt, _ in best_plan]
    times = [t for _, t in best_plan]

    gdf_points = gpd.GeoDataFrame({'time': times}, geometry=points, crs=f"EPSG:{result['epsg']}")
    gdf_points.plot(ax=ax, color='red', markersize=8)

    # 标注编号和时间
    for i, (pt, t) in enumerate(zip(points, times)):
        ax.text(pt.x, pt.y, f"{i+1}\n{t:.1f}s", fontsize=6, ha='center', va='center', color='darkred')

    ax.set_title(f"Best UAV Flight Plan (EPSG:{result['epsg']})")
    ax.set_aspect('equal')
    plt.tight_layout()
    plt.show()

def generate_uav_flight_plan(polygon_wgs84, altitude, vfov_deg, hfov_deg, speed, overlap_front,
                             overlap_side, ground_station, turn_time_buffer=2.0):
    longitudes = [pt[0] for pt in polygon_wgs84]
    center_lon = sum(longitudes) / len(longitudes)
    zone = int((center_lon - 1.5) / 3) + 1
    epsg_code = 4509 + zone
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)
    projected_ground_station = transformer.transform(ground_station[0], ground_station[1])
    # 投影 polygon
    projected_coords = [transformer.transform(lon, lat) for lon, lat in polygon_wgs84]
    projected_polygon = Polygon(projected_coords)

    # 航带宽度和间距
    hfov_rad = math.radians(hfov_deg)
    footprint_width = 2 * altitude * math.tan(hfov_rad / 2)
    lane_spacing = footprint_width * (1 - overlap_side)

    vfov_rad = math.radians(vfov_deg)
    footprint_height = 2 * altitude * math.tan(vfov_rad / 2)

    # 主方向（最小外接矩形最长边）
    min_rect = projected_polygon.minimum_rotated_rectangle
    coords = list(min_rect.exterior.coords)
    edges = [(coords[i], coords[i + 1]) for i in range(4)]
    edge_lengths = [math.hypot(b[1][0] - b[0][0], b[1][1] - b[0][1]) for b in edges]
    longest_edge = edges[edge_lengths.index(max(edge_lengths))]
    dx = longest_edge[1][0] - longest_edge[0][0]
    dy = longest_edge[1][1] - longest_edge[0][1]
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    # 垂直方向向量
    dx_perp = -math.sin(angle_rad)
    dy_perp = math.cos(angle_rad)

    projections = [x * dx_perp + y * dy_perp for x, y in projected_coords]
    min_proj, max_proj = min(projections), max(projections)
    mid_proj = (min_proj + max_proj) / 2
    span_proj = max_proj - min_proj
    n_lanes = int(span_proj / lane_spacing) + 2

    lines = []
    diag = projected_polygon.length
    centroid = projected_polygon.centroid
    projected_polygon_extended = min_rect.buffer(lane_spacing) # 扩大一定缓冲区距离以囊括边缘

    for i in range(n_lanes + 1):
        offset = min_proj + i * lane_spacing - mid_proj
        base = LineString([(-diag, 0), (diag, 0)])
        moved = translate(base, yoff=offset)
        rotated = rotate(moved, angle_deg, origin=(0, 0))
        final = translate(rotated, xoff=centroid.x, yoff=centroid.y)
        clipped = final.intersection(projected_polygon_extended)
        if not clipped.is_empty:
            if clipped.geom_type == 'MultiLineString':
                lines.extend(clipped.geoms)
            elif clipped.geom_type == 'LineString':
                lines.append(clipped)

    # 曝光点序列（有顺序）
    exposure_sequences = []
    exposure_interval = footprint_height * (1 - overlap_front)
    cumulative_time = 0
    last_end_point = None
    turn_time = 0
    for idx, line in enumerate(lines):
        length = line.length
        n_pts = int(length // exposure_interval)
        if n_pts == 0:
            continue

        # Step 1: 先生成原始点列表
        raw_pts = [line.interpolate(i * exposure_interval) for i in range(n_pts + 1)]


        if idx % 2 == 1:
            raw_pts.reverse()

        # Step 2: 获取当前航线起点（原始顺序）
        start_pt = raw_pts[0]

        # Step 3: 转弯时间（从上一条航线终点飞到当前起点）
        if last_end_point is not None:
            dist = last_end_point.distance(start_pt)
            turn_time = dist / speed + turn_time_buffer
            cumulative_time += turn_time

        # Step 4: 计算每个点的时间戳（时间严格按顺序）
        times = [cumulative_time + i * exposure_interval / speed for i in range(n_pts + 1)]


        # Step 6: 组合为 (pt, time)
        seq = list(zip(raw_pts, times))

        # Step 7: 更新状态
        last_end_point = raw_pts[-1]  # 原始方向终点不变
        cumulative_time += length / speed
        exposure_sequences.append(seq)

    interval_time = exposure_interval / speed
    # 6. 时间重算逻辑
    def recompute_times(sequences, interval_time, turn_time):
        new_sequences = []
        cumulative_time = 0
        for s_idx, seg in enumerate(sequences):
            new_seg = []
            for p_idx, (pt, _) in enumerate(seg):
                if s_idx > 0 and p_idx == 0:
                    cumulative_time += turn_time
                elif p_idx > 0:
                    cumulative_time += interval_time
                new_seg.append((pt, cumulative_time))
            new_sequences.append(new_seg)
        return new_sequences

    # A：原始顺序
    new_A = recompute_times(exposure_sequences, interval_time, turn_time)

    # B：整体逆序
    seq_B = list(reversed(exposure_sequences))
    new_B = recompute_times(seq_B, interval_time, turn_time)

    # C：分段内反
    seq_C = [list(reversed(seg)) for seg in exposure_sequences]
    new_C = recompute_times(seq_C, interval_time, turn_time)

    # D：段序+内反
    seq_D = [list(reversed(seg)) for seg in reversed(exposure_sequences)]
    new_D = recompute_times(seq_D, interval_time, turn_time)

    # 扁平化
    flatten_A = [item for seg in new_A for item in seg]
    flatten_B = [item for seg in new_B for item in seg]
    flatten_C = [item for seg in new_C for item in seg]
    flatten_D = [item for seg in new_D for item in seg]

    start_points = [
        flatten_A[0][0],  # A 起点
        flatten_B[0][0],  # B 起点
        flatten_C[0][0],  # C 起点
        flatten_D[0][0],  # D 起点
    ]

    gs_point = Point(projected_ground_station)
    distances = [gs_point.distance(sp) for sp in start_points]
    min_index = distances.index(min(distances))
    candidates = [flatten_A, flatten_B, flatten_C, flatten_D]
    best_plan = candidates[min_index]
    inverse_transformer = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
    def convert_to_wgs84(point_time_list, altitude):
        return [(inverse_transformer.transform(pt.x, pt.y)[0],
                 inverse_transformer.transform(pt.x, pt.y)[1],
                 altitude, t) for pt, t in point_time_list]
    absolute_altitude = altitude + ground_station[2]
    best_plan_wgs84 = convert_to_wgs84(best_plan, absolute_altitude)
    gdf_lines = gpd.GeoDataFrame(geometry=lines, crs=f"EPSG:{epsg_code}")
    return {
        'epsg': epsg_code,
        'projected_polygon': projected_polygon,
        'flight_lines': gdf_lines,
        'best_plan_projected': best_plan,  # (Point, time)
        'wgs84_xyz_time': best_plan_wgs84,
    }

    # 展平曝光点与时间
    # all_points = [pt for seq in exposure_sequences for (pt, _) in seq]
    # all_times = [t for seq in exposure_sequences for (_, t) in seq]
    #
    #
    # gdf_points = gpd.GeoDataFrame({'timestamp': all_times}, geometry=all_points, crs=f"EPSG:{epsg_code}")
    #
    #
    # plot_four_sequences(projected_polygon, gdf_lines, flatten_A, flatten_B, flatten_C, flatten_D, epsg_code)

    # 构造逆变换器（投影 → WGS84）
    #
    # wgs84_A = convert_to_wgs84(flatten_A, altitude)
    # wgs84_B = convert_to_wgs84(flatten_B, altitude)
    # wgs84_C = convert_to_wgs84(flatten_C, altitude)
    # wgs84_D = convert_to_wgs84(flatten_D, altitude)
    #
    # # 将曝光点转换回 WGS84 坐标，并添加航高 Z
    # wgs84_points_with_time = []
    # for pt, t in [(pt, t) for seq in exposure_sequences for pt, t in seq]:
    #     lon, lat = inverse_transformer.transform(pt.x, pt.y)
    #     wgs84_points_with_time.append((lon, lat, altitude, t))

    # return {
    #     'epsg': epsg_code,
    #     'projected_polygon': projected_polygon,
    #     'flight_lines': gdf_lines,
    #     'exposure_points': gdf_points,
    #     'exposure_sequences': exposure_sequences,
    #     'point_time_list': [(pt, t) for seq in exposure_sequences for pt, t in seq],
    #     'wgs84_xyz_time': best_plan_wgs84,
    # }


def plot_all_flight_plans(result):
    projected_polygon = result['projected_polygon']
    flight_lines = result['flight_lines']
    plans = result['plans_by_corner']

    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    axes = axes.flatten()

    for idx, (corner_name, plan) in enumerate(plans.items()):
        ax = axes[idx]

        # 绘制区域和航线
        gpd.GeoSeries([projected_polygon]).plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1)
        flight_lines.plot(ax=ax, color='blue', linewidth=1)

        # 获取点序列
        all_points = [pt for seq in plan['sequences'] for pt, _ in seq]
        all_times = [t for seq in plan['sequences'] for _, t in seq]

        # 转换为 GeoDataFrame 以便绘图
        gdf_points = gpd.GeoDataFrame({'timestamp': all_times}, geometry=all_points, crs=flight_lines.crs)
        gdf_points.plot(ax=ax, color='red', markersize=8)

        # 添加编号和时间标签
        for i, (pt, t) in enumerate(zip(all_points, all_times)):
            ax.text(pt.x, pt.y, f"{i+1}\n{t:.1f}s", fontsize=6, ha='center', va='center', color='darkred')

        ax.set_title(f"Plan {corner_name} (EPSG:{result['epsg']})")
        ax.set_aspect('equal')

    plt.tight_layout()
    plt.show()

def generate_uav_flight_plan2(polygon_wgs84, altitude, vfov_deg, hfov_deg, speed, overlap_front, overlap_side, turn_time_buffer=2.0):
    # 1. 坐标转换：WGS84 -> 投影坐标
    longitudes = [pt[0] for pt in polygon_wgs84]
    center_lon = sum(longitudes) / len(longitudes)
    zone = int((center_lon - 1.5) / 3) + 1
    epsg_code = 4509 + zone
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)

    projected_coords = [transformer.transform(lon, lat) for lon, lat in polygon_wgs84]
    projected_polygon = Polygon(projected_coords)

    # 2. 计算航带参数
    hfov_rad = math.radians(hfov_deg)
    vfov_rad = math.radians(vfov_deg)
    footprint_width = 2 * altitude * math.tan(hfov_rad / 2)
    footprint_height = 2 * altitude * math.tan(vfov_rad / 2)
    lane_spacing = footprint_width * (1 - overlap_side)

    # 3. 确定航向角度
    min_rect = projected_polygon.minimum_rotated_rectangle
    coords = list(min_rect.exterior.coords)
    edges = [(coords[i], coords[i + 1]) for i in range(4)]
    edge_lengths = [math.hypot(b[1][0] - b[0][0], b[1][1] - b[0][1]) for b in edges]
    longest_edge = edges[edge_lengths.index(max(edge_lengths))]
    dx = longest_edge[1][0] - longest_edge[0][0]
    dy = longest_edge[1][1] - longest_edge[0][1]
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    # 垂直方向向量
    dx_perp = -math.sin(angle_rad)
    dy_perp = math.cos(angle_rad)

    projections = [x * dx_perp + y * dy_perp for x, y in projected_coords]
    min_proj, max_proj = min(projections), max(projections)
    mid_proj = (min_proj + max_proj) / 2
    span_proj = max_proj - min_proj
    n_lanes = int(span_proj / lane_spacing) + 2

    # 4. 生成航线
    lines = []
    diag = projected_polygon.length
    centroid = projected_polygon.centroid
    projected_polygon_extended = min_rect.buffer(lane_spacing)

    for i in range(n_lanes + 1):
        offset = min_proj + i * lane_spacing - mid_proj
        base = LineString([(-diag, 0), (diag, 0)])
        moved = translate(base, yoff=offset)
        rotated = rotate(moved, angle_deg, origin=(0, 0))
        final = translate(rotated, xoff=centroid.x, yoff=centroid.y)
        clipped = final.intersection(projected_polygon_extended)
        if not clipped.is_empty:
            if clipped.geom_type == 'MultiLineString':
                lines.extend(clipped.geoms)
            elif clipped.geom_type == 'LineString':
                lines.append(clipped)

    # 5. 生成曝光点（默认顺序）
    exposure_interval = footprint_height * (1 - overlap_front)
    cumulative_time = 0
    last_end_point = None
    exposure_sequences = []

    for idx, line in enumerate(lines):
        length = line.length
        n_pts = int(length // exposure_interval)
        if n_pts == 0:
            continue

        raw_pts = [line.interpolate(i * exposure_interval) for i in range(n_pts + 1)]
        if idx % 2 == 1:
            raw_pts.reverse()

        start_pt = raw_pts[0]
        if last_end_point is not None:
            dist = last_end_point.distance(start_pt)
            turn_time = dist / speed + turn_time_buffer
            cumulative_time += turn_time

        times = [cumulative_time + i * exposure_interval / speed for i in range(n_pts + 1)]
        seq = list(zip(raw_pts, times))

        last_end_point = raw_pts[-1]
        cumulative_time += length / speed
        exposure_sequences.append(seq)

    # 6. 逆变换器
    inverse_transformer = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)

    # 默认方案 WGS84
    wgs84_points_with_time = []
    for pt, t in [(pt, t) for seq in exposure_sequences for pt, t in seq]:
        lon, lat = inverse_transformer.transform(pt.x, pt.y)
        wgs84_points_with_time.append((lon, lat, altitude, t))

    gdf_lines = gpd.GeoDataFrame(geometry=lines, crs=f"EPSG:{epsg_code}")

    # 7. 获取最小外接矩形4个角点
    rect_coords = list(min_rect.exterior.coords)[:-1]
    corner_points = [Point(c) for c in rect_coords]

    # 辅助函数：重新排序
    def reorder_sequences(sequences, start_corner_idx):
        start_corner = corner_points[start_corner_idx]
        first_idx = min(range(len(sequences)), key=lambda i: sequences[i][0][0].distance(start_corner))
        rotated_sequences = sequences[first_idx:] + sequences[:first_idx]

        new_sequences = []
        cumulative_time = 0
        last_end_point = None
        for seq in rotated_sequences:
            pts = [pt for pt, _ in seq]

            if last_end_point and pts[0].distance(last_end_point) > pts[-1].distance(last_end_point):
                pts.reverse()

            if last_end_point:
                dist = last_end_point.distance(pts[0])
                cumulative_time += dist / speed + turn_time_buffer

            times = [cumulative_time + i * exposure_interval / speed for i in range(len(pts))]
            cumulative_time += (len(pts) - 1) * exposure_interval / speed
            new_sequences.append(list(zip(pts, times)))
            last_end_point = pts[-1]
        return new_sequences

    # 8. 生成4种起点方案
    plans_by_corner = {}
    for i in range(4):
        reordered = reorder_sequences(exposure_sequences, i)
        wgs84_points = []
        for seq in reordered:
            for pt, t in seq:
                lon, lat = inverse_transformer.transform(pt.x, pt.y)
                wgs84_points.append((lon, lat, altitude, t))
        plans_by_corner[f'start_corner_{i}'] = {
            'sequences': reordered,
            'wgs84_points': wgs84_points
        }

    return {
        'epsg': epsg_code,
        'projected_polygon': projected_polygon,
        'flight_lines': gdf_lines,
        'original_sequences': exposure_sequences,
        'wgs84_xyz_time': wgs84_points_with_time,
        'plans_by_corner': plans_by_corner
    }

if __name__ == "__main__":
    polygon_coords = [
        (114.3508317, 30.5356698),
        (114.3592425, 30.5323666),
        (114.3566078, 30.5266232),
        (114.3486309, 30.5293104)
    ]

    params = {
        'altitude': 200,    # 飞行高度
        # 'vfov_deg': 14.34,     # 垂直视场角 °
        # 'hfov_deg': 21.46,     # 水平视场角 °
        'vfov_deg': 90.34,  # 垂直视场角 °
        'hfov_deg': 120.46,  # 水平视场角 °
        'speed': 8,     # 飞行速度 m/s
        'overlap_front': 0.8,   # 航向重叠度
        'overlap_side': 0.6,    # 旁向重叠度
        'ground_station': (115.3486309, 30.5293104, 50),
        'turn_time_buffer': 3.0,  # 转弯的冗余时间 s
    }

    with open("input_config.txt", "w", encoding="utf-8") as f:
        f.write("# Polygon Coordinates (WGS84)\n")
        for lon, lat in polygon_coords:
            f.write(f"{lon:.8f}, {lat:.8f}\n")

        f.write("\n# Flight Parameters\n")
        for k, v in params.items():
            f.write(f"{k} = {v}\n")

    plan = generate_uav_flight_plan(polygon_coords, **params)
    # plot_all_flight_plans(plan)
    with open("trajectory.txt", "w", encoding="utf-8") as f:
        f.write("Lon,Lat,Z,Time\n")
        for lon, lat, z, t in plan['wgs84_xyz_time']:
            f.write(f"{lon:.8f},{lat:.8f},{z:.2f},{t:.2f}\n")
    plot_best_plan(plan)

    # # 可视化航线 + 曝光点
    # fig, ax = plt.subplots(figsize=(10, 10))
    # gpd.GeoSeries([plan['projected_polygon']]).plot(ax=ax, facecolor='none', edgecolor='black')
    # plan['flight_lines'].plot(ax=ax, color='blue', linewidth=1)
    # plan['exposure_points'].plot(ax=ax, color='red', markersize=5)
    #
    # # 添加编号
    # all_pts = plan['exposure_points'].geometry.tolist()
    # for idx, pt in enumerate(all_pts):
    #     ax.text(pt.x, pt.y, str(idx + 1), fontsize=6, color='darkred')
    #
    # ax.set_title(f"UAV Flight Plan (EPSG:{plan['epsg']})")
    # ax.set_aspect('equal')
    # plt.tight_layout()
    # plt.show()

    # # 可视化绘图
    # fig, ax = plt.subplots(figsize=(10, 10))
    # gpd.GeoSeries([plan['projected_polygon']]).plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1)
    # plan['flight_lines'].plot(ax=ax, color='blue', linewidth=1)
    # plan['exposure_points'].plot(ax=ax, color='red', markersize=8)
    #
    # # 添加编号和时间标签
    # for idx, (pt, t) in enumerate(plan['point_time_list']):
    #     label = f"{idx + 1}\n{t:.1f}s"
    #     ax.text(pt.x, pt.y, label, fontsize=6, ha='center', va='center', color='darkred')
    #
    # ax.set_title(f"UAV Flight Plan (EPSG:{plan['epsg']})")
    # ax.set_aspect('equal')
    # plt.tight_layout()
    # plt.show()




# import math
# from shapely.geometry import Polygon, LineString
# from shapely.affinity import rotate, translate
# import geopandas as gpd
# from pyproj import Transformer
# import matplotlib.pyplot as plt
#
# def generate_uav_flight_plan(polygon_wgs84, altitude, vfov_deg, hfov_deg, speed, overlap_front, overlap_side, turn_time_buffer=2.0):
#     longitudes = [pt[0] for pt in polygon_wgs84]
#     center_lon = sum(longitudes) / len(longitudes)
#     zone = int((center_lon - 1.5) / 3) + 1
#     epsg_code = 4509 + zone
#     transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)
#
#     # 投影 polygon
#     projected_coords = [transformer.transform(lon, lat) for lon, lat in polygon_wgs84]
#     projected_polygon = Polygon(projected_coords)
#
#     # 航带宽度和间距
#     hfov_rad = math.radians(hfov_deg)
#     footprint_width = 2 * altitude * math.tan(hfov_rad / 2)
#     lane_spacing = footprint_width * (1 - overlap_side)
#
#     vfov_rad = math.radians(vfov_deg)
#     footprint_height = 2 * altitude * math.tan(vfov_rad / 2)
#
#     # 主方向（最小外接矩形最长边）
#     min_rect = projected_polygon.minimum_rotated_rectangle
#     coords = list(min_rect.exterior.coords)
#     edges = [(coords[i], coords[i + 1]) for i in range(4)]
#     edge_lengths = [math.hypot(b[1][0] - b[0][0], b[1][1] - b[0][1]) for b in edges]
#     longest_edge = edges[edge_lengths.index(max(edge_lengths))]
#     dx = longest_edge[1][0] - longest_edge[0][0]
#     dy = longest_edge[1][1] - longest_edge[0][1]
#     angle_rad = math.atan2(dy, dx)
#     angle_deg = math.degrees(angle_rad)
#
#     # 垂直方向向量
#     dx_perp = -math.sin(angle_rad)
#     dy_perp = math.cos(angle_rad)
#
#     projections = [x * dx_perp + y * dy_perp for x, y in projected_coords]
#     min_proj, max_proj = min(projections), max(projections)
#     mid_proj = (min_proj + max_proj) / 2
#     span_proj = max_proj - min_proj
#     n_lanes = int(span_proj / lane_spacing) + 2
#
#     lines = []
#     diag = projected_polygon.length
#     centroid = projected_polygon.centroid
#     projected_polygon_extended = min_rect.buffer(lane_spacing) # 扩大一定缓冲区距离以囊括边缘
#
#     for i in range(n_lanes + 1):
#         offset = min_proj + i * lane_spacing - mid_proj
#         base = LineString([(-diag, 0), (diag, 0)])
#         moved = translate(base, yoff=offset)
#         rotated = rotate(moved, angle_deg, origin=(0, 0))
#         final = translate(rotated, xoff=centroid.x, yoff=centroid.y)
#         clipped = final.intersection(projected_polygon_extended)
#         if not clipped.is_empty:
#             if clipped.geom_type == 'MultiLineString':
#                 lines.extend(clipped.geoms)
#             elif clipped.geom_type == 'LineString':
#                 lines.append(clipped)
#
#     # 曝光点序列（有顺序）
#     exposure_sequences = []
#     exposure_interval = footprint_height * (1 - overlap_front)
#     cumulative_time = 0
#     last_end_point = None
#
#     for idx, line in enumerate(lines):
#         length = line.length
#         n_pts = int(length // exposure_interval)
#         if n_pts == 0:
#             continue
#
#         # Step 1: 先生成原始点列表
#         raw_pts = [line.interpolate(i * exposure_interval) for i in range(n_pts + 1)]
#
#
#         if idx % 2 == 1:
#             raw_pts.reverse()
#
#         # Step 2: 获取当前航线起点（原始顺序）
#         start_pt = raw_pts[0]
#
#         # Step 3: 转弯时间（从上一条航线终点飞到当前起点）
#         if last_end_point is not None:
#             dist = last_end_point.distance(start_pt)
#             turn_time = dist / speed + turn_time_buffer
#             cumulative_time += turn_time
#
#         # Step 4: 计算每个点的时间戳（时间严格按顺序）
#         times = [cumulative_time + i * exposure_interval / speed for i in range(n_pts + 1)]
#
#
#         # Step 6: 组合为 (pt, time)
#         seq = list(zip(raw_pts, times))
#
#         # Step 7: 更新状态
#         last_end_point = raw_pts[-1]  # 原始方向终点不变
#         cumulative_time += length / speed
#         exposure_sequences.append(seq)
#
#
#
#     # 展平曝光点与时间
#     all_points = [pt for seq in exposure_sequences for (pt, _) in seq]
#     all_times = [t for seq in exposure_sequences for (_, t) in seq]
#
#     gdf_lines = gpd.GeoDataFrame(geometry=lines, crs=f"EPSG:{epsg_code}")
#     gdf_points = gpd.GeoDataFrame({'timestamp': all_times}, geometry=all_points, crs=f"EPSG:{epsg_code}")
#
#     # 构造逆变换器（投影 → WGS84）
#     inverse_transformer = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
#
#     # 将曝光点转换回 WGS84 坐标，并添加航高 Z
#     wgs84_points_with_time = []
#     for pt, t in [(pt, t) for seq in exposure_sequences for pt, t in seq]:
#         lon, lat = inverse_transformer.transform(pt.x, pt.y)
#         wgs84_points_with_time.append((lon, lat, altitude, t))
#
#     return {
#         'epsg': epsg_code,
#         'projected_polygon': projected_polygon,
#         'flight_lines': gdf_lines,
#         'exposure_points': gdf_points,
#         'exposure_sequences': exposure_sequences,
#         'point_time_list': [(pt, t) for seq in exposure_sequences for pt, t in seq],
#         'wgs84_xyz_time': wgs84_points_with_time,
#     }
#
#
# if __name__ == "__main__":
#     polygon_coords = [
#         (114.3508317, 30.5356698),
#         (114.3592425, 30.5323666),
#         (114.3566078, 30.5266232),
#         (114.3486309, 30.5293104)
#     ]
#
#     params = {
#         'altitude': 120,    # 飞行高度
#         # 'vfov_deg': 14.34,     # 垂直视场角 °
#         # 'hfov_deg': 21.46,     # 水平视场角 °
#         'vfov_deg': 90.34,  # 垂直视场角 °
#         'hfov_deg': 120.46,  # 水平视场角 °
#         'speed': 8,     # 飞行速度 m/s
#         'overlap_front': 0.8,   # 航向重叠度
#         'overlap_side': 0.6,    # 旁向重叠度
#         'turn_time_buffer': 3.0,  # 转弯的冗余时间 s
#     }
#
#     with open("input_config.txt", "w", encoding="utf-8") as f:
#         f.write("# Polygon Coordinates (WGS84)\n")
#         for lon, lat in polygon_coords:
#             f.write(f"{lon:.8f}, {lat:.8f}\n")
#
#         f.write("\n# Flight Parameters\n")
#         for k, v in params.items():
#             f.write(f"{k} = {v}\n")
#
#     plan = generate_uav_flight_plan(polygon_coords, **params)
#
#     with open("trajectory.txt", "w", encoding="utf-8") as f:
#         f.write("Lon,Lat,Z,Time\n")
#         for lon, lat, z, t in plan['wgs84_xyz_time']:
#             f.write(f"{lon:.8f},{lat:.8f},{z:.2f},{t:.2f}\n")
#
#     # # 可视化航线 + 曝光点
#     # fig, ax = plt.subplots(figsize=(10, 10))
#     # gpd.GeoSeries([plan['projected_polygon']]).plot(ax=ax, facecolor='none', edgecolor='black')
#     # plan['flight_lines'].plot(ax=ax, color='blue', linewidth=1)
#     # plan['exposure_points'].plot(ax=ax, color='red', markersize=5)
#     #
#     # # 添加编号
#     # all_pts = plan['exposure_points'].geometry.tolist()
#     # for idx, pt in enumerate(all_pts):
#     #     ax.text(pt.x, pt.y, str(idx + 1), fontsize=6, color='darkred')
#     #
#     # ax.set_title(f"UAV Flight Plan (EPSG:{plan['epsg']})")
#     # ax.set_aspect('equal')
#     # plt.tight_layout()
#     # plt.show()
#
#     # 可视化绘图
#     fig, ax = plt.subplots(figsize=(10, 10))
#     gpd.GeoSeries([plan['projected_polygon']]).plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1)
#     plan['flight_lines'].plot(ax=ax, color='blue', linewidth=1)
#     plan['exposure_points'].plot(ax=ax, color='red', markersize=8)
#
#     # 添加编号和时间标签
#     for idx, (pt, t) in enumerate(plan['point_time_list']):
#         label = f"{idx + 1}\n{t:.1f}s"
#         ax.text(pt.x, pt.y, label, fontsize=6, ha='center', va='center', color='darkred')
#
#     ax.set_title(f"UAV Flight Plan (EPSG:{plan['epsg']})")
#     ax.set_aspect('equal')
#     plt.tight_layout()
#     plt.show()

