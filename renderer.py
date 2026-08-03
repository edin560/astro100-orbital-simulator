import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector4D
from physics import calculate_kepler_position, calculate_star_position, generate_orbit_line_points

class SceneRenderer:
    def __init__(self, view_3d):
        self.view_3d = view_3d
        self.render_items = []
        self.animated_meshes = []
        self.animation_paths = []
        self.labels = []

    def render_orbital_body(self, body, is_colorblind):
        a, e, inc = body["a"], body["e"], np.radians(body["inc"])
        color = body["color_cb"] if (is_colorblind and "color_cb" in body) else body.get("color_std", body.get("color"))
        is_bound = body.get("is_bound", True)
        name = body.get("name", "Unknown")

        # 1. 轨道线
        pts = generate_orbit_line_points(a, e, inc, is_bound)
        orbit_line = gl.GLLinePlotItem(pos=pts, color=color, width=2, antialias=True)
        self.view_3d.addItem(orbit_line)
        self.render_items.append(orbit_line)

        # 2. 3D 行星实体
        p_md = gl.MeshData.sphere(rows=10, cols=10, radius=0.07)
        p_mesh = gl.GLMeshItem(meshdata=p_md, smooth=True, color=color)
        r0 = a * (1 - e**2) / (1 + e) if is_bound else abs(a) * (e**2 - 1) / (1 + e)
        p_mesh.translate(r0, 0, 0)
        self.view_3d.addItem(p_mesh)
        self.render_items.append(p_mesh)

        # 3. 2D 文本标签浮层
        lbl = QLabel(name, self.view_3d)
        lbl.setStyleSheet("color: white; background-color: rgba(15, 23, 42, 0.75); border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lbl.show()
        self.labels.append(lbl)

        # 4. 存储属性
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
        lbl.setStyleSheet("color: #FACC15; background-color: rgba(15, 23, 42, 0.85); border: 1px solid #FACC15; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
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
        lbl.setStyleSheet("color: #F87171; background-color: rgba(15, 23, 42, 0.85); border: 1px solid #F87171; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
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

        self.refresh_label_positions()

    def refresh_label_positions(self):
        """修复参数传递后的 3D -> 2D 坐标映射逻辑"""
        if not self.labels:
            return

        try:
            w = self.view_3d.width()
            h = self.view_3d.height()
            if w <= 0 or h <= 0:
                return

            region = (0, 0, w, h)
            viewport = (0, 0, w, h)

            # 正确给 projectionMatrix 传入 region 与 viewport
            view_m = self.view_3d.viewMatrix()
            proj_m = self.view_3d.projectionMatrix(region, viewport)
            mvp = proj_m * view_m

            for i, p in enumerate(self.animation_paths):
                lbl = self.labels[i]
                pos = p["pos_3d"]

                # 构造齐次坐标（Z轴抬高 0.15 避免文字覆盖球体中心）
                v_3d = QVector4D(float(pos[0]), float(pos[1]), float(pos[2] + 0.15), 1.0)
                vt = mvp * v_3d

                if vt.w() != 0:
                    ndc_x = vt.x() / vt.w()
                    ndc_y = vt.y() / vt.w()
                    ndc_z = vt.z() / vt.w()

                    # 判断是否在视野的前裁剪面和后裁剪面之间 (-1 <= Z <= 1)
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
        self.animated_meshes.clear()
        self.animation_paths.clear()
        self.labels.clear()