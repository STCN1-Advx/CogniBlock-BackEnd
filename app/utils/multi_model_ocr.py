"""
多模型 OCR 图片文字识别库
支持 Gemini 和 Qwen-VL 模型，提供流式输出功能

作者: AI Assistant
版本: 2.0.0
支持模型:
- Google Gemini: gemini-2.5-pro, gemini-2.0-flash-exp
- Alibaba Qwen-VL: qwen-vl-plus, qwen-vl-max-latest

使用方法:
    from app.utils.multi_model_ocr import MultiModelOCR
    
    # 初始化
    ocr = MultiModelOCR()
    
    # 使用 Gemini 模型
    result = ocr.extract_text("image.jpg", model="gemini-2.5-pro")
    
    # 使用 Qwen 模型（流式输出）
    for chunk in ocr.extract_text_stream("image.jpg", model="qwen-vl-plus"):
        print(chunk, end="")
"""

import os
import base64
import requests
from typing import Union, Optional, Iterator, Dict, Any, Callable
from pathlib import Path
from PIL import Image
import io
import json
from google import genai
from google.genai import types
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class ModelConfig:
    """模型配置类"""
    
    # Gemini 模型配置
    GEMINI_MODELS = {
        "gemini-2.5-pro": {
            "name": "gemini-2.5-pro",
            "provider": "google",
            "supports_stream": True,
            "max_tokens": 8192,
            "description": "Gemini 2.5 Pro - 最强性能模型"
        },
        "gemini-2.0-flash-exp": {
            "name": "gemini-2.0-flash-exp", 
            "provider": "google",
            "supports_stream": True,
            "max_tokens": 8192,
            "description": "Gemini 2.0 Flash - 快速响应模型"
        }
    }
    
    # Qwen 模型配置
    QWEN_MODELS = {
        "qwen-vl-plus": {
            "name": "qwen-vl-plus",
            "provider": "alibaba",
            "supports_stream": True,
            "max_tokens": 8192,
            "description": "Qwen-VL Plus - 高性价比视觉理解模型"
        },
        "qwen-vl-max-latest": {
            "name": "qwen-vl-max-latest",
            "provider": "alibaba", 
            "supports_stream": True,
            "max_tokens": 8192,
            "description": "Qwen-VL Max - 最强视觉理解模型"
        }
    }
    
    # PPInfra 模型配置
    PPINFRA_MODELS = {
        "qwen/qwen2.5-vl-72b-instruct": {
            "name": "qwen/qwen2.5-vl-72b-instruct",
            "provider": "ppinfra",
            "supports_stream": True,
            "max_tokens": 8192,
            "description": "Qwen2.5-VL 72B - PPInfra提供的高性能视觉理解模型"
        }
    }
    
    @classmethod
    def get_all_models(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有支持的模型"""
        return {**cls.GEMINI_MODELS, **cls.QWEN_MODELS, **cls.PPINFRA_MODELS}
    
    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """获取指定模型的信息"""
        return cls.get_all_models().get(model_name)


class MultiModelOCR:
    """
    多模型 OCR 识别类
    支持 Google Gemini 和 Alibaba Qwen-VL 模型
    """
    
    def __init__(self, 
                 gemini_api_key: Optional[str] = None,
                 qwen_api_key: Optional[str] = None,
                 qwen_base_url: Optional[str] = None,
                 ppinfra_api_key: Optional[str] = None,
                 ppinfra_base_url: Optional[str] = None):
        """
        初始化多模型 OCR 客户端
        
        Args:
            gemini_api_key: Gemini API 密钥
            qwen_api_key: Qwen API 密钥  
            qwen_base_url: Qwen API 基础 URL
            ppinfra_api_key: PPInfra API 密钥
            ppinfra_base_url: PPInfra API 基础 URL
        """
        # Gemini 配置
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.gemini_client = None
        if self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                print(f"Gemini 客户端初始化失败: {e}")
        
        # Qwen 配置
        self.qwen_api_key = qwen_api_key or os.getenv('DASHSCOPE_API_KEY')
        self.qwen_base_url = qwen_base_url or os.getenv('DASHSCOPE_BASE_URL', 
                                                       'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.qwen_client = None
        if self.qwen_api_key:
            try:
                self.qwen_client = OpenAI(
                    api_key=self.qwen_api_key,
                    base_url=self.qwen_base_url
                )
            except Exception as e:
                print(f"Qwen 客户端初始化失败: {e}")
        
        # PPInfra 配置
        self.ppinfra_api_key = ppinfra_api_key or os.getenv('PPINFRA_API_KEY')
        self.ppinfra_base_url = ppinfra_base_url or os.getenv('PPINFRA_BASE_URL', 
                                                             'https://api.ppinfra.com/v3/openai')
        self.ppinfra_client = None
        if self.ppinfra_api_key:
            try:
                self.ppinfra_client = OpenAI(
                    api_key=self.ppinfra_api_key,
                    base_url=self.ppinfra_base_url
                )
            except Exception as e:
                print(f"PPInfra 客户端初始化失败: {e}")
    
    def _load_image_from_path(self, image_path: Union[str, Path]) -> bytes:
        """从本地路径加载图片"""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        with open(image_path, 'rb') as f:
            return f.read()
    
    def _load_image_from_url(self, image_url: str) -> bytes:
        """从网络 URL 加载图片"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise Exception(f"无法从 URL 加载图片: {e}")
    
    def _get_mime_type(self, image_data: bytes) -> str:
        """根据图片数据判断 MIME 类型"""
        try:
            image = Image.open(io.BytesIO(image_data))
            format_to_mime = {
                'JPEG': 'image/jpeg',
                'PNG': 'image/png', 
                'GIF': 'image/gif',
                'BMP': 'image/bmp',
                'WEBP': 'image/webp'
            }
            return format_to_mime.get(image.format, 'image/jpeg')
        except Exception:
            return 'image/jpeg'
    
    def _prepare_image_data(self, image_source: Union[str, Path, bytes]) -> tuple[bytes, str]:
        """准备图片数据和 MIME 类型"""
        if isinstance(image_source, bytes):
            image_data = image_source
        elif isinstance(image_source, (str, Path)):
            image_source_str = str(image_source)
            if image_source_str.startswith(('http://', 'https://')):
                image_data = self._load_image_from_url(image_source_str)
            else:
                image_data = self._load_image_from_path(image_source)
        else:
            raise ValueError("不支持的图片来源类型")
        
        mime_type = self._get_mime_type(image_data)
        return image_data, mime_type
    
    def _extract_text_gemini(self, 
                           image_data: bytes, 
                           mime_type: str,
                           prompt: str, 
                           model: str,
                           stream: bool = False) -> Union[str, Iterator[str]]:
        """使用 Gemini 模型提取文字"""
        if not self.gemini_client:
            raise ValueError("Gemini 客户端未初始化，请检查 API 密钥")
        
        # 创建图片部分
        image_part = types.Part.from_bytes(
            data=image_data,
            mime_type=mime_type
        )
        
        try:
            if stream:
                # 流式输出
                response = self.gemini_client.models.generate_content_stream(
                    model=model,
                    contents=[prompt, image_part]
                )
                
                def stream_generator():
                    for chunk in response:
                        if hasattr(chunk, 'text') and chunk.text:
                            yield chunk.text
                
                return stream_generator()
            else:
                # 非流式输出
                response = self.gemini_client.models.generate_content(
                    model=model,
                    contents=[prompt, image_part]
                )
                return response.text
                
        except Exception as e:
            raise Exception(f"Gemini OCR 识别失败: {e}")
    
    def _extract_text_qwen(self, 
                         image_source: Union[str, Path, bytes],
                         prompt: str, 
                         model: str,
                         stream: bool = False) -> Union[str, Iterator[str]]:
        """使用 Qwen 模型提取文字"""
        if not self.qwen_client:
            raise ValueError("Qwen 客户端未初始化，请检查 API 密钥")
        
        # 准备图片 URL 或 base64 数据
        if isinstance(image_source, (str, Path)):
            image_source_str = str(image_source)
            if image_source_str.startswith(('http://', 'https://')):
                # 网络图片直接使用 URL
                image_url = image_source_str
            else:
                # 本地图片转换为 base64
                image_data, mime_type = self._prepare_image_data(image_source)
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_url = f"data:{mime_type};base64,{image_base64}"
        else:
            # 字节数据转换为 base64
            image_data, mime_type = self._prepare_image_data(image_source)
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{image_base64}"
        
        # 构建消息
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful OCR assistant."}]
            },
            {
                "role": "user", 
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        try:
            if stream:
                # 流式输出
                response = self.qwen_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True
                )
                
                def stream_generator():
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                
                return stream_generator()
            else:
                # 非流式输出
                response = self.qwen_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=False
                )
                return response.choices[0].message.content
                
        except Exception as e:
            raise Exception(f"Qwen OCR 识别失败: {e}")
    
    def _extract_text_ppinfra(self, 
                             image_source: Union[str, Path, bytes],
                             prompt: str,
                             model: str,
                             stream: bool = False) -> Union[str, Iterator[str]]:
        """
        使用 PPInfra API 进行文字识别
        
        Args:
            image_source: 图片来源（文件路径、URL 或字节数据）
            prompt: 提示词
            model: 模型名称
            stream: 是否流式输出
            
        Returns:
            识别结果或流式生成器
        """
        if not self.ppinfra_client:
            raise Exception("PPInfra 客户端未初始化")
        
        # 准备图片数据
        if isinstance(image_source, str) and (image_source.startswith('http://') or image_source.startswith('https://')):
            # URL 格式
            image_url = image_source
        else:
            # 本地文件或字节数据，转换为 base64
            if isinstance(image_source, (str, Path)):
                with open(image_source, 'rb') as f:
                    image_data = f.read()
            else:
                image_data = image_source
            
            # 获取 MIME 类型
            mime_type = self._get_mime_type(image_data)
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{image_base64}"
        
        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        try:
            if stream:
                # 流式输出
                response = self.ppinfra_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True
                )
                
                def stream_generator():
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                
                return stream_generator()
            else:
                # 非流式输出
                response = self.ppinfra_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=False
                )
                return response.choices[0].message.content
                
        except Exception as e:
            raise Exception(f"PPInfra OCR 识别失败: {e}")
    
    def extract_text(self, 
                    image_source: Union[str, Path, bytes],
                    prompt: str = "请提取这张图片中的所有文字内容，保持原有的格式和布局。",
                    model: str = "gemini-2.5-pro") -> str:
        """
        从图片中提取文字（非流式）
        
        Args:
            image_source: 图片来源（文件路径、URL 或字节数据）
            prompt: 提示词
            model: 使用的模型名称
            
        Returns:
            提取的文字内容
        """
        model_info = ModelConfig.get_model_info(model)
        if not model_info:
            raise ValueError(f"不支持的模型: {model}")
        
        if model_info["provider"] == "google":
            image_data, mime_type = self._prepare_image_data(image_source)
            return self._extract_text_gemini(image_data, mime_type, prompt, model, stream=False)
        elif model_info["provider"] == "alibaba":
            return self._extract_text_qwen(image_source, prompt, model, stream=False)
        elif model_info["provider"] == "ppinfra":
            return self._extract_text_ppinfra(image_source, prompt, model, stream=False)
        else:
            raise ValueError(f"不支持的模型提供商: {model_info['provider']}")
    
    def extract_text_stream(self, 
                           image_source: Union[str, Path, bytes],
                           prompt: str = "请提取这张图片中的所有文字内容，保持原有的格式和布局。",
                           model: str = "qwen-vl-plus") -> Iterator[str]:
        """
        从图片中提取文字（流式输出）
        
        Args:
            image_source: 图片来源（文件路径、URL 或字节数据）
            prompt: 提示词
            model: 使用的模型名称
            
        Yields:
            文字内容片段
        """
        model_info = ModelConfig.get_model_info(model)
        if not model_info:
            raise ValueError(f"不支持的模型: {model}")
        
        if not model_info["supports_stream"]:
            raise ValueError(f"模型 {model} 不支持流式输出")
        
        if model_info["provider"] == "google":
            image_data, mime_type = self._prepare_image_data(image_source)
            yield from self._extract_text_gemini(image_data, mime_type, prompt, model, stream=True)
        elif model_info["provider"] == "alibaba":
            yield from self._extract_text_qwen(image_source, prompt, model, stream=True)
        elif model_info["provider"] == "ppinfra":
            yield from self._extract_text_ppinfra(image_source, prompt, model, stream=True)
        else:
            raise ValueError(f"不支持的模型提供商: {model_info['provider']}")
    
    def extract_text_with_structure(self, 
                                  image_source: Union[str, Path, bytes],
                                  model: str = "gemini-2.5-pro",
                                  stream: bool = False) -> Union[str, Iterator[str]]:
        """
        提取图片中的文字并保持结构化格式
        
        Args:
            image_source: 图片来源
            model: 使用的模型
            stream: 是否使用流式输出
            
        Returns:
            结构化的文字内容或流式生成器
        """
        prompt = """请仔细分析这张图片中的所有文字内容，并按照以下要求输出：

1. 保持原有的文字布局和层次结构
2. 如果是表格，请用 Markdown 表格格式输出
3. 如果有标题、段落等层次，请用适当的 Markdown 格式标记
4. 保持文字的原始顺序和分组
5. 如果有特殊符号或格式，请尽量保留

请直接输出识别的文字内容，不要添加额外的说明。"""
        
        if stream:
            return self.extract_text_stream(image_source, prompt, model)
        else:
            return self.extract_text(image_source, prompt, model)
    
    def extract_specific_info(self, 
                            image_source: Union[str, Path, bytes],
                            target_info: str,
                            model: str = "gemini-2.5-pro",
                            stream: bool = False) -> Union[str, Iterator[str]]:
        """
        从图片中提取特定信息
        
        Args:
            image_source: 图片来源
            target_info: 要提取的特定信息描述
            model: 使用的模型
            stream: 是否使用流式输出
            
        Returns:
            提取的特定信息或流式生成器
        """
        prompt = f"""请从这张图片中提取以下特定信息：{target_info}

请只返回相关的信息，如果图片中没有相关内容，请回答"未找到相关信息"。"""
        
        if stream:
            return self.extract_text_stream(image_source, prompt, model)
        else:
            return self.extract_text(image_source, prompt, model)
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的模型信息"""
        available_models = {}
        
        # 检查 Gemini 模型可用性
        if self.gemini_client:
            for model_name, model_info in ModelConfig.GEMINI_MODELS.items():
                available_models[model_name] = {**model_info, "available": True}
        else:
            for model_name, model_info in ModelConfig.GEMINI_MODELS.items():
                available_models[model_name] = {**model_info, "available": False}
        
        # 检查 Qwen 模型可用性
        if self.qwen_client:
            for model_name, model_info in ModelConfig.QWEN_MODELS.items():
                available_models[model_name] = {**model_info, "available": True}
        else:
            for model_name, model_info in ModelConfig.QWEN_MODELS.items():
                available_models[model_name] = {**model_info, "available": False}
        
        # 检查 PPInfra 模型可用性
        if self.ppinfra_client:
            for model_name, model_info in ModelConfig.PPINFRA_MODELS.items():
                available_models[model_name] = {**model_info, "available": True}
        else:
            for model_name, model_info in ModelConfig.PPINFRA_MODELS.items():
                available_models[model_name] = {**model_info, "available": False}
        
        return available_models
    
    def test_model(self, model: str, test_image_url: str = None) -> Dict[str, Any]:
        """
        测试指定模型的可用性
        
        Args:
            model: 模型名称
            test_image_url: 测试图片 URL（可选）
            
        Returns:
            测试结果
        """
        if not test_image_url:
            test_image_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
        
        try:
            result = self.extract_text(
                test_image_url, 
                "请简单描述这张图片的内容。", 
                model
            )
            return {
                "model": model,
                "status": "success",
                "result": result[:100] + "..." if len(result) > 100 else result
            }
        except Exception as e:
            return {
                "model": model,
                "status": "error", 
                "error": str(e)
            }