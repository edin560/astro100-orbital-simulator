import numpy as np

def calculate_kepler_position(a, e, inc_rad, theta, is_bound=True):
    """根据真近点角 theta 计算单点 3D 笛卡尔坐标 (x, y, z)"""
    if is_bound:
        theta = theta % (2 * np.pi)
        r = a * (1 - e**2) / (1 + e * np.cos(theta))
    else:
        theta = np.sin(theta) * 1.1 
        r = abs(a) * (e**2 - 1) / (1 + e * np.cos(theta))

    x = r * np.cos(theta)
    y = r * np.sin(theta) * np.cos(inc_rad)
    z = r * np.sin(theta) * np.sin(inc_rad)
    return x, y, z

def calculate_star_position(orbit_r, theta):
    """计算双星系统恒星的简单圆轨道坐标"""
    x = orbit_r * np.cos(theta)
    y = orbit_r * np.sin(theta)
    z = 0.0
    return x, y, z

def generate_orbit_line_points(a, e, inc_rad, is_bound=True, num_points=200):
    """生成轨道静态绘制线的点阵数据 (N, 3)"""
    if is_bound:
        theta_line = np.linspace(0, 2 * np.pi, num_points)
        r_line = a * (1 - e**2) / (1 + e * np.cos(theta_line))
    else:
        theta_line = np.linspace(-1.1, 1.1, num_points)
        r_line = abs(a) * (e**2 - 1) / (1 + e * np.cos(theta_line))

    x_line = r_line * np.cos(theta_line)
    y_line = r_line * np.sin(theta_line) * np.cos(inc_rad)
    z_line = r_line * np.sin(theta_line) * np.sin(inc_rad)

    return np.vstack([x_line, y_line, z_line]).transpose()