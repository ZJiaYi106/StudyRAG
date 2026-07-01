"""
OCR 图片文字提取
从 PDF 中提取内嵌图片，使用 OCR 识别其中的文字。
支持 pytesseract（本地）和 VLM API（远程）。

使用场景：
- 扫描版 PDF（整页图片）
- 含图表的文档（提取图表中的文字标注）
- PPT 导出的 PDF（文字以图片形式存在）

技术栈：
- PDF 图片提取：PyMuPDF (fitz)
- OCR 文字识别：pytesseract + Tesseract OCR 引擎
- VLM 图片理解：DeepSeek Vision / OpenAI Vision API
"""

import logging
from typing import List, Optional
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


def extract_images_from_pdf(file_path: str, page_num: int) -> List[bytes]:
    """
    从 PDF 指定页提取所有图片。

    Args:
        file_path: PDF 文件路径
        page_num: 页码（0-indexed）

    Returns:
        图片字节列表（PNG 格式）
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page = doc[page_num]
        images = page.get_images(full=True)

        result = []
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            result.append(base_image["image"])

        doc.close()
        return result
    except Exception as e:
        logger.warning(f"[OCR] 图片提取失败 (第{page_num+1}页): {e}")
        return []


def ocr_page(file_path: str, page_num: int, lang: str = "chi_sim+eng") -> str:
    """
    对 PDF 指定页做整页 OCR。

    先用 PyMuPDF 将页面渲染为图片，再用 Tesseract 识别。

    Args:
        file_path: PDF 文件路径
        page_num: 页码（0-indexed）
        lang: OCR 语言（默认中文+英文）

    Returns:
        识别出的文本
    """
    try:
        import fitz
        import pytesseract
        from PIL import Image
        import io

        doc = fitz.open(file_path)
        page = doc[page_num]
        # 渲染页面为图片（300 DPI 适合 OCR）
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        text = pytesseract.image_to_string(img, lang=lang)
        doc.close()

        if text.strip():
            logger.info(f"[OCR] 第{page_num+1}页识别到 {len(text)} 字符")
        return text.strip()
    except ImportError as e:
        logger.warning(f"[OCR] 依赖缺失: {e}。需要 pytesseract 和 Tesseract OCR 引擎。")
        return ""
    except Exception as e:
        logger.warning(f"[OCR] 第{page_num+1}页识别失败: {e}")
        return ""


def describe_image_vlm(image_bytes: bytes, prompt: Optional[str] = None) -> str:
    """
    使用 VLM（视觉语言模型）描述图片内容。

    Args:
        image_bytes: 图片字节（PNG/JPEG）
        prompt: 自定义描述提示（默认：描述图中与文档内容相关的信息）

    Returns:
        图片的文本描述
    """
    if prompt is None:
        prompt = "请描述这张图片中与文档内容相关的信息，包括图表类型、关键数据和标注文字。"

    try:
        import base64
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        # VLM 必须是支持图片输入的模型（如 glm-4v-flash），
        # 不能复用 llm_model（deepseek-chat 等纯文本模型会报错）
        # vlm_api_key 未配置时回退到 embedding_api_key（同平台可复用）
        # 注意：SecretStr 掩码恒为真值，必须用 get_secret_value() 判空
        vlm_key = settings.vlm_api_key.get_secret_value()
        api_key = vlm_key if vlm_key else settings.embedding_api_key.get_secret_value()
        llm = ChatOpenAI(
            model=settings.vlm_model,
            openai_api_key=api_key,
            openai_api_base=settings.vlm_api_base,
            temperature=0.1,
            max_tokens=500,
        )

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ])

        response = llm.invoke([message])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"[VLM] 图片描述失败: {e}")
        return ""
