import sys
import json
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QCheckBox, QComboBox, 
                             QGroupBox, QTextEdit)
from PyQt6.QtCore import QTimer
import pyqtgraph.opengl as gl

# 导入我们解耦出来的另外两个模块
from renderer import SceneRenderer

class ProductionAstroSim(QMainWindow):
    def __init__(self, config_path="astro_data.json"):
        super().__init__()
        self.setWindowTitle("ASTRO100 Orbital Simulation Tool - University Release")
        self.resize(1280, 850)

        # 1. 加载数据
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # 2. 状态变量
        self.current_system = "solar_system"
        self.is_colorblind = False
        self.show_hz = False
        self.is_playing = False

        # 3. 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)

        # 4. 初始化 UI 与 渲染器
        self.init_ui()
        self.renderer = SceneRenderer(self.view_3d)
        
        # 5. 加载初始场景
        self.load_current_scene()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # === 左侧面板：控制与交互区 ===
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

        # Group 2: 视角控制
        cam_group = QGroupBox("2. 视角快速切换 (Camera View Controls)")
        cam_layout = QHBoxLayout()
        btn_cam_3d = QPushButton("3D 视角")
        btn_cam_3d.clicked.connect(lambda: self.set_camera_view(distance=15, elev=30, azim=45))
        btn_cam_top = QPushButton("Top 俯视")
        btn_cam_top.clicked.connect(lambda: self.set_camera_view(distance=15, elev=90, azim=0))
        cam_layout.addWidget(btn_cam_3d)
        cam_layout.addWidget(btn_cam_top)
        cam_group.setLayout(cam_layout)

        # Group 3: 开关
        opt_group = QGroupBox("3. 实验观察辅助开关 (Toggles)")
        opt_layout = QVBoxLayout()
        self.chk_hz = QCheckBox("显示宜居带 (Habitable Zone)")
        self.chk_hz.toggled.connect(self.on_hz_toggle)
        self.chk_cb = QCheckBox("色盲友好模式 (Colorblind Theme)")
        self.chk_cb.toggled.connect(self.on_colorblind_toggle)
        opt_layout.addWidget(self.chk_hz)
        opt_layout.addWidget(self.chk_cb)
        opt_group.setLayout(opt_layout)

        # Group 4: 播放与清理控制
        play_group = QGroupBox("4. 运行控制 (Simulation)")
        play_layout = QVBoxLayout()
        self.btn_play = QPushButton("▶ 播放轨道动画")
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_clear = QPushButton("🧹 释放内存 / 重置场景")
        self.btn_clear.clicked.connect(self.clear_scene_memory)
        play_layout.addWidget(self.btn_play)
        play_layout.addWidget(self.btn_clear)
        play_group.setLayout(play_layout)

        # Group 5: 信息框
        info_group = QGroupBox("5. 教学说明与天体信息 (Info)")
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

        # === 右侧面板：3D 渲染画布 ===
        self.view_3d = gl.GLViewWidget()
        self.set_camera_view(distance=15, elev=30, azim=45)

        grid = gl.GLGridItem()
        grid.setSize(24, 24, 1)
        grid.setSpacing(1, 1, 1)
        self.view_3d.addItem(grid)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(320)

        main_layout.addWidget(sidebar_widget)
        main_layout.addWidget(self.view_3d)

    # === 场景调度逻辑 ===
    def load_current_scene(self):
        self.renderer.clear()

        if self.current_system == "solar_system":
            self.chk_hz.setEnabled(False)
            self.info_box.setText("【太阳系模式】\n包含八大行星、高倾角冥王星、椭圆轨道哈雷彗星以及双曲线逃逸轨道的 31/ATLAS 彗星。")
            self.build_solar_system()
        elif self.current_system == "kepler_16":
            self.chk_hz.setEnabled(False)
            self.info_box.setText("【Kepler-16 系统】\n著名的双星系统，系外行星 Kepler-16 b 围绕两颗恒星的共同质心旋转。")
            self.build_kepler16_system()
        elif self.current_system == "trappist_1":
            self.chk_hz.setEnabled(True)
            self.info_box.setText("【TRAPPIST-1 系统】\n包含 7 颗行星，勾选‘显示宜居带’可查看位于宜居带内的行星 e, f, g。")
            self.build_trappist1_system()

    def build_solar_system(self):
        self.renderer.render_star(radius=0.4, color=(1, 0.9, 0, 1))
        bodies = self.config["solar_system"]["planets"] + self.config["solar_system"]["small_bodies"]
        for body in bodies:
            self.renderer.render_orbital_body(body, self.is_colorblind)

    def build_kepler16_system(self):
        data = self.config["exoplanets"]["kepler_16"]
        for i, star in enumerate(data["stars"]):
            phase_offset = 0.0 if i == 0 else np.pi
            self.renderer.render_binary_star(star, phase_offset)
        for planet in data["planets"]:
            self.renderer.render_orbital_body(planet, self.is_colorblind)

    def build_trappist1_system(self):
        data = self.config["exoplanets"]["trappist_1"]
        self.renderer.render_star(radius=0.3, color=(1, 0.3, 0.1, 1))
        for planet in data["planets"]:
            self.renderer.render_orbital_body(planet, self.is_colorblind)
        if self.show_hz:
            self.renderer.render_habitable_zone(data["habitable_zone"], self.is_colorblind)

    # === 事件回调 ===
    def set_camera_view(self, distance, elev, azim):
        self.view_3d.setCameraPosition(distance=distance, elevation=elev, azimuth=azim)

    def on_system_change(self, index):
        systems = ["solar_system", "kepler_16", "trappist_1"]
        self.current_system = systems[index]
        self.load_current_scene()

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

    def update_animation(self):
        self.renderer.update_animation(dt=0.03)

    def clear_scene_memory(self):
        self.renderer.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProductionAstroSim()
    window.show()
    sys.exit(app.exec())