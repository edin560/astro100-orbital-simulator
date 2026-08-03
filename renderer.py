import numpy as np
import pyqtgraph.opengl as gl
from physics import calculate_kepler_position, calculate_star_position, generate_orbit_line_points

class SceneRenderer:
    def __init__(self, view_3d):
        self.view_3d = view_3d
        self.render_items = []      # 所有静态 3D 对象
        self.animated_meshes = []   # 需要移动的 3D 网格对象
        self.animation_paths = []   # 对应的物理参数状态

    def render_orbital_body(self, body, is_colorblind):
        """渲染轨道线与行星实体"""
        a, e, inc = body["a"], body["e"], np.radians(body["inc"])
        color = body["color_cb"] if (is_colorblind and "color_cb" in body) else body.get("color_std", body.get("color"))
        is_bound = body.get("is_bound", True)

        # 1. 绘制轨道线（调用 physics 算坐标）
        pts = generate_orbit_line_points(a, e, inc, is_bound)
        orbit_line = gl.GLLinePlotItem(pos=pts, color=color, width=2, antialias=True)
        self.view_3d.addItem(orbit_line)
        self.render_items.append(orbit_line)

        # 2. 绘制 3D 行星实体
        p_md = gl.MeshData.sphere(rows=10, cols=10, radius=0.07)
        p_mesh = gl.GLMeshItem(meshdata=p_md, smooth=True, color=color)
        
        # 初始位置
        r0 = a * (1 - e**2) / (1 + e) if is_bound else abs(a) * (e**2 - 1) / (1 + e)
        p_mesh.translate(r0, 0, 0)
        
        self.view_3d.addItem(p_mesh)
        self.render_items.append(p_mesh)

        # 3. 记录动画物理属性
        self.animated_meshes.append(p_mesh)
        self.animation_paths.append({
            "a": a, "e": e, "inc": inc, 
            "is_bound": is_bound,
            "speed": body.get("speed", 1.0),
            "current_theta": 0.0
        })

    def render_habitable_zone(self, hz_cfg, is_colorblind):
        """渲染宜居带"""
        color = hz_cfg["color_cb"] if is_colorblind else hz_cfg["color_std"]
        r_in, r_out = hz_cfg["inner"], hz_cfg["outer"]

        theta = np.linspace(0, 2 * np.pi, 80)
        pts = []
        for t in theta:
            pts.append([r_in * np.cos(t), r_in * np.sin(t), 0])
            pts.append([r_out * np.cos(t), r_out * np.sin(t), 0])

        hz_mesh = gl.GLLinePlotItem(pos=np.array(pts), color=color, width=4)
        self.view_3d.addItem(hz_mesh)
        self.render_items.append(hz_mesh)

    def render_star(self, radius, color):
        """渲染静态中心恒星"""
        star_md = gl.MeshData.sphere(rows=12, cols=24, radius=radius)
        star_mesh = gl.GLMeshItem(meshdata=star_md, smooth=True, color=color, shader='balloon')
        self.view_3d.addItem(star_mesh)
        self.render_items.append(star_mesh)
        return star_mesh

    def render_binary_star(self, star, phase_offset):
        """渲染双星中的单颗恒星"""
        s_md = gl.MeshData.sphere(rows=10, cols=20, radius=star["radius"])
        s_mesh = gl.GLMeshItem(meshdata=s_md, smooth=True, color=star["color"], shader='balloon')
        self.view_3d.addItem(s_mesh)
        self.render_items.append(s_mesh)

        self.animated_meshes.append(s_mesh)
        self.animation_paths.append({
            "is_star": True,
            "orbit_r": star["orbit_r"],
            "speed": 1.5,
            "current_theta": phase_offset
        })

    def update_animation(self, dt=0.03):
        """驱动所有物体移动一帧"""
        for i, mesh in enumerate(self.animated_meshes):
            p = self.animation_paths[i]
            p["current_theta"] += p["speed"] * dt
            theta = p["current_theta"]

            if p.get("is_star"):
                x, y, z = calculate_star_position(p["orbit_r"], theta)
            else:
                x, y, z = calculate_kepler_position(
                    p["a"], p["e"], p["inc"], theta, p["is_bound"]
                )

            mesh.resetTransform()
            mesh.translate(x, y, z)

    def clear(self):
        """完全清理内存和画布"""
        for item in self.render_items:
            if item in self.view_3d.items:
                self.view_3d.removeItem(item)
        self.render_items.clear()
        self.animated_meshes.clear()
        self.animation_paths.clear()