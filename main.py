import sys
import json
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QCheckBox, QComboBox, 
                             QLabel, QGroupBox, QTextEdit)
from PyQt6.QtCore import QTimer
import pyqtgraph.opengl as gl

class ProductionAstroSim(QMainWindow):
    # ProductionAstroSim 类继承 QMainWindow 的所有能力
    def __init__(self, config_path="astro_data.json"):
        super().__init__()
        self.setWindowTitle("ASTRO100 Orbital Simulation Tool - University Release")
        self.resize(1280, 850)

        # 1. 加载数据
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f) # 解析成dict and list以供使用

        # 2. 状态变量
        self.current_system = "solar_system" # "solar_system", "kepler_16", "trappist_1"
        self.is_colorblind = False #色盲模式（关）
        self.show_hz = False # 宜居带（关）
        self.is_playing = False # 播放动画 （关）
        self.time_step = 0.0 # 时间累加器，动画每更新一帧，这个值就会按照一定的速度递增，然后代入到开普勒方程里算出每个行星在这一刻的 3D 位置 (x, y, z)

        # 资源清理句柄
        self.render_items = [] # 存放场景里的所有静态 3D 对象（比如轨道线、宜居带半透明环、恒星等）。
        self.animated_meshes = [] # 专门存放需要移动的 3D 网格（比如会公转的行星球体对象）。
        self.animation_paths = [] # 存放这些移动行星对应的开普勒轨道数学轨迹数据

        # 3. 动画定时器
        self.timer = QTimer() # 创建一个 Qt 内部的硬件级定时器对象。
        self.timer.timeout.connect(self.update_animation)
        # 整行逻辑：相当于告诉系统——“一旦定时器计时结束（比如每隔 30 毫秒），立刻自动去触发 self.update_animation() 函数，把所有行星的位置往前推进一帧！

        # 4. 初始化 UI
        self.init_ui()
        self.load_current_scene()

    def init_ui(self):
        main_widget = QWidget() # 没有任何样式的空白面板, 承载后续所有的按钮、控制面板和 3D 画布
        self.setCentralWidget(main_widget) # 刚才创建的 main_widget 填充到正中间的整个空白区域
        main_layout = QHBoxLayout(main_widget) # 水平布局直接绑定到 main_widget 上

        # === 左侧面板：控制与交互区 ===
        sidebar = QVBoxLayout()

        # Group 1: 模拟模式与场景切换
        sys_group = QGroupBox("1. 实验场景选择 (Expt Mode)")
        sys_layout = QVBoxLayout()
        self.combo_system = QComboBox()
        self.combo_system.addItems([
            "JPL 太阳系与天体 (Solar System + Pluto + Comets)",
            "Kepler-16 双星系统 (Binary Star System)",
            "TRAPPIST-1 宜居带对比 (Exoplanets & Habitable Zone)"
        ])
        self.combo_system.currentIndexChanged.connect(self.on_system_change) # 事件监听
        sys_layout.addWidget(self.combo_system)
        sys_group.setLayout(sys_layout) # 塞入盒子

        # Group 2: 视角控制 (Camera Views)
        cam_group = QGroupBox("2. 视角快速切换 (Camera View Controls)")
        cam_layout = QHBoxLayout()
        btn_cam_3d = QPushButton("3D 视角")
        btn_cam_3d.clicked.connect(lambda: self.set_camera_view(distance=15, elev=30, azim=45)) # 设置lambda以防程序开始时就执行函数
        btn_cam_top = QPushButton("Top 俯视")
        btn_cam_top.clicked.connect(lambda: self.set_camera_view(distance=15, elev=90, azim=0))
        cam_layout.addWidget(btn_cam_3d)
        cam_layout.addWidget(btn_cam_top)
        cam_group.setLayout(cam_layout) # 塞入盒子

        # Group 3: 业务功能与无障碍开关
        opt_group = QGroupBox("3. 实验观察辅助开关 (Toggles)")
        opt_layout = QVBoxLayout()
        self.chk_hz = QCheckBox("显示宜居带 (Habitable Zone)")
        self.chk_hz.toggled.connect(self.on_hz_toggle) # 调用函数
        self.chk_cb = QCheckBox("色盲友好模式 (Colorblind Theme)")
        self.chk_cb.toggled.connect(self.on_colorblind_toggle) #调用对应函数connect
        opt_layout.addWidget(self.chk_hz) # 第一个开关入盒
        opt_layout.addWidget(self.chk_cb) # 第二个开关入盒
        opt_group.setLayout(opt_layout) # 塞入盒子

        # Group 4: 播放控制与内存优化
        play_group = QGroupBox("4. 运行控制 (Simulation)")
        play_layout = QVBoxLayout()
        self.btn_play = QPushButton("▶ 播放轨道动画")
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_clear = QPushButton("🧹 释放内存 / 重置场景")
        self.btn_clear.clicked.connect(self.clear_scene_memory)
        play_layout.addWidget(self.btn_play)
        play_layout.addWidget(self.btn_clear)
        play_group.setLayout(play_layout)

        # Group 5: 教学知识点说明信息框
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
        self.view_3d = gl.GLViewWidget() # 造3D屏幕，提供3D渲染窗口
        self.set_camera_view(distance=15, elev=30, azim=45)
        # 相机离中心太阳的距离为 15 个单位（拉远/拉近）
        # 相机的仰角为 30 度（稍微俯视视角）
        # 相机的方位角/旋转角为 45 度（斜着看，让 3D 空间感最强）

        # 添加底面网格
        grid = gl.GLGridItem() # 造网格
        grid.setSize(24, 24, 1) # 设置整体大小
        grid.setSpacing(1, 1, 1) # 设置间隙大小，网格上每隔 1 个单位画一条格子线
        self.view_3d.addItem(grid) # 放在画布中

        sidebar_widget = QWidget() # 造底板（地基）
        sidebar_widget.setLayout(sidebar) # 给五个功能塞到地基里
        sidebar_widget.setMaximumWidth(320) # 设置最大宽度，这样无论如何调整窗口，功能栏不会扭曲

        main_layout.addWidget(sidebar_widget) #入箱子
        main_layout.addWidget(self.view_3d) #入箱

    # === 渲染核心逻辑 ===
    def load_current_scene(self):
        """根据当前选中的场景加载数据并渲染"""
        self.clear_scene_memory() # 先清理一遍内存

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
        """绘制太阳系：八大行星 + 冥王星 + 彗星"""
        # 1. 太阳
        sun_md = gl.MeshData.sphere(rows=12, cols=24, radius=0.4) # 捏一个球体骨架，rows=12, cols=24，指的是球体的网格密度，横向 12 圈，纵向 24 圈
        sun_mesh = gl.GLMeshItem(meshdata=sun_md, smooth=True, color=(1, 0.9, 0, 1), shader='balloon') # 骨架渲染
        self.view_3d.addItem(sun_mesh) # 放入画布
        self.render_items.append(sun_mesh) # 放入待释放缓存列表

        # 2. 天体列表
        bodies = self.config["solar_system"]["planets"] + self.config["solar_system"]["small_bodies"]
        for body in bodies:
            self.render_orbital_body(body) # 交给函数计算轨迹弧线并防止行星

    def build_kepler16_system(self):
        """绘制 Kepler-16 双星系统"""
        data = self.config["exoplanets"]["kepler_16"]
        
        # 渲染双星
        for star in data["stars"]:
            s_md = gl.MeshData.sphere(rows=10, cols=20, radius=star["radius"])
            s_mesh = gl.GLMeshItem(meshdata=s_md, smooth=True, color=star["color"], shader='balloon')
            self.view_3d.addItem(s_mesh)
            self.render_items.append(s_mesh)
            
            # 双星小范围旋转路径
            theta = np.linspace(0, 2 * np.pi, 100) # 切分圆周角：把一个圆周均分成 100 份
            r = star["orbit_r"]
            x, y, z = r * np.cos(theta), r * np.sin(theta), np.zeros_like(theta)
            self.animated_meshes.append(s_mesh)
            self.animation_paths.append({"x": x, "y": y, "z": z, "speed": 1.5})

        # 渲染环双星行星
        for planet in data["planets"]:
            self.render_orbital_body(planet)

    def build_trappist1_system(self):
        """绘制 TRAPPIST-1 系统及宜居带"""
        data = self.config["exoplanets"]["trappist_1"]

        # 矮恒星
        star_md = gl.MeshData.sphere(rows=12, cols=24, radius=0.3)
        star_mesh = gl.GLMeshItem(meshdata=star_md, smooth=True, color=(1, 0.3, 0.1, 1), shader='balloon')
        self.view_3d.addItem(star_mesh)
        self.render_items.append(star_mesh)

        # 7 颗行星
        for planet in data["planets"]:
            self.render_orbital_body(planet)

        # 宜居带渲染
        if self.show_hz:
            self.render_habitable_zone_mesh(data["habitable_zone"])

    def render_orbital_body(self, body):
        """通用的 3D 轨迹与天体渲染算法"""
        a, e, inc = body["a"], body["e"], np.radians(body["inc"])
        color = body["color_cb"] if (self.is_colorblind and "color_cb" in body) else body.get("color_std", body.get("color"))
        is_bound = body.get("is_bound", True) #是否受轨道约束

        if is_bound: # 椭圆/圆轨道
            theta = np.linspace(0, 2 * np.pi, 150)
            r = a * (1 - e**2) / (1 + e * np.cos(theta))
            x = r * np.cos(theta)
            y = r * np.sin(theta) * np.cos(inc)
            z = r * np.sin(theta) * np.sin(inc)
        else: # 31/ATLAS 双曲线逃逸轨道
            theta = np.linspace(-1.1, 1.1, 150)
            r = abs(a) * (e**2 - 1) / (1 + e * np.cos(theta))
            x = r * np.cos(theta)
            y = r * np.sin(theta) * np.cos(inc)
            z = r * np.sin(theta) * np.sin(inc)

        pts = np.vstack([x, y, z]).transpose() # 将三个独立的 x, y, z 1维数组拼合成一个 N x 3 的 3D 空间坐标点阵列
        orbit_line = gl.GLLinePlotItem(pos=pts, color=color, width=2, antialias=True) # 讲点用宽度为2的彩色实线连接起来
        self.view_3d.addItem(orbit_line)
        self.render_items.append(orbit_line)

        # 3D 天体实体
        p_md = gl.MeshData.sphere(rows=10, cols=10, radius=0.07)
        p_mesh = gl.GLMeshItem(meshdata=p_md, smooth=True, color=color)
        p_mesh.translate(x[0], y[0], z[0])
        self.view_3d.addItem(p_mesh)
        self.render_items.append(p_mesh)

        # 加入动画绑定
        self.animated_meshes.append(p_mesh)
        self.animation_paths.append({"x": x, "y": y, "z": z, "speed": body.get("speed", 1.0)})

    def render_habitable_zone_mesh(self, hz_cfg):
        """渲染绿色半透明宜居带色块"""
        color = hz_cfg["color_cb"] if self.is_colorblind else hz_cfg["color_std"]
        r_in, r_out = hz_cfg["inner"], hz_cfg["outer"]

        theta = np.linspace(0, 2 * np.pi, 80)
        pts = []
        for t in theta:
            pts.append([r_in * np.cos(t), r_in * np.sin(t), 0])
            pts.append([r_out * np.cos(t), r_out * np.sin(t), 0])

        hz_mesh = gl.GLLinePlotItem(pos=np.array(pts), color=color, width=4)
        self.view_3d.addItem(hz_mesh)
        self.render_items.append(hz_mesh)

    # === 事件响应与控制 ===
    def set_camera_view(self, distance, elev, azim):
        self.view_3d.setCameraPosition(distance=distance, elevation=elev, azimuth=azim)

    def on_system_change(self, index):
        if index == 0:
            self.current_system = "solar_system"
        elif index == 1:
            self.current_system = "kepler_16"
        elif index == 2:
            self.current_system = "trappist_1"
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
        self.time_step += 0.5
        for i, mesh in enumerate(self.animated_meshes):
            path = self.animation_paths[i]
            idx = int((self.time_step * path["speed"])) % len(path["x"])
            mesh.resetTransform()
            mesh.translate(path["x"][idx], path["y"][idx], path["z"][idx])

    def clear_scene_memory(self):
        """彻底清理 3D 画布与内存中残留的 Mesh 句柄"""
        for item in self.render_items:
            if item in self.view_3d.items:
                self.view_3d.removeItem(item)
        self.render_items.clear()
        self.animated_meshes.clear()
        self.animation_paths.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProductionAstroSim()
    window.show()
    sys.exit(app.exec())