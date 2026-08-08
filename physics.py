import numpy as np

def calculate_kepler_position(a, e, inc_rad, theta, is_bound=True):
    """根据真近点角 theta 计算单点 3D 笛卡尔坐标 (x, y, z)"""
    if is_bound or e < 1.0:
        # 1. 闭合椭圆轨道 (例如八大行星、哈雷彗星)
        theta_clamped = theta % (2 * np.pi)
        r = a * (1 - e**2) / (1 + e * np.cos(theta_clamped))
        curr_theta = theta_clamped
    else:
        # 2. 逃逸双曲线轨道 (例如 31/ATLAS 彗星)
        # 算出于渐近线边界：theta_limit = arccos(-1/e)
        max_theta = np.arccos(-1.0 / e) - 0.05  # 留出 0.05 rad 安全边际，防止分母趋近 0
        
        # 将无界递增的 theta 映射到正弦平滑区间 [-max_theta, max_theta]
        # 视觉效果：从深空飞入 -> 近日点 -> 极速转向 -> 飞向深空
        curr_theta = np.sin(theta) * max_theta
        r = abs(a) * (e**2 - 1) / (1 + e * np.cos(curr_theta))

    x = r * np.cos(curr_theta)
    y = r * np.sin(curr_theta) * np.cos(inc_rad)
    z = r * np.sin(curr_theta) * np.sin(inc_rad)
    return x, y, z

def calculate_star_position(orbit_r, theta):
    """计算双星系统恒星的简单圆轨道坐标"""
    x = orbit_r * np.cos(theta)
    y = orbit_r * np.sin(theta)
    z = 0.0
    return x, y, z

def generate_orbit_line_points(a, e, inc_rad, is_bound=True, num_points=250):
    """生成轨道静态绘制线的点阵数据 (N, 3)"""
    if is_bound or e < 1.0:
        theta_line = np.linspace(0, 2 * np.pi, num_points)
        r_line = a * (1 - e**2) / (1 + e * np.cos(theta_line))
    else:
        # 双曲线轨道线的采样范围控制在渐近线以内
        max_theta = np.arccos(-1.0 / e) - 0.05
        theta_line = np.linspace(-max_theta, max_theta, num_points)
        r_line = abs(a) * (e**2 - 1) / (1 + e * np.cos(theta_line))

    x_line = r_line * np.cos(theta_line)
    y_line = r_line * np.sin(theta_line) * np.cos(inc_rad)
    z_line = r_line * np.sin(theta_line) * np.sin(inc_rad)

    return np.vstack([x_line, y_line, z_line]).transpose()