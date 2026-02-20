"""
几何算法工具模块
用于计算箍筋路径、凸包等几何计算
"""

from typing import List, Tuple

Point = Tuple[float, float]


def cross_product(o: Point, a: Point, b: Point) -> float:
    """
    计算向量 OA 和 OB 的叉积
    返回值 > 0 表示逆时针，< 0 表示顺时针，= 0 表示共线
    """
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points: List[Point]) -> List[Point]:
    """
    计算点集的凸包（Andrew's monotone chain 算法）
    用于推导外箍筋的路径
    
    Args:
        points: 点坐标列表 [(x1, y1), (x2, y2), ...]
        
    Returns:
        凸包顶点列表（逆时针顺序）
    """
    if len(points) < 3:
        return points
    
    # 按 x 坐标排序，x 相同则按 y 排序
    points = sorted(set(points))
    
    if len(points) < 3:
        return points
    
    # 构建下凸包
    lower = []
    for p in points:
        while len(lower) >= 2 and cross_product(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    
    # 构建上凸包
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross_product(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    
    # 合并（去除首尾重复点）
    return lower[:-1] + upper[:-1]


def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
    """
    判断点是否在多边形内部（Ray Casting 算法）
    
    Args:
        point: 待检测点 (x, y)
        polygon: 多边形顶点列表
        
    Returns:
        True 如果点在多边形内部
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def distance(p1: Point, p2: Point) -> float:
    """计算两点之间的欧几里得距离"""
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def find_inner_points(all_points: List[Point], hull: List[Point]) -> List[Point]:
    """
    找出不在凸包上的内部点
    
    Args:
        all_points: 所有点
        hull: 凸包顶点
        
    Returns:
        内部点列表
    """
    hull_set = set(hull)
    return [p for p in all_points if p not in hull_set]


def generate_hoop_path(predictions: List[dict]) -> dict:
    """
    根据钢筋检测结果生成箍筋路径
    
    Args:
        predictions: Roboflow 返回的检测结果列表
        
    Returns:
        包含外箍筋和内拉筋路径的字典
    """
    if len(predictions) < 3:
        return {"outer_hoop": [], "inner_ties": []}
    
    # 提取中心点坐标
    points = [(p["x"], p["y"]) for p in predictions]
    
    # 计算凸包作为外箍筋路径
    hull = convex_hull(points)
    
    # 找出内部点
    inner = find_inner_points(points, hull)
    
    # 转换为字典格式
    outer_hoop = [{"x": p[0], "y": p[1]} for p in hull]
    
    # 为内部点生成拉筋连接（简化：连接到最近的外框边界）
    inner_ties = []
    if inner and hull:
        # 计算外框边界
        min_x = min(p[0] for p in hull)
        max_x = max(p[0] for p in hull)
        min_y = min(p[1] for p in hull)
        max_y = max(p[1] for p in hull)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        for p in inner:
            # 判断点偏向哪个方向，生成水平或垂直拉筋
            if abs(p[0] - center_x) > abs(p[1] - center_y):
                # 水平拉筋
                inner_ties.append({
                    "from": {"x": min_x, "y": p[1]},
                    "to": {"x": max_x, "y": p[1]},
                    "type": "horizontal"
                })
            else:
                # 垂直拉筋
                inner_ties.append({
                    "from": {"x": p[0], "y": min_y},
                    "to": {"x": p[0], "y": max_y},
                    "type": "vertical"
                })
    
    return {
        "outer_hoop": outer_hoop,
        "inner_ties": inner_ties
    }
