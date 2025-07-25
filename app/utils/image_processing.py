"""
图片处理工具模块
从PoltNoteOCR项目迁移的图片处理功能
"""

import io
from PIL import Image, ImageFilter, ImageEnhance
import cv2
import numpy as np

def preprocess_image_color(image_data: bytes, mimetype: str) -> bytes:
    """
    彩色图片预处理
    增强对比度和清晰度
    """
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # 增强清晰度
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        # 保存为字节
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95)
        
        return output.getvalue()
        
    except Exception as e:
        # 如果处理失败，返回原图
        return image_data

def preprocess_image_to_grayscale(image_data: bytes, mimetype: str) -> bytes:
    """
    转换为灰度图并进行预处理
    """
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为灰度
        grayscale = image.convert('L')
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(grayscale)
        grayscale = enhancer.enhance(1.3)
        
        # 保存为字节
        output = io.BytesIO()
        grayscale.save(output, format='JPEG', quality=95)
        
        return output.getvalue()
        
    except Exception as e:
        # 如果处理失败，返回原图
        return image_data

def preprocess_image_edges(image_data: bytes, mimetype: str) -> bytes:
    """
    边缘检测预处理
    """
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为灰度
        grayscale = image.convert('L')
        
        # 转换为numpy数组
        img_array = np.array(grayscale)
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(img_array, (5, 5), 0)
        
        # Canny边缘检测
        edges = cv2.Canny(blurred, 50, 150)
        
        # 转换回PIL图片
        edge_image = Image.fromarray(edges)
        
        # 保存为字节
        output = io.BytesIO()
        edge_image.save(output, format='JPEG', quality=95)
        
        return output.getvalue()
        
    except Exception as e:
        # 如果处理失败，返回原图
        return image_data

def auto_crop_document(image_data: bytes) -> bytes:
    """
    自动裁剪文档边界
    """
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 转换为灰度
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 边缘检测
        edges = cv2.Canny(blurred, 50, 150)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 找到最大的轮廓
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 获取边界框
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 添加一些边距
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(image.width - x, w + 2 * margin)
            h = min(image.height - y, h + 2 * margin)
            
            # 裁剪图片
            cropped = image.crop((x, y, x + w, y + h))
            
            # 保存为字节
            output = io.BytesIO()
            cropped.save(output, format='JPEG', quality=95)
            
            return output.getvalue()
        
        # 如果没有找到合适的轮廓，返回原图
        return image_data
        
    except Exception as e:
        # 如果处理失败，返回原图
        return image_data

def enhance_text_clarity(image_data: bytes) -> bytes:
    """
    增强文字清晰度
    """
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为灰度
        if image.mode != 'L':
            image = image.convert('L')
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 自适应阈值处理
        adaptive_thresh = cv2.adaptiveThreshold(
            img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 形态学操作去噪
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
        
        # 转换回PIL图片
        enhanced_image = Image.fromarray(cleaned)
        
        # 保存为字节
        output = io.BytesIO()
        enhanced_image.save(output, format='JPEG', quality=95)
        
        return output.getvalue()
        
    except Exception as e:
        # 如果处理失败，返回原图
        return image_data