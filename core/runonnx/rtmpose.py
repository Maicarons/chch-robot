import numpy as np
import cv2
from typing import Tuple, List, Union
from .base_onnx import BaseONNX

class RTMPOSE_ONNX(BaseONNX):

    bone_names = [
        "A0", "A8",
        "J0", "J8",
    ]


    skeleton_links = [
        "A0-A8",
        "A8-J8",
        "J8-J0",
        "J0-A0",
    ]

    def __init__(self, 
                model_path, input_size=(256, 256),
                padding=1.25,
                bone_names=None,
                skeleton_links=None,
                ):
        super().__init__(model_path, input_size)
        self.padding = padding

        if bone_names is not None:
            self.bone_names = bone_names

        if skeleton_links is not None:
            self.skeleton_links = skeleton_links

        self.bone_colors = np.random.randint(0, 256, (len(self.bone_names), 3))

    
    def get_bbox_center_scale(self, bbox: List[int]):
        """Convert bounding box to center and scale.
        
        The center is the coordinates of the bbox center, and the scale is the 
        bbox width and height normalized by the padding factor.
        
        Args:
            bbox: Bounding box in format [x1, y1, x2, y2]
            
        Returns:
            tuple: A tuple containing:
                - center (numpy.ndarray): Center coordinates [x, y]
                - scale (numpy.ndarray): Scale [width, height] 
        """
        
        # Get bbox center
        x1, y1, x2, y2 = bbox
        center = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])
        
        # Get bbox scale (width and height)
        w = x2 - x1
        h = y2 - y1
        
        # Convert to scaled width/height
        scale = np.array([w, h]) * self.padding
        
        return center, scale


    @staticmethod
    def _rotate_point(pt: np.ndarray, angle_rad: float) -> np.ndarray:
        """Rotate a point by an angle.

        Args:
            pt (np.ndarray): 2D point coordinates (x, y) in shape (2, )
            angle_rad (float): rotation angle in radian

        Returns:
            np.ndarray: Rotated point in shape (2, )
        """

        sn, cs = np.sin(angle_rad), np.cos(angle_rad)
        rot_mat = np.array([[cs, -sn], [sn, cs]])
        return rot_mat @ pt


    @staticmethod
    def _get_3rd_point(a: np.ndarray, b: np.ndarray):
        """To calculate the affine matrix, three pairs of points are required. This
        function is used to get the 3rd point, given 2D points a & b.

        The 3rd point is defined by rotating vector `a - b` by 90 degrees
        anticlockwise, using b as the rotation center.

        Args:
            a (np.ndarray): The 1st point (x,y) in shape (2, )
            b (np.ndarray): The 2nd point (x,y) in shape (2, )

        Returns:
            np.ndarray: The 3rd point.
        """
        direction = a - b
        c = b + np.r_[-direction[1], direction[0]]
        return c


    @staticmethod
    def get_warp_matrix(
        center: np.ndarray,
        scale: np.ndarray,
        rot: float,
        output_size: Tuple[int, int],
        shift: Tuple[float, float] = (0., 0.),
        inv: bool = False,
        fix_aspect_ratio: bool = True,
    ) -> np.ndarray:
        """Calculate the affine transformation matrix that can warp the bbox area
        in the input image to the output size.

        Args:
            center (np.ndarray[2, ]): Center of the bounding box (x, y).
            scale (np.ndarray[2, ]): Scale of the bounding box
                wrt [width, height].
            rot (float): Rotation angle (degree).
            output_size (np.ndarray[2, ] | list(2,)): Size of the
                destination heatmaps.
            shift (0-100%): Shift translation ratio wrt the width/height.
                Default (0., 0.).
            inv (bool): Option to inverse the affine transform direction.
                (inv=False: src->dst or inv=True: dst->src)
            fix_aspect_ratio (bool): Whether to fix aspect ratio during transform.
                Defaults to True.

        Returns:
            np.ndarray: A 2x3 transformation matrix
        """
        assert len(center) == 2
        assert len(scale) == 2
        assert len(output_size) == 2
        assert len(shift) == 2

        shift = np.array(shift)
        src_w, src_h = scale[:2]
        dst_w, dst_h = output_size[:2]

        rot_rad = np.deg2rad(rot)
        src_dir = RTMPOSE_ONNX._rotate_point(np.array([src_w * -0.5, 0.]), rot_rad)
        dst_dir = np.array([dst_w * -0.5, 0.])

        src = np.zeros((3, 2), dtype=np.float32)
        src[0, :] = center + scale * shift
        src[1, :] = center + src_dir + scale * shift

        dst = np.zeros((3, 2), dtype=np.float32)
        dst[0, :] = [dst_w * 0.5, dst_h * 0.5]
        dst[1, :] = np.array([dst_w * 0.5, dst_h * 0.5]) + dst_dir

        if fix_aspect_ratio:
            src[2, :] = RTMPOSE_ONNX._get_3rd_point(src[0, :], src[1, :])
            dst[2, :] = RTMPOSE_ONNX._get_3rd_point(dst[0, :], dst[1, :])
        else:
            src_dir_2 = RTMPOSE_ONNX._rotate_point(np.array([0., src_h * -0.5]), rot_rad)
            dst_dir_2 = np.array([0., dst_h * -0.5])
            src[2, :] = center + src_dir_2 + scale * shift
            dst[2, :] = np.array([dst_w * 0.5, dst_h * 0.5]) + dst_dir_2

        if inv:
            warp_mat = cv2.getAffineTransform(np.float32(dst), np.float32(src))
        else:
            warp_mat = cv2.getAffineTransform(np.float32(src), np.float32(dst))
        return warp_mat


    def get_warp_size_with_input_size(self, 
                                      bbox_center: List[int], 
                                      bbox_scale: List[int],
                                      inv: bool = False,
                                      ):
        """
        获取仿射变换矩阵的输出尺寸
        """

        w, h = self.input_size
        warp_size = self.input_size
        
        # 修正长宽比
        scale_w, scale_h = bbox_scale
        aspect_ratio = w / h
        if scale_w > scale_h * aspect_ratio:
            bbox_scale = [scale_w, scale_w / aspect_ratio]
        else:
            bbox_scale = [scale_h * aspect_ratio, scale_h]
        
        # 计算仿射变换矩阵 确保数据类型正确
        center = np.array(bbox_center, dtype=np.float32)
        scale = np.array(bbox_scale, dtype=np.float32)
        
        rot = 0.0  # 不考虑旋转
        
        warp_mat = self.get_warp_matrix(center, scale, rot, output_size=warp_size, inv=inv)

        return warp_mat

    def topdown_affine(self, img: cv2.UMat, bbox_center: List[int], bbox_scale: List[int]):
        """简化版的 top-down 仿射变换函数
        
        Args:
        img: 输入图像
        
        Returns:
            变换后的图像
        """
        
        warp_mat = self.get_warp_size_with_input_size(bbox_center, bbox_scale)

        # 应用仿射变换
        dst_img = cv2.warpAffine(img, warp_mat, self.input_size, flags=cv2.INTER_LINEAR)
        
        return dst_img
    

    # 获取每个关键点的最优预测位置
    def get_simcc_maximum(self, simcc_x, simcc_y):
        
        # 在最后一维上找到最大值的索引
        x_indices = np.argmax(simcc_x[0], axis=1)  # (N,)
        y_indices = np.argmax(simcc_y[0], axis=1)  # (N,)
        

        input_w, input_h = self.input_size

        # 将索引转换为实际坐标 (0-1之间)
        x_coords = x_indices / (input_w * 2)  # 归一化到0-1
        y_coords = y_indices / (input_h * 2)
        
        # 组合成坐标对
        keypoints = np.stack([x_coords, y_coords], axis=1)  # (N, 2)
        
        # 获取每个点的置信度分数
        scores = np.max(simcc_x[0], axis=1) * np.max(simcc_y[0], axis=1)
        
        return keypoints, scores



    def preprocess_image(self, img_bgr: cv2.UMat, bbox_center: List[int], bbox_scale: List[int]):

        """
        预处理图像

        Args:
            img_bgr (cv2.UMat): 输入图像
            bbox_center (list[int, int]): 边界框中心坐标 [x, y]
            bbox_scale (list[int, int]): 边界框尺度 [w, h]
        """

        affine_img_bgr = self.topdown_affine(img_bgr, bbox_center, bbox_scale)

        # 转RGB并进行归一化
        affine_img_rgb = cv2.cvtColor(affine_img_bgr, cv2.COLOR_BGR2RGB)
        # normalize mean and std
        affine_img_rgb_norm = (affine_img_rgb - np.array([123.675, 116.28, 103.53])) / np.array([58.395, 57.12, 57.375])
        # 转换为浮点型并归一化
        img = affine_img_rgb_norm.astype(np.float32)
        # 调整维度顺序 (H,W,C) -> (C,H,W)
        img = np.transpose(img, (2, 0, 1))
        # 添加 batch 维度
        img = np.expand_dims(img, axis=0)

        return img
    

    def run_inference(self, image: np.ndarray):
        """
        Run inference on the image.

        Args:
            image (np.ndarray): The image to run inference on.

        Returns:
            tuple: A tuple containing the detection results and labels.
        """
        # 运行推理
        outputs = self.session.run(None, {self.input_name: image})
        """
        simcc_x: float32[batch,MatMulsimcc_x_dim_1,512]
        simcc_y: float32[batch,MatMulsimcc_x_dim_1,512]
        """
        simcc_x, simcc_y = outputs

        return simcc_x, simcc_y

    def pred(self, image: List[Union[cv2.UMat, str]], bbox: List[int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict the keypoints results of the image.

        Args:
            image (str | cv2.UMat): The image to predict.
            bbox (list[int, int, int, int]): The bounding box to predict.

        Returns:
            keypoints (np.ndarray): The predicted keypoints.
            scores (np.ndarray): The predicted scores.
        """
        if isinstance(image, str):
            img_bgr = cv2.imread(image)
        else:
            img_bgr = image.copy()

        bbox_center, bbox_scale = self.get_bbox_center_scale(bbox)

        image = self.preprocess_image(img_bgr, bbox_center, bbox_scale)
        simcc_x, simcc_y  = self.run_inference(image)

        # 获取SimCC预测的最大值位置，返回关键点坐标和置信度分数
        # 对应 width 和 height 为  input_size 的归一化，即 （256,256）
        keypoints, scores = self.get_simcc_maximum(simcc_x, simcc_y)

        # 将预测的关键点坐标从模型输出尺寸映射回原图尺寸
        keypoints = self.transform_keypoints_to_original(keypoints, bbox_center, bbox_scale, self.input_size)

        return keypoints, scores
    
    def transform_keypoints_to_original(self, keypoints, center, scale, output_size):
        """
        将预测的关键点坐标从模型输出尺寸映射回原图尺寸
        
        Args:
            keypoints: 预测的关键点坐标 [N, 2]
            center: bbox中心点 [x, y]
            scale: bbox尺度 [w, h]
            output_size: 模型输入尺寸 (w, h)

        Returns:
            np.ndarray: 转换后的关键点坐标 [N, 2]
        """
        target_coords = keypoints.copy()
    
        # 将0-1的预测坐标转换为像素坐标， 256*256
        target_coords[:, 0] = target_coords[:, 0] * output_size[0]
        target_coords[:, 1] = target_coords[:, 1] * output_size[1]
        
        # 计算仿射变换矩阵
        warp_mat = self.get_warp_size_with_input_size(center, scale, inv=True)
        
        # 转换为齐次坐标
        ones = np.ones((len(target_coords), 1))
        target_coords_homogeneous = np.hstack([target_coords, ones])
        
        # 应用逆变换
        original_keypoints = target_coords_homogeneous @ warp_mat.T
        
        return original_keypoints
    
    def draw_pred(self, 
                  img: cv2.UMat, 
                  keypoints: np.ndarray, 
                  scores: np.ndarray, 
                  is_rgb: bool = True,
                  score_threshold: float = 0.6) -> cv2.UMat:
        """
        Draw the keypoints results on the image.
        """

        if not is_rgb:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        colors = self.bone_colors

        for i, (point, score) in enumerate(zip(keypoints, scores)):
           
                x, y = map(int, point)
                # 使用不同颜色标注不同的关键点
                color = colors[i]

                cv2.circle(img, (x, y), 5, (int(color[0]), int(color[1]), int(color[2])), -1)
                # 添加关键点索引标注
                if score < score_threshold:  # 设置置信度阈值
                    text = f"{self.bone_names[i]}: {score:.2f}"
                else:
                    text = f"{self.bone_names[i]}"
                cv2.putText(img, text, (x+5, y+5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (int(color[0]), int(color[1]), int(color[2])), 2)
                
                # 绘制 关节连接线
        for link in self.skeleton_links:
            start_bone, end_bone = link.split("-")

            start_index = self.bone_names.index(start_bone)
            end_index = self.bone_names.index(end_bone)

            start_keypoint = keypoints[start_index]
            end_keypoint = keypoints[end_index]
            link_color = colors[start_index]

            # 绘制连线
            if scores[start_index] > score_threshold and scores[end_index] > score_threshold:
                start_point = tuple(map(int, start_keypoint))
                end_point = tuple(map(int, end_keypoint))
                cv2.line(img, start_point, end_point, 
                        (int(link_color[0]), int(link_color[1]), int(link_color[2])), 
                        thickness=2)
                
        return img
    
