"""
Markdown处理工具
"""

import re
from typing import Optional
try:
    import markdown
    from markdown.extensions import codehilite, tables, toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

def extract_codeblock(text: str, language: str = "markdown") -> str:
    """
    从文本中提取代码块内容
    
    Args:
        text: 包含代码块的文本
        language: 代码块语言标识符
    
    Returns:
        提取的代码块内容，如果没有找到则返回原文本
    """
    # 匹配代码块的正则表达式
    pattern = rf"```{language}?\s*\n(.*?)\n```"
    
    # 查找代码块
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if matches:
        # 返回第一个匹配的代码块内容
        return matches[0].strip()
    
    # 如果没有找到指定语言的代码块，尝试查找任意代码块
    pattern = r"```\w*\s*\n(.*?)\n```"
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # 如果没有找到代码块，返回原文本
    return text.strip()

def convert_markdown_to_html(markdown_text: str) -> str:
    """
    将Markdown文本转换为HTML
    
    Args:
        markdown_text: Markdown格式的文本
    
    Returns:
        HTML格式的文本
    """
    if not MARKDOWN_AVAILABLE:
        # 如果markdown库不可用，进行简单的转换
        return simple_markdown_to_html(markdown_text)
    
    try:
        # 配置markdown扩展
        extensions = ['tables', 'codehilite', 'toc', 'fenced_code']
        
        # 转换为HTML
        md = markdown.Markdown(extensions=extensions)
        html = md.convert(markdown_text)
        
        return html
        
    except Exception as e:
        # 如果转换失败，使用简单转换
        return simple_markdown_to_html(markdown_text)

def simple_markdown_to_html(markdown_text: str) -> str:
    """
    简单的Markdown到HTML转换（不依赖外部库）
    """
    html = markdown_text
    
    # 标题转换
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.*?)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^###### (.*?)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    
    # 粗体和斜体
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # 代码块
    html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # 链接
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # 列表（简单处理）
    lines = html.split('\n')
    in_list = False
    result_lines = []
    
    for line in lines:
        if re.match(r'^\s*[-*+]\s+', line):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            item_text = re.sub(r'^\s*[-*+]\s+', '', line)
            result_lines.append(f'<li>{item_text}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    # 段落处理
    html = '\n'.join(result_lines)
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith('<'):
            para = f'<p>{para}</p>'
        html_paragraphs.append(para)
    
    return '\n'.join(html_paragraphs)

def clean_markdown_text(text: str) -> str:
    """
    清理Markdown文本，移除多余的空行和格式
    """
    # 移除多余的空行
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # 移除行首行尾的空白
    lines = [line.strip() for line in text.split('\n')]
    
    # 移除空行
    cleaned_lines = []
    for line in lines:
        if line or (cleaned_lines and cleaned_lines[-1]):
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

def validate_markdown(text: str) -> bool:
    """
    验证Markdown文本的基本格式
    """
    if not text or not text.strip():
        return False
    
    # 检查是否包含基本的Markdown元素
    has_content = bool(re.search(r'[a-zA-Z0-9\u4e00-\u9fff]', text))
    
    return has_content

def extract_markdown_metadata(text: str) -> dict:
    """
    提取Markdown文本的元数据信息
    """
    metadata = {
        'word_count': len(re.findall(r'\b\w+\b', text)),
        'line_count': len(text.split('\n')),
        'has_headers': bool(re.search(r'^#+\s+', text, re.MULTILINE)),
        'has_lists': bool(re.search(r'^\s*[-*+]\s+', text, re.MULTILINE)),
        'has_code': bool(re.search(r'`.*?`', text)),
        'has_links': bool(re.search(r'\[.*?\]\(.*?\)', text)),
        'has_images': bool(re.search(r'!\[.*?\]\(.*?\)', text))
    }
    
    return metadata