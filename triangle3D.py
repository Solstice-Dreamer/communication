# import numpy as np
# from pyqtgraph.opengl import GLMeshItem, MeshData
# from pyqtgraph.Qt import QtGui
#
# class Triangle3D(GLMeshItem):
#     def __init__(self, pos, direction, length=0.4, width=0.1, color=(1, 0, 0, 1), smooth=False):
#         """
#         pos: 三角形底边中心在世界坐标中的位置 [x, y, z]
#         quat: UAV 朝向的四元数 [w, x, y, z]。默认本地三角尖头朝 +Y。
#         length: 三角形高度，从底边中心到尖头的长度
#         width: 底边宽度
#         color: RGBA 颜色元组
#         smooth: 是否平滑渲染，平面三角形通常不需要平滑
#         """
#         # 先构造本地坐标系下的顶点：底边中心在 (0,0,0)
#         # 底边两个顶点：(-width/2, 0, 0) 和 (width/2, 0, 0)
#         # 尖头顶点： (0, length, 0)
#         verts = np.array([
#             [0.0, length, 0.0],
#             [-width/2.0, 0.0, 0.0],
#             [ width/2.0, 0.0, 0.0]
#         ], dtype=float)
#         faces = np.array([[0, 1, 2]], dtype=int)
#
#         meshdata = MeshData(vertexes=verts, faces=faces)
#         super().__init__(meshdata=meshdata, smooth=smooth, color=color, shader='shaded', drawEdges=False)
#
#         # 存储属性
#         self.pos = np.array(pos, dtype=float)
#         self.direction = np.array(direction, dtype=float)
#         self.width = width
#         self.length = length
#
#         # 应用初始变换
#         self.update_transform()
#
#     def update_transform(self):
#         """
#         根据 self.quat 旋转本地三角（默认指向 +Y），并将底边中心平移到 self.pos
#         """
#         R = quaternion_to_rotation_matrix(self.quat)
#         mat = QtGui.QMatrix4x4()
#
#         # 设置旋转：将本地坐标系 X、Y、Z 根据 R 旋转
#         for i in range(3):
#             for j in range(3):
#                 mat[i, j] = R[i, j]
#
#         # 设置平移：将三角形底边中心移动到世界坐标 pos
#         mat[0, 3] = self.pos[0]
#         mat[1, 3] = self.pos[1]
#         mat[2, 3] = self.pos[2]
#
#         # 应用变换
#         self.setTransform(mat)
#
#     def set_position(self, pos):
#         """
#         更新位置后刷新：pos 是三角底边中心的世界坐标 [x, y, z]
#         """
#         self.pos = np.array(pos, dtype=float)
#         self.update_transform()
#
#     def set_quaternion(self, quat):
#         """
#         更新朝向四元数后刷新：quat = [w, x, y, z]
#         """
#         self.quat = np.array(quat, dtype=float)
#         self.update_transform()

import numpy as np
from pyqtgraph.opengl import GLMeshItem, MeshData
from pyqtgraph.Qt import QtGui

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

class Triangle3D(GLMeshItem):
    def __init__(self, pos, direction, length=0.4, width=0.1, color=(1, 0, 0, 1), roll=0.0, smooth=False):
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
