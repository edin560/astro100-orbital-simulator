import sys
import json
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QCheckBox, QComboBox, 
                             QGroupBox, QTextEdit, QSlider, QLabel)
from PyQt6.QtCore import QTimer, Qt, QDate
from PyQt6.QtGui import QVector3D
import pyqtgraph.opengl as gl

from renderer import SceneRenderer

class ProductionAstroSim(QMainWindow):
    def __init__(self, config_path="astro_data.json"):
        super().__init__()
        self.setWindowTitle("ASTRO100 Orbital Simulation Tool - University Release")
        self.resize(1280, 850)

        # 时间系统变量
        self.sim_days = 0.0                     
        self.speed_factor = 1.0                 
        self.base_date = QDate(2026, 1, 1)      

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.current_system = "solar_system"
        self.is_colorblind = False
        self.show_hz = False
        self.show_orbits = True   
        self.is_playing = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)

        self.init_ui()
        self.renderer = SceneRenderer(self.view_3d)
        self.renderer.setup_grid()
        
        self.load_current_scene()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        sidebar = QVBoxLayout()

        # Group 1: 实验场景选择
        sys_group = QGroupBox("1. 实验场景选择 (Expt Mode)")
        sys_layout = QVBoxLayout()
        self.combo_system = QComboBox()
        self.combo_system.addItems([
            "JPL 太阳系与天体 (Solar System + Pluto + Comets)",
            "Kepler-16 双星系统 (Binary Star System)",
            "TRAPPIST-1 宜居带对比 (Exoplanets & Habitable Zone)"
        ])
        self.combo_system.currentIndexChanged.connect(self.on_system_change)
        sys_layout.addWidget(self.combo_system)
        sys_group.setLayout(sys_layout)

        # Group 2: 视角与追踪控制
        cam_group = QGroupBox("2. 视角与追踪 (Camera & Tracking)")
        cam_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn_cam_3d = QPushButton("3D 全景")
        btn_cam_3d.clicked.connect(lambda: self.reset_camera_target(distance=15, elev=30, azim=45))
        btn_cam_top = QPushButton("Top 俯视")
        btn_cam_top.clicked.connect(lambda: self.reset_camera_target(distance=15, elev=90, azim=0))
        btn_layout.addWidget(btn_cam_3d)
        btn_layout.addWidget(btn_cam_top)

        track_layout = QHBoxLayout()
        track_label = QLabel("聚焦目标:")
        self.combo_target = QComboBox()
        self.combo_target.addItem("🌐 全局质心 (System Center)", userData=None)
        self.combo_target.currentIndexChanged.connect(self.on_target_changed)
        track_layout.addWidget(track_label)
        track_layout.addWidget(self.combo_target)

        cam_layout.addLayout(btn_layout)
        cam_layout.addLayout(track_layout)
        cam_group.setLayout(cam_layout)

        # Group 3: 辅助开关
        opt_group = QGroupBox("3. 实验观察辅助开关 (Toggles)")
        opt_layout = QVBoxLayout()
        
        self.chk_grid = QCheckBox("显示空间参考网格 (Grid)")
        self.chk_grid.setChecked(True)
        self.chk_grid.toggled.connect(self.on_grid_toggle)

        self.chk_orbits = QCheckBox("显示天体轨道 (Orbit Lines)")
        self.chk_orbits.setChecked(True)
        self.chk_orbits.toggled.connect(self.on_orbits_toggle)

        self.chk_hz = QCheckBox("显示宜居带 (Habitable Zone)")
        self.chk_hz.toggled.connect(self.on_hz_toggle)

        self.chk_cb = QCheckBox("色盲友好模式 (Colorblind Theme)")
        self.chk_cb.toggled.connect(self.on_colorblind_toggle)

        opt_layout.addWidget(self.chk_grid)
        opt_layout.addWidget(self.chk_orbits)
        opt_layout.addWidget(self.chk_hz)
        opt_layout.addWidget(self.chk_cb)
        opt_group.setLayout(opt_layout)

        # Group 4: 运行与时间控制
        play_group = QGroupBox("4. 运行与时间控制 (Simulation)")
        play_layout = QVBoxLayout()

        btn_ctrl_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ 播放动画")
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_reset_time = QPushButton("⏱ 重置时间")
        self.btn_reset_time.clicked.connect(self.reset_sim_time)

        self.btn_clear = QPushButton("🧹 释放内存")
        self.btn_clear.clicked.connect(self.clear_scene_memory)

        btn_ctrl_layout.addWidget(self.btn_play)
        btn_ctrl_layout.addWidget(self.btn_reset_time)
        btn_ctrl_layout.addWidget(self.btn_clear)

        speed_label_layout = QHBoxLayout()
        speed_title = QLabel("模拟速率:")
        self.lbl_speed_val = QLabel("1.0x")
        self.lbl_speed_val.setStyleSheet("font-weight: bold; color: #38BDF8;")
        speed_label_layout.addWidget(speed_title)
        speed_label_layout.addWidget(self.lbl_speed_val)
        speed_label_layout.addStretch()

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(1, 100)      
        self.slider_speed.setValue(10)          
        self.slider_speed.valueChanged.connect(self.on_speed_change)

        self.lbl_clock = QLabel("🗓 2026-01-01\n⏱ 经过: 0 天 (0.00 年)")
        self.lbl_clock.setStyleSheet("""
            background-color: #0F172A; 
            color: #4ADE80; 
            border: 1px solid #334155; 
            border-radius: 4px; 
            padding: 6px; 
            font-family: monospace; 
            font-size: 12px; 
            font-weight: bold;
        """)

        play_layout.addLayout(btn_ctrl_layout)
        play_layout.addLayout(speed_label_layout)
        play_layout.addWidget(self.slider_speed)
        play_layout.addWidget(self.lbl_clock)
        play_group.setLayout(play_layout)

        # Group 5: 物理遥测与信息框
        info_group = QGroupBox("5. 实时物理遥测与说明 (Live Telemetry)")
        info_layout = QVBoxLayout()
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        info_layout.addWidget(self.info_box)
        info_group.setLayout(info_layout)

        sidebar.addWidget(sys_group)
        sidebar.addWidget(cam_group)
        sidebar.addWidget(opt_group)
        sidebar.addWidget(play_group)
        sidebar.addWidget(info_group)

        # === 右侧 3D 渲染画布 ===
        self.view_3d = gl.GLViewWidget()
        self.set_camera_view(distance=15, elev=30, azim=45)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(320)

        main_layout.addWidget(sidebar_widget)
        main_layout.addWidget(self.view_3d)

    def populate_target_combo(self):
        """填充聚焦目标下拉框"""
        self.combo_target.blockSignals(True)
        self.combo_target.clear()
        self.combo_target.addItem("🌐 全局质心 (System Center)", userData=None)
        
        for path in self.renderer.animation_paths:
            name = path.get("name", "Unknown")
            self.combo_target.addItem(f"🪐 {name}", userData=name)
            
        self.combo_target.blockSignals(False)

    def update_telemetry_panel(self):
        """动态渲染选中天体的物理参数面板"""
        target_name = self.combo_target.currentData()
        
        if not target_name:
            if self.current_system == "solar_system":
                self.info_box.setText("【太阳系模式】\n包含八大行星、高倾角冥王星、椭圆轨道哈雷彗星以及双曲线逃逸轨道的 31/ATLAS 彗星。\n\n💡 提示：在上方下拉菜单选择天体，即可开启追踪并查看实时物理参数。")
            elif self.current_system == "kepler_16":
                self.info_box.setText("【Kepler-16 系统】\n著名的双星系统，系外行星 Kepler-16 b 围绕两颗恒星的共同质心旋转。")
            elif self.current_system == "trappist_1":
                self.info_box.setText("【TRAPPIST-1 系统】\n包含 7 颗行星，勾选‘显示宜居带’可查看位于宜居带内的行星 e, f, g。")
            return

        data = self.renderer.get_body_telemetry(target_name)
        if data:
            html_info = f"""
            <div style='font-family: sans-serif; font-size: 12px;'>
                <h3 style='color: #38BDF8; margin: 0px 0px 6px 0px;'>🪐 {data['name']}</h3>
                <hr style='border: 1px solid #334155; margin-bottom: 8px;'>
                <p style='margin: 3px 0;'><b>📍 瞬时位置 (3D):</b><br>
                <code style='color: #FACC15;'>X:{data['pos'][0]:.2f} | Y:{data['pos'][1]:.2f} | Z:{data['pos'][2]:.2f}</code></p>
                
                <p style='margin: 5px 0;'><b>📏 距离主星 (r):</b> <span style='color: #4ADE80; font-weight: bold;'>{data['r']:.3f} AU</span></p>
                <p style='margin: 5px 0;'><b>⚡ 瞬时公转速度 (v):</b> <span style='color: #F87171; font-weight: bold;'>{data['v']:.2f} km/s</span></p>
                <p style='margin: 5px 0;'><b>⏱ 轨道周期 (T):</b> <span style='color: #E0E7FF;'>{data['period']}</span></p>
                
                <hr style='border: 1px solid #334155; margin: 8px 0;'>
                <p style='margin: 3px 0;'><b>📐 半长轴 (a):</b> {data['a']:.2f} AU</p>
                <p style='margin: 3px 0;'><b>🌀 偏心率 (e):</b> {data['e']:.3f} ({'椭圆轨道' if data['e'] < 1 else '双曲线逃逸'})</p>
            </div>
            """
            self.info_box.setHtml(html_info)

    def load_current_scene(self):
        self.renderer.clear()

        if self.current_system == "solar_system":
            self.chk_hz.setEnabled(False)
            self.build_solar_system()
        elif self.current_system == "kepler_16":
            self.chk_hz.setEnabled(False)
            self.build_kepler16_system()
        elif self.current_system == "trappist_1":
            self.chk_hz.setEnabled(True)
            self.build_trappist1_system()

        self.renderer.refresh_label_positions()
        self.populate_target_combo()
        self.update_telemetry_panel()

    def build_solar_system(self):
        star_cfg = self.config["solar_system"].get("star", {"name": "Sun (太阳)", "radius": 0.4, "color": [1, 0.9, 0, 1]})
        self.renderer.render_star(
            radius=star_cfg.get("radius", 0.4), 
            color=star_cfg.get("color", [1, 0.9, 0, 1]), 
            name=star_cfg.get("name", "Sun (太阳)")
        )

        bodies = self.config["solar_system"]["planets"] + self.config["solar_system"]["small_bodies"]
        for body in bodies:
            self.renderer.render_orbital_body(body, self.is_colorblind, self.show_orbits)

    def build_kepler16_system(self):
        data = self.config["exoplanets"]["kepler_16"]
        for i, star in enumerate(data["stars"]):
            phase_offset = 0.0 if i == 0 else np.pi
            self.renderer.render_binary_star(star, phase_offset)
        for planet in data["planets"]:
            self.renderer.render_orbital_body(planet, self.is_colorblind, self.show_orbits)

    def build_trappist1_system(self):
        data = self.config["exoplanets"]["trappist_1"]
        star_cfg = data.get("star", {"name": "TRAPPIST-1 (红矮星)", "radius": 0.3, "color": [1, 0.3, 0.1, 1]})
        self.renderer.render_star(
            radius=star_cfg.get("radius", 0.3), 
            color=star_cfg.get("color", [1, 0.3, 0.1, 1]), 
            name=star_cfg.get("name", "TRAPPIST-1 (红矮星)")
        )

        for planet in data["planets"]:
            self.renderer.render_orbital_body(planet, self.is_colorblind, self.show_orbits)
            
        if self.show_hz:
            self.renderer.render_habitable_zone(data["habitable_zone"], self.is_colorblind)

    # === 回调函数与逻辑 ===
    def set_camera_view(self, distance, elev, azim):
        self.view_3d.setCameraPosition(distance=distance, elevation=elev, azimuth=azim)

    def reset_camera_target(self, distance, elev, azim):
        self.combo_target.setCurrentIndex(0)
        self.view_3d.opts['center'] = QVector3D(0, 0, 0)
        self.set_camera_view(distance=distance, elev=elev, azim=azim)

    def on_target_changed(self, index):
        target_name = self.combo_target.currentData()
        if target_name is None:
            self.view_3d.opts['center'] = QVector3D(0, 0, 0)
            self.set_camera_view(distance=15, elev=30, azim=45)
        else:
            pos = self.renderer.get_body_position(target_name)
            if pos:
                self.view_3d.setCameraPosition(pos=pos, distance=4.0)
        
        self.update_telemetry_panel()

    def on_system_change(self, index):
        systems = ["solar_system", "kepler_16", "trappist_1"]
        self.current_system = systems[index]
        self.load_current_scene()

    def on_grid_toggle(self, checked):
        self.renderer.toggle_grid(checked)

    def on_orbits_toggle(self, checked):
        self.show_orbits = checked
        self.renderer.toggle_orbits(checked)

    def on_hz_toggle(self, checked):
        self.show_hz = checked
        self.load_current_scene()

    def on_colorblind_toggle(self, checked):
        self.is_colorblind = checked
        self.load_current_scene()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.setText("⏸ 暂停动画")
            self.timer.start(30)
        else:
            self.btn_play.setText("▶ 播放动画")
            self.timer.stop()

    def on_speed_change(self, value):
        self.speed_factor = value / 10.0
        self.lbl_speed_val.setText(f"{self.speed_factor:.1f}x")

    def reset_sim_time(self):
        self.sim_days = 0.0
        self.update_time_display()
        self.load_current_scene()

    def update_time_display(self):
        current_date = self.base_date.addDays(int(self.sim_days))
        date_str = current_date.toString("yyyy-MM-dd")
        years = self.sim_days / 365.25
        self.lbl_clock.setText(f"🗓 {date_str}\n⏱ 经过: {int(self.sim_days)} 天 ({years:.2f} 年)")

    def update_animation(self):
        base_dt = 0.03
        effective_dt = base_dt * self.speed_factor

        self.renderer.update_animation(dt=effective_dt)

        # 1. 实时视角追踪
        target_name = self.combo_target.currentData()
        if target_name:
            pos = self.renderer.get_body_position(target_name)
            if pos:
                opts = self.view_3d.opts
                self.view_3d.setCameraPosition(
                    pos=pos, 
                    distance=opts['distance'], 
                    elevation=opts['elevation'], 
                    azimuth=opts['azimuth']
                )

        # 2. 实时刷新物理参数遥测看板
        self.update_telemetry_panel()

        # 3. 时间推进
        days_per_step = 0.5 * self.speed_factor
        self.sim_days += days_per_step
        self.update_time_display()

    def clear_scene_memory(self):
        self.renderer.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProductionAstroSim()
    window.show()
    sys.exit(app.exec())