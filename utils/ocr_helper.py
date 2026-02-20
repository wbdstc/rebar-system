"""
OCR 处理工具模块
用于识别平法标注、解析配筋信息
"""

import re
from typing import List, Dict, Optional, Tuple
from PIL import Image
import io

# pytesseract 导入（需要系统安装 Tesseract）
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    TESSERACT_AVAILABLE = False
    print(f"[警告] pytesseract 不可用: {e}")


def extract_text(image_data: bytes, lang: str = "chi_sim+eng") -> str:
    """
    从图片中提取文字
    
    Args:
        image_data: 图片二进制数据
        lang: OCR 语言，默认中文简体+英文
        
    Returns:
        识别到的文字
    """
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract 未安装或 Tesseract 未配置")
    
    # 从二进制数据创建 PIL Image
    image = Image.open(io.BytesIO(image_data))
    
    # 转换为灰度图以提高识别率
    if image.mode != 'L':
        image = image.convert('L')
    
    # 执行 OCR
    text = pytesseract.image_to_string(image, lang=lang)
    
    return text.strip()


def parse_pingfa(text: str) -> List[Dict[str, int]]:
    """
    解析平法格式配筋标注
    
    支持格式：
    - nCd: 如 4C22, 8C20, 12C25
    - nφd 或 nΦd: 如 4φ22, 8Φ20
    - 复合格式: "4C25 8C22" 或 "4C25+8C22"
    
    Args:
        text: 待解析的文字
        
    Returns:
        解析结果列表 [{"count": 4, "diameter": 22}, ...]
    """
    results = []
    
    # 正则匹配所有 nCd 或 nφd 格式
    pattern = r'(\d+)\s*[CΦφ]\s*(\d+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    for match in matches:
        count = int(match[0])
        diameter = int(match[1])
        
        # 合理性校验
        if 1 <= count <= 50 and 6 <= diameter <= 50:
            results.append({
                "count": count,
                "diameter": diameter
            })
    
    return results


def parse_column_id(text: str) -> Optional[str]:
    """
    从文字中提取柱号
    
    支持格式：KZ1, KZ2, GZ1, Z1 等
    
    Args:
        text: 待解析的文字
        
    Returns:
        柱号字符串，未找到则返回 None
    """
    pattern = r'[KGZ]+Z?\d+'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def parse_section_size(text: str) -> Optional[Tuple[int, int]]:
    """
    从文字中提取截面尺寸
    
    支持格式：650x600, 650*600, 650×600 等
    
    Args:
        text: 待解析的文字
        
    Returns:
        (宽, 高) 元组，未找到则返回 None
    """
    pattern = r'(\d{3,4})\s*[x×\*]\s*(\d{3,4})'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def get_design_total(rebar_config: List[Dict[str, int]]) -> int:
    """
    计算配筋的总根数
    
    Args:
        rebar_config: 配筋配置列表
        
    Returns:
        总根数
    """
    return sum(item["count"] for item in rebar_config)


def process_ocr_image(image_data: bytes) -> Dict:
    """
    完整处理 OCR 图片：识别 + 解析
    
    Args:
        image_data: 图片二进制数据
        
    Returns:
        包含所有解析结果的字典
    """
    result = {
        "raw_text": "",
        "column_id": None,
        "section_size": None,
        "rebar_config": [],
        "design_total": 0,
        "success": False,
        "error": None
    }
    
    try:
        # 提取文字
        raw_text = extract_text(image_data)
        result["raw_text"] = raw_text
        
        # 解析柱号
        result["column_id"] = parse_column_id(raw_text)
        
        # 解析截面尺寸
        result["section_size"] = parse_section_size(raw_text)
        
        # 解析配筋
        result["rebar_config"] = parse_pingfa(raw_text)
        result["design_total"] = get_design_total(result["rebar_config"])
        
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def check_compliance(detected_count: int, design_total: int) -> Dict:
    """
    检查合规性：比较检测数量与设计数量
    
    Args:
        detected_count: AI 检测到的数量
        design_total: 设计规定的数量
        
    Returns:
        合规性检查结果
    """
    if design_total == 0:
        return {
            "status": "UNKNOWN",
            "message": "未提供设计数量，无法判定"
        }
    
    diff = detected_count - design_total
    
    if diff == 0:
        return {
            "status": "PASS",
            "message": f"✅ 合规：检测数量({detected_count})与设计数量({design_total})一致"
        }
    elif diff > 0:
        return {
            "status": "WARNING",
            "message": f"⚠️ 警告：检测数量({detected_count})超出设计数量({design_total})，多出 {diff} 根"
        }
    else:
        return {
            "status": "FAIL",
            "message": f"❌ 不合规：检测数量({detected_count})少于设计数量({design_total})，缺少 {abs(diff)} 根"
        }
