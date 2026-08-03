# astro100-orbital-simulator
Local-first 3D Orbital Simulation Tool for ASTRO100 Lab (PyQt6 + pyqtgraph)

## 关于各类库
PyQt6是专门又来搭建软件界面的，而.QtWidgets主要负责窗口组件（Widgets）和排版工具（Layouts），PyQt6.QtCore（核心逻辑与定时器）

QApplication整个桌面应用的主心骨/事件循环管理器。每一个 PyQt 程序必须有且仅有一个 QApplication 实例

QMainWindow主窗口基类，提供了标准的窗口结构（支持标题栏、菜单栏、状态栏等）

QWidget所有界面元素的基础“画布/容器”

QVBoxLayout把组件从上到下垂直排列

QPushButton：按钮（如“▶ 播放动画”）

QCheckBox：复选框（如“显示宜居带”、“色盲模式”）

QComboBox：下拉选择框（如“切换太阳系 / TRAPPIST-1”）

QLabel & QTextEdit：文本标签与文本框（用来显示左下角的教学说明）

QGroupBox：带有标题的分组外框（把侧边栏分成 1, 2, 3, 4, 5 个逻辑块）

QTimer一个定时触发器

## 渲染
渲染用了PyOpenGL

gl.GLViewWidget：直接在 PyQt 窗口里开辟一块 3D OpenGL 渲染画布

gl.MeshData.sphere()：生成球体网格（用来画太阳和行星）

gl.GLLinePlotItem()：画 3D 空间里的线条（用来画轨道的椭圆线和宜居带半透明环）



## 依旧存在的问题以及优化点

**英文版**

行星动画不流畅 （已解决）

轨道透明度以及开关按钮

太阳系轨道位置优化

开/关网格按钮

无法得知星体名称，后面应加鼠标放上去就显示名称的功能（或者角度速度等参数）

缺少光面渲染

宜居带显示有bug

重置场景有bug

未采用rebound库（如果更优后面再改）

解耦 （已解决）

添加速度控制以及时间单位

双击锁定行星功能




