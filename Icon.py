import random
import numpy as np
from pyqtgraph.opengl import GLMeshItem, MeshData
from pyqtgraph.Qt import QtGui
import pyqtgraph.opengl as gl
from scipy.spatial.transform import Rotation as R

# 颜色显示器，为每一个图标分配不同的颜色
class ColorGenerator:
    def __init__(self):
        self.used_colors = set()

    def _color_to_tuple(self, color):
        return tuple(round(c, 2) for c in color)

    def get_unique_color(self):
        max_attempts = 1000
        for _ in range(max_attempts):
            color = (
                random.random(),
                random.random(),
                random.random(),
                1.0
            )
            color_tuple = self._color_to_tuple(color)
            if color_tuple not in self.used_colors:
                self.used_colors.add(color_tuple)
                return color
        # 超过尝试次数时返回默认颜色并警告
        print("警告：颜色池用尽，使用默认颜色")
        return (0.5, 0.5, 0.5, 1.0)


def rodrigues_rotation_matrix(axis, angle):
    """
    Rodrigues 公式生成绕给定单位轴 axis 旋转 angle（弧度）的 3x3 旋转矩阵。
    axis: 长度3数组，需已归一化；angle: 弧度
    """
    # 若 angle 接近 0，可直接返回单位矩阵
    if abs(angle) < 1e-8:
        return np.eye(3)
    x, y, z = axis
    c = np.cos(angle)
    s = np.sin(angle)
    C = 1 - c
    # Rodrigues 公式：
    # R = I*c + (1-c) * (axis ⊗ axis) + s * [axis]_x
    # 其中 [axis]_x 是反对称矩阵
    R = np.array([
        [c + x*x*C,    x*y*C - z*s,  x*z*C + y*s],
        [y*x*C + z*s,  c + y*y*C,    y*z*C - x*s],
        [z*x*C - y*s,  z*y*C + x*s,  c + z*z*C]
    ], dtype=float)
    return R

# 三角形图标类，用于三维无人机的可视化
class Triangle3D(GLMeshItem):
    def __init__(self, pos, direction, length=0.8, width=0.2, color=(1, 0, 0, 1), roll=0.0, smooth=False):
        """
        pos: 底边中心在世界坐标 [x, y, z]
        direction: 目标方向向量 [dx, dy, dz]，表示底边中点到尖头的方向
        length: 三角形高度，从底边中心到尖头的距离
        width: 底边宽度
        color: RGBA 颜色元组
        roll: 绕中轴（方向轴）的滚转角度，弧度
        smooth: 是否平滑渲染（平面三角形通常不需要）
        """
        # 存储属性
        self.pos = np.array(pos, dtype=float)
        self.direction = np.array(direction, dtype=float)
        self.length = float(length)
        self.width = float(width)
        self.roll = float(roll)

        # 构造本地三角形网格：底边中心在 (0,0,0)，尖头在 (0, length, 0)
        verts = np.array([
            [0.0, self.length, 0.0],            # 顶点（尖头）
            [-self.width/2.0, 0.0, 0.0],        # 底边左
            [ self.width/2.0, 0.0, 0.0]         # 底边右
        ], dtype=float)
        faces = np.array([[0, 1, 2]], dtype=int)
        meshdata = MeshData(vertexes=verts, faces=faces)
        super().__init__(meshdata=meshdata, smooth=smooth, color=color, shader='shaded', drawEdges=False)

        # 初次应用变换
        self.update_transform()

    def update_transform(self):
        """
        计算旋转矩阵将本地 +Y 对齐到目标 direction，再绕中轴滚转 roll，
        然后将底边中心平移到 pos，构造并应用 4x4 变换矩阵。
        """
        # 1. 归一化目标方向
        dir_vec = np.array(self.direction, dtype=float)
        norm = np.linalg.norm(dir_vec)
        if norm < 1e-8:
            # 方向近零：视为不旋转，本地 +Y 保持
            R_align = np.eye(3)
        else:
            v_local = np.array([0.0, 1.0, 0.0], dtype=float)
            v_target = dir_vec / norm
            # 计算 dot 和 axis
            dot = np.dot(v_local, v_target)
            if dot >= 1.0 - 1e-8:
                # 同向，无旋转
                R_align = np.eye(3)
            elif dot <= -1.0 + 1e-8:
                # 反向，旋转180度，选任意垂直轴
                # 例如选本地 X 轴 [1,0,0]，若 v_local 近似 [±1,0,0] 则改用 [0,0,1]
                arbitrary = np.array([1.0, 0.0, 0.0], dtype=float)
                if abs(np.dot(v_local, arbitrary)) > 0.9:
                    arbitrary = np.array([0.0, 0.0, 1.0], dtype=float)
                axis = np.cross(v_local, arbitrary)
                axis /= np.linalg.norm(axis)
                R_align = rodrigues_rotation_matrix(axis, np.pi)
            else:
                axis = np.cross(v_local, v_target)
                axis_norm = np.linalg.norm(axis)
                axis /= axis_norm
                angle = np.arccos(dot)
                R_align = rodrigues_rotation_matrix(axis, angle)

        # 2. 如果有 roll，需要在对齐后绕对齐轴滚转
        if abs(self.roll) < 1e-8 or norm < 1e-8:
            R_total = R_align
        else:
            # 对齐后中轴方向 = v_target
            axis = dir_vec / norm
            R_roll = rodrigues_rotation_matrix(axis, self.roll)
            # 先对齐，再滚转：R_total = R_roll @ R_align
            R_total = R_roll @ R_align

        # 3. 构造 4x4 变换矩阵
        mat = QtGui.QMatrix4x4()
        # 填充旋转部分
        for i in range(3):
            for j in range(3):
                mat[i, j] = R_total[i, j]
        # 填充平移部分：本地原点(0,0,0)映射到世界 pos
        mat[0, 3] = self.pos[0]
        mat[1, 3] = self.pos[1]
        mat[2, 3] = self.pos[2]

        # 应用
        self.setTransform(mat)

    def set_position(self, pos):
        self.pos = np.array(pos, dtype=float)
        self.update_transform()

    def set_direction(self, direction):
        self.direction = np.array(direction, dtype=float)
        self.update_transform()

    def set_roll(self, roll):
        self.roll = float(roll)
        self.update_transform()

class Cylinder3D(GLMeshItem):
    """
    圆柱形图标类，用于三维地面站的可视化。
    """

    def __init__(self, position, radius=0.3, length=1.0, cols=32, color=(1, 1, 0, 1)):
        """
        初始化 Cylinder3D。

        :param position: 圆柱体中心点 (x, y, z)
        :param radius: 圆柱半径
        :param length: 圆柱高度
        :param cols: 圆周分段数
        :param color: RGBA 颜色
        """
        self.radius = radius
        self.length = length
        self.cols = cols
        self.color = color
        self.position = position

        # 创建 meshData
        mesh_data = self._mesh_cylinder()

        # 初始化父类 GLMeshItem
        super().__init__(
            meshdata=mesh_data,
            smooth=True,
            color=self.color,
            shader="shaded",
            drawFaces=True
        )

        # 平移到指定位置，并居中
        self.translate(*self.position)
        self.translate(0, 0, -self.length / 2)

    def _mesh_cylinder(self):
        """
        创建一个封顶封底、法线平滑、顶点不重复的圆柱体 MeshData。
        圆柱沿 Z 轴方向，底部在 z=0，顶部在 z=length。
        """
        # 角度分段
        angle = np.linspace(0, 2 * np.pi, self.cols, endpoint=False)
        x = self.radius * np.cos(angle)
        y = self.radius * np.sin(angle)
        z_bottom = np.zeros(self.cols)
        z_top = np.full(self.cols, self.length)

        # 生成侧面顶点：交错 bottom, top, bottom, top ...
        verts = []
        for i in range(self.cols):
            verts.append([x[i], y[i], z_bottom[i]])
            verts.append([x[i], y[i], z_top[i]])
        verts = np.array(verts, dtype=np.float32)

        # 添加底面中心和顶面中心
        bottom_center = [0, 0, 0]
        top_center = [0, 0, self.length]
        verts = np.vstack([verts, bottom_center, top_center])
        bottom_center_idx = len(verts) - 2
        top_center_idx = len(verts) - 1

        # 构造侧面三角形
        faces = []
        for i in range(self.cols):
            i0 = i * 2
            i1 = i * 2 + 1
            i2 = (i * 2 + 2) % (self.cols * 2)
            i3 = (i * 2 + 3) % (self.cols * 2)
            faces.append([i0, i2, i1])
            faces.append([i2, i3, i1])

        # 底面三角形
        for i in range(self.cols):
            i0 = i * 2
            i1 = (i * 2 + 2) % (self.cols * 2)
            faces.append([bottom_center_idx, i0, i1])

        # 顶面三角形
        for i in range(self.cols):
            i0 = i * 2 + 1
            i1 = (i * 2 + 3) % (self.cols * 2)
            faces.append([top_center_idx, i1, i0])

        faces = np.array(faces, dtype=np.int32)

        return gl.MeshData(vertexes=verts, faces=faces)


# class Line3D(GLMeshItem):
#     def __init__(self, start, end, color=(1,0,0,1), radius=0.05, sectors=16):
#         """
#         绘制一个“粗线” —— 用圆柱体表示一条线段，粗细是 radius。
#
#         :param start: np.ndarray, (3,), 起点
#         :param end: np.ndarray, (3,), 终点
#         :param color: tuple, RGBA
#         :param radius: float, 圆柱体半径 (线条粗细)
#         :param sectors: int, 圆柱体圆周分段数
#         """
#         self.start = np.asarray(start)
#         self.end = np.asarray(end)
#         self.radius = radius
#         self.color = color
#         self.sectors = sectors
#
#         meshdata = self._create_cylinder_mesh()
#
#         super().__init__(meshdata=meshdata, color=self.color, smooth=True, shader='shaded', drawEdges=False)
#
#     def _create_cylinder_mesh(self):
#         """
#         创建一根朝 Z 正方向的单位高度圆柱体，再旋转缩放平移到正确位置
#         """
#         # 默认单位圆柱体：高度=1，底部 z=0，顶部 z=1
#         theta = np.linspace(0, 2 * np.pi, self.sectors, endpoint=False)
#         x = np.cos(theta)
#         y = np.sin(theta)
#         z0 = np.zeros_like(x)
#         z1 = np.ones_like(x)
#
#         # 侧面顶点
#         verts = []
#         for i in range(len(x)):
#             verts.append([x[i], y[i], z0[i]])
#             verts.append([x[i], y[i], z1[i]])
#         verts = np.array(verts, dtype=np.float32)
#
#         # 顶底中心点
#         verts = np.vstack([verts,
#                            [0, 0, 0],
#                            [0, 0, 1]])
#
#         bottom_center_idx = len(verts) - 2
#         top_center_idx = len(verts) - 1
#
#         faces = []
#
#         # 侧面
#         for i in range(self.sectors):
#             i0 = i * 2
#             i1 = i * 2 + 1
#             i2 = (i * 2 + 2) % (self.sectors * 2)
#             i3 = (i * 2 + 3) % (self.sectors * 2)
#
#             faces.append([i0, i2, i1])
#             faces.append([i2, i3, i1])
#
#         # 底面
#         for i in range(self.sectors):
#             i0 = i * 2
#             i1 = (i * 2 + 2) % (self.sectors * 2)
#             faces.append([bottom_center_idx, i0, i1])
#
#         # 顶面
#         for i in range(self.sectors):
#             i0 = i * 2 + 1
#             i1 = (i * 2 + 3) % (self.sectors * 2)
#             faces.append([top_center_idx, i1, i0])
#
#         verts = verts * self.radius   # 缩放半径
#
#         # 计算长度和方向
#         vec = self.end - self.start
#         length = np.linalg.norm(vec)
#         if length == 0:
#             raise ValueError("start and end points are identical.")
#
#         # 沿 z 轴缩放到目标长度
#         verts[:,2] *= length
#
#         # 求旋转矩阵
#         z_axis = np.array([0, 0, 1])
#         vec_norm = vec / length
#         rot_axis = np.cross(z_axis, vec_norm)
#         rot_angle = np.arccos(np.clip(np.dot(z_axis, vec_norm), -1, 1))
#
#         if np.linalg.norm(rot_axis) < 1e-6:
#             # 不需要旋转
#             rotation = np.eye(3)
#         else:
#             rot_axis = rot_axis / np.linalg.norm(rot_axis)
#             r = R.from_rotvec(rot_angle * rot_axis)
#             rotation = r.as_matrix()
#
#         verts = verts @ rotation.T
#         verts += self.start
#
#         return MeshData(vertexes=verts, faces=np.array(faces, dtype=np.int32))

class Line3D(GLMeshItem):
    def __init__(self, start, end, color=(1,0,0,1), radius=0.05, sectors=16):
        self.start = np.asarray(start)
        self.end = np.asarray(end)
        self.radius = radius
        self.color = color
        self.sectors = sectors

        meshdata = self._create_cylinder_mesh()
        super().__init__(meshdata=meshdata, color=self.color,
                         smooth=True, drawEdges=False)

    def _create_cylinder_mesh(self):
        # 创建 [-0.5, +0.5] 高度的单位圆柱体
        theta = np.linspace(0, 2 * np.pi, self.sectors, endpoint=False)
        x = np.cos(theta)
        y = np.sin(theta)
        z0 = -0.5 * np.ones_like(x)
        z1 = +0.5 * np.ones_like(x)

        verts = []
        for i in range(len(x)):
            verts.append([x[i], y[i], z0[i]])
            verts.append([x[i], y[i], z1[i]])
        verts = np.array(verts, dtype=np.float32)

        # 顶底中心点
        verts = np.vstack([verts,
                           [0, 0, -0.5],
                           [0, 0, +0.5]])

        bottom_center_idx = len(verts) - 2
        top_center_idx = len(verts) - 1

        faces = []

        # 侧面
        for i in range(self.sectors):
            i0 = i * 2
            i1 = i * 2 + 1
            i2 = (i * 2 + 2) % (self.sectors * 2)
            i3 = (i * 2 + 3) % (self.sectors * 2)

            faces.append([i0, i2, i1])
            faces.append([i2, i3, i1])

        # 底面
        for i in range(self.sectors):
            i0 = i * 2
            i1 = (i * 2 + 2) % (self.sectors * 2)
            faces.append([bottom_center_idx, i0, i1])

        # 顶面
        for i in range(self.sectors):
            i0 = i * 2 + 1
            i1 = (i * 2 + 3) % (self.sectors * 2)
            faces.append([top_center_idx, i1, i0])

        verts[:,:2] = verts[:,:2] * self.radius

        # 计算旋转和平移
        vec = self.end - self.start
        length = np.linalg.norm(vec)
        if length == 0:
            raise ValueError("start and end points are identical.")

        # 缩放高度
        verts[:,2] *= length

        # 旋转到目标方向
        z_axis = np.array([0, 0, 1])
        vec_norm = vec / length
        rot_axis = np.cross(z_axis, vec_norm)
        rot_angle = np.arccos(np.clip(np.dot(z_axis, vec_norm), -1, 1))

        if np.linalg.norm(rot_axis) < 1e-6:
            rotation = np.eye(3)
        else:
            rot_axis = rot_axis / np.linalg.norm(rot_axis)
            r = R.from_rotvec(rot_angle * rot_axis)
            rotation = r.as_matrix()

        verts = verts @ rotation.T

        # 平移到中心
        center = (self.start + self.end) * 0.5
        verts += center

        return MeshData(vertexes=verts, faces=np.array(faces, dtype=np.int32))