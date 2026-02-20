"""
VLM (Vision Language Model) 大模型调用服务
用于解析 CAD 图纸截图，自动提取平法参数

支持构件类型：柱(column)、梁(beam)、板/墙(slab/wall)
内置 16G101 平法专家知识库，提升复杂标注解析准确率
使用智谱 AI GLM-4V 多模态大模型
"""

import base64
import json
import os
import re
from typing import Optional

# 智谱 AI SDK（可选依赖）
try:
    from zhipuai import ZhipuAI
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False
    print("[警告] zhipuai 未安装，CAD 图纸解析功能不可用。请运行: pip install zhipuai")

# 智谱 AI API Key
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '53fd371c732b403cb6ac7e009a6946a7.nCrwtHF2LJBa26cS')


# =============================================
# 16G101 平法专家知识库（System Prompt）
# =============================================

EXPERT_KNOWLEDGE = """【专家识图规则库（16G101平法）】
1. 箍筋规则：如"φ10@100/200(4)"表示箍筋为φ10，加密区间距100，非加密区间距200，全为四肢箍。如有括号如(2)或(4)代表箍筋肢数。
2. 梁上下主筋：如"3Φ22，3Φ20"表示上部钢筋3根，下部钢筋3根。
3. 多排钢筋计算：如"6Φ25 4/2"表示上排4根，下排2根，总计6根；"2Φ22+(4Φ12)"表示总计6根；"2Φ25+3Φ22(-3)/5Φ25"中上排为5根，下排为5根。
4. 梁腰筋：以G打头为构造筋(如G2φ12)，以N打头为抗扭筋(如N4Φ18)。
"""


# =============================================
# 动态 Prompt 构建
# =============================================

def _build_prompt(component_type: str) -> str:
    """根据构件类型构建对应的大模型 Prompt（含专家知识库）"""

    if component_type == 'beam':
        return (
            EXPERT_KNOWLEDGE + "\n"
            "你是一个土木工程师。请读取这张CAD梁配筋图（平法标注），"
            "利用上述【多排钢筋计算规则】和【箍筋规则】，"
            "提取并计算出：上部纵筋总根数、下部纵筋总根数、"
            "箍筋加密区间距(mm)、非加密区间距(mm)、箍筋肢数。"
            "请严格以 JSON 格式返回，不要包含其他任何文字：\n"
            '{"top_bars_total": 6, "bottom_bars_total": 5, '
            '"stirrup_dense": 100, "stirrup_normal": 200, "stirrup_legs": 4}'
        )
    elif component_type in ('slab', 'wall'):
        return (
            EXPERT_KNOWLEDGE + "\n"
            "你是一个土木工程师。请读取这张CAD板/墙配筋图（平法标注），"
            "提取出钢筋网格的设计间距(mm)。"
            "请严格以 JSON 格式返回，不要包含其他任何文字：\n"
            '{"design_spacing": 150}'
        )
    else:  # column（默认）
        return (
            EXPERT_KNOWLEDGE + "\n"
            "你是一个土木工程师。请读取这张CAD柱截面配筋图，"
            "利用上述【箍筋规则】和【多排钢筋计算规则】，"
            "提取出角筋数量、中部筋数量（注意结合图形推理总根数），"
            "以及箍筋加密区间距(mm)和非加密区间距(mm)。"
            "请严格以 JSON 格式返回，不要包含其他任何文字：\n"
            '{"corner_bars": 4, "middle_bars": 8, "total_bars": 12, '
            '"stirrup_dense": 100, "stirrup_normal": 200}'
        )


# =============================================
# 核心解析函数
# =============================================

def parse_cad_image(image_data: bytes, component_type: str = 'column') -> dict:
    """
    解析 CAD 截图，根据构件类型提取平法参数

    Args:
        image_data: CAD 截图的二进制数据
        component_type: 构件类型 (column / beam / slab / wall)

    Returns:
        dict: 包含解析结果，字段随 component_type 变化
    """
    if not ZHIPU_AVAILABLE:
        return {
            "success": False,
            "error": "zhipuai SDK 未安装，请运行: pip install zhipuai"
        }

    if not ZHIPU_API_KEY:
        return {
            "success": False,
            "error": "未配置 ZHIPU_API_KEY 环境变量，请设置智谱 AI API Key"
        }

    try:
        img_base64 = base64.b64encode(image_data).decode('utf-8')
        prompt = _build_prompt(component_type)

        client = ZhipuAI(api_key=ZHIPU_API_KEY)
        response = client.chat.completions.create(
            model="glm-4v-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=512
        )

        raw_text = response.choices[0].message.content.strip()
        print(f"[VLM] 构件={component_type}, 原始返回: {raw_text}")

        parsed = _extract_json(raw_text)
        if not parsed:
            return {
                "success": False,
                "error": "大模型返回格式异常，无法提取 JSON",
                "raw_response": raw_text
            }

        # 统一返回格式
        result = {
            "success": True,
            "component_type": component_type,
            "raw_response": raw_text
        }
        result.update(parsed)
        return result

    except Exception as e:
        print(f"[VLM] 调用失败: {str(e)}")
        return {
            "success": False,
            "error": f"大模型调用失败: {str(e)}"
        }


# =============================================
# 原材微观核验（钢筋轧印识别）
# =============================================

MATERIAL_VERIFY_PROMPT = (
    "你是一个钢筋质检员。请读取图中钢筋表面的凸起轧印（如4E22）。\n"
    "轧印识别规则：\n"
    "- 首位数字代表牌号：4代表HRB400，5代表HRB500，3代表HRB335\n"
    "- 字母E代表抗震钢筋（满足抗震要求）\n"
    "- 最后的数字代表公称直径(mm)\n"
    "- 示例：4E22 = HRB400抗震钢筋，直径22mm\n"
    "- 示例：5E25 = HRB500抗震钢筋，直径25mm\n"
    "- 示例：422 = HRB400非抗震钢筋，直径22mm\n\n"
    "请严格以 JSON 格式返回，不要包含其他任何文字：\n"
    '{"material_grade": "HRB400", "is_seismic": true, "diameter": 22, "raw_text": "4E22"}'
)


def verify_material(image_data: bytes) -> dict:
    """
    识别钢筋表面轧印，提取牌号、抗震性、直径信息

    Args:
        image_data: 钢筋特写照片的二进制数据

    Returns:
        dict: {"success": True, "material_grade": "HRB400", "is_seismic": True, "diameter": 22, "raw_text": "4E22"}
    """
    if not ZHIPU_AVAILABLE:
        return {"success": False, "error": "zhipuai SDK 未安装，请运行: pip install zhipuai"}

    if not ZHIPU_API_KEY:
        return {"success": False, "error": "未配置 ZHIPU_API_KEY"}

    try:
        img_base64 = base64.b64encode(image_data).decode('utf-8')

        client = ZhipuAI(api_key=ZHIPU_API_KEY)
        response = client.chat.completions.create(
            model="glm-4v-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": MATERIAL_VERIFY_PROMPT
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=256
        )

        raw_text = response.choices[0].message.content.strip()
        print(f"[VLM-Material] 原始返回: {raw_text}")

        parsed = _extract_json(raw_text)
        if not parsed:
            return {
                "success": False,
                "error": "大模型返回格式异常，无法提取 JSON",
                "raw_response": raw_text
            }

        return {
            "success": True,
            "material_grade": parsed.get("material_grade", ""),
            "is_seismic": parsed.get("is_seismic", False),
            "diameter": parsed.get("diameter", 0),
            "raw_text": parsed.get("raw_text", ""),
            "raw_response": raw_text
        }

    except Exception as e:
        print(f"[VLM-Material] 调用失败: {str(e)}")
        return {"success": False, "error": f"大模型调用失败: {str(e)}"}


# =============================================
# JSON 提取工具
# =============================================

def _extract_json(text: str) -> Optional[dict]:
    """从大模型返回的文本中提取 JSON 对象"""
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # markdown 代码块
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 花括号匹配
    brace_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None
