import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector4D, QVector3D
from physics import calculate_kepler_position, calculate_star_position, generate_orbit_line_points

class SceneRenderer:
    def __init__(self, view_3d):
        self.view_3d = view_3d
        self.render_items = []
        self.orbit_lines = []   
        self.animated_meshes = []
        self.animation_paths = []
        self.labels = []
        self.grid_item = None

        self._original_paintGL = self.view_3d.paintGL
        self.view_3d.paintGL = self._on_view_paint

    def _on_view_paint(self, *args, **kwargs):
        # 1. 跑原本的 3D 渲染
        self._original_paintGL(*args, **kwargs)
        # 2. 3D 视图变动后，立刻更新 2D 标签屏幕位置
        self.refresh_label_positions()

    def setup_grid(self):
        """初始化空间参考网格"""
        self.grid_item = gl.GLGridItem()
        self.grid_item.setSize(24, 24, 1)
        self.grid_item.setSpacing(1, 1, 1)
        self.view_3d.addItem(self.grid_item)

    def toggle_grid(self, visible):
        """显示 / 隐藏网格"""
        if self.grid_item:
            self.grid_item.setVisible(visible)

    def toggle_orbits(self, visible):
        """显示 / 隐藏所有轨道线条"""
        for line in self.orbit_lines:
            line.setVisible(visible)

    def _apply_transparency(self, color_arr, alpha=0.35):
        """将 RGB/RGBA 颜色数组转化为半透明 RGBA"""
        c = list(color_arr)
        if len(c) == 3:
            c.append(alpha)
        else:
            c[3] = alpha
        return c

    def get_body_position(self, name):
        """根据名称获取天体当前的 3D 物理坐标 [x, y, z]"""
        for path in self.animation_paths:
            if path.get("name") == name:
                pos = path.get("pos_3d", [0.0, 0.0, 0.0])
                return QVector3D(float(pos[0]), float(pos[1]), float(pos[2]))
        return None

    def get_body_telemetry(self, name):
        """实时计算并返回指定天体的物理参数数据"""
        for p in self.animation_paths:
            if p.get("name") == name:
                if p.get("is_static_star"):
                    return {
                        "name": name,
                        "pos": [0.0, 0.0, 0.0],
                        "r": 0.0,
                        "v": 0.0,
                        "a": 0.0,
                        "e": 0.0,
                        "period": "中央恒星 (固定)"
                    }

                pos = p.get("pos_3d", [0.0, 0.0, 0.0])
                # 使用 np.linalg.norm 或 纯 Python 模长计算
                r = float((pos[0]**2 + pos[1]**2 + pos[2]**2) ** 0.5)
                
                a = p.get("a", 1.0)
                e = p.get("e", 0.0)
                is_bound = p.get("is_bound", True)

                if is_bound and a > 0:
                    period_years = a ** 1.5
                    period_str = f"{period_years:.2f} 年 ({period_years * 365.25:.1f} 天)"
                else:
                    period_str = "∞ (非闭合逃逸轨道)"

                # Vis-Viva 活力公式近似计算线速度
                if is_bound:
                    v_rel = np.sqrt(max(0.001, (2.0 / max(r, 0.01)) - (1.0 / a)))
                else:
                    v_rel = np.sqrt(max(0.001, (2.0 / max(r, 0.01)) + (1.0 / abs(a))))
                
                v_kms = v_rel * 29.78  # 基于地球公转 29.78 km/s 进行基准转换

                return {
                    "name": name,
                    "pos": pos,
                    "r": r,
                    "v": v_kms,
                    "a": a,
                    "e": e,
                    "period": period_str
                }
        return None

    def render_orbital_body(self, body, is_colorblind, show_orbits=True):
        a, e, inc = body["a"], body["e"], np.radians(body["inc"])
        base_color = body["color_cb"] if (is_colorblind and "color_cb" in body) else body.get("color_std", body.get("color"))
        is_bound = body.get("is_bound", True)
        name = body.get("name", "Unknown")

        # 1. 半透明轨道线
        orbit_color = self._apply_transparency(base_color, alpha=0.35)
        pts = generate_orbit_line_points(a, e, inc, is_bound)
        
        orbit_line = gl.GLLinePlotItem(
            pos=pts, 
            color=orbit_color, 
            width=1.5, 
            antialias=True, 
            glOptions='translucent'
        )
        orbit_line.setVisible(show_orbits)
        self.view_3d.addItem(orbit_line)
        self.render_items.append(orbit_line)
        self.orbit_lines.append(orbit_line)

        # 2. 实体行星
        planet_color = list(base_color)
        if len(planet_color) == 3:
            planet_color.append(1.0)
        else:
            planet_color[3] = 1.0

        p_md = gl.MeshData.sphere(rows=10, cols=10, radius=0.08)
        p_mesh = gl.GLMeshItem(meshdata=p_md, smooth=True, color=planet_color)
        r0 = a * (1 - e**2) / (1 + e) if is_bound else abs(a) * (e**2 - 1) / (1 + e)
        p_mesh.translate(r0, 0, 0)
        self.view_3d.addItem(p_mesh)
        self.render_items.append(p_mesh)

        # 3. UI 标签
        lbl = QLabel(name, self.view_3d)
        lbl.setStyleSheet("color: white; background-color: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.25); border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.show()
        self.labels.append(lbl)

        self.animated_meshes.append(p_mesh)
        self.animation_paths.append({
            "name": name,
            "a": a, "e": e, "inc": inc, 
            "is_bound": is_bound,
            "speed": body.get("speed", 1.0),
            "current_theta": 0.0,
            "pos_3d": [r0, 0.0, 0.0]
        })

    def render_star(self, radius, color, name="Central Star"):
        star_md = gl.MeshData.sphere(rows=12, cols=24, radius=radius)
        star_mesh = gl.GLMeshItem(meshdata=star_md, smooth=True, color=color, shader='balloon')
        self.view_3d.addItem(star_mesh)
        self.render_items.append(star_mesh)

        lbl = QLabel(name, self.view_3d)
        lbl.setStyleSheet("color: #FACC15; background-color: rgba(15, 23, 42, 0.9); border: 1px solid #FACC15; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.show()
        self.labels.append(lbl)

        self.animated_meshes.append(star_mesh)
        self.animation_paths.append({
            "name": name,
            "is_static_star": True,
            "speed": 0.0,
            "current_theta": 0.0,
            "pos_3d": [0.0, 0.0, 0.0]
        })
        return star_mesh

    def render_binary_star(self, star, phase_offset):
        s_md = gl.MeshData.sphere(rows=10, cols=20, radius=star["radius"])
        s_mesh = gl.GLMeshItem(meshdata=s_md, smooth=True, color=star["color"], shader='balloon')
        self.view_3d.addItem(s_mesh)
        self.render_items.append(s_mesh)

        lbl = QLabel(star.get("name", "Star"), self.view_3d)
        lbl.setStyleSheet("color: #F87171; background-color: rgba(15, 23, 42, 0.9); border: 1px solid #F87171; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.show()
        self.labels.append(lbl)

        x, y, z = calculate_star_position(star["orbit_r"], phase_offset)
        s_mesh.translate(x, y, z)

        self.animated_meshes.append(s_mesh)
        self.animation_paths.append({
            "name": star.get("name", "Star"),
            "is_star": True,
            "orbit_r": star["orbit_r"],
            "speed": 1.5,
            "current_theta": phase_offset,
            "pos_3d": [x, y, z]
        })

    def render_habitable_zone(self, hz_cfg, is_colorblind):
        color = self._apply_transparency(
            hz_cfg["color_cb"] if is_colorblind else hz_cfg["color_std"], 
            alpha=0.25
        )
        r_in, r_out = hz_cfg["inner"], hz_cfg["outer"]

        theta = np.linspace(0, 2 * np.pi, 80)
        pts = []
        for t in theta:
            pts.append([r_in * np.cos(t), r_in * np.sin(t), 0])
            pts.append([r_out * np.cos(t), r_out * np.sin(t), 0])

        hz_mesh = gl.GLLinePlotItem(pos=np.array(pts), color=color, width=3, glOptions='translucent')
        self.view_3d.addItem(hz_mesh)
        self.render_items.append(hz_mesh)

    def update_animation(self, dt=0.03):
        for i, mesh in enumerate(self.animated_meshes):
            p = self.animation_paths[i]

            if not p.get("is_static_star"):
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
                p["pos_3d"] = [x, y, z]


    def refresh_label_positions(self):
        if not self.labels:
            return

        try:
            w = self.view_3d.width()
            h = self.view_3d.height()
            if w <= 0 or h <= 0:
                return

            region = (0, 0, w, h)
            viewport = (0, 0, w, h)

            view_m = self.view_3d.viewMatrix()
            proj_m = self.view_3d.projectionMatrix(region, viewport)
            mvp = proj_m * view_m

            for i, p in enumerate(self.animation_paths):
                lbl = self.labels[i]
                pos = p["pos_3d"]

                v_3d = QVector4D(float(pos[0]), float(pos[1]), float(pos[2] + 0.15), 1.0)
                vt = mvp * v_3d

                if vt.w() != 0:
                    ndc_x = vt.x() / vt.w()
                    ndc_y = vt.y() / vt.w()
                    ndc_z = vt.z() / vt.w()

                    if -1.0 <= ndc_z <= 1.0:
                        lbl.show()
                        screen_x = int((ndc_x + 1.0) * 0.5 * w)
                        screen_y = int((1.0 - ndc_y) * 0.5 * h)
                        lbl.move(screen_x - lbl.width() // 2, screen_y - lbl.height() // 2)
                    else:
                        lbl.hide()
        except Exception as e:
            print(f"Label Position Error: {e}")

    def clear(self):
        for item in self.render_items:
            if item in self.view_3d.items:
                self.view_3d.removeItem(item)
        for lbl in self.labels:
            lbl.deleteLater()

        self.render_items.clear()
        self.orbit_lines.clear()
        self.animated_meshes.clear()
        self.animation_paths.clear()
        self.labels.clear()