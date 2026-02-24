"""
VLM (Vision Language Model) 大模型调用服务
用于解析 CAD 图纸截图，自动提取平法参数

支持构件类型：柱(column)、梁(beam)、板(slab)、墙(wall)
内置 16G101 平法专家知识库，提升复杂标注解析准确率
输出模式：思维链(CoT)推理报告 + JSON 结构化数据双轨制
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
ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '22efb9769fdc45e38d14e3af6f2cdaa0.Rja37r4VRnqu40rZ')

# 模型选择（便于未来切换）
GLM_MODEL = os.environ.get('GLM_MODEL', 'glm-4v-flash')


# =============================================
# 动态 Prompt 构建（保持短小 + 精准改进）
# =============================================

def _build_prompt(component_type: str) -> str:
    """
    构建 prompt。

    设计原则（glm-4v 兼容性约束）：
    - 总长度控制在 400 字以内（过长会触发 <|observation|> 控制符）
    - 不使用 system 消息（glm-4v 对 system role 支持不稳定）
    - 保持"两步"结构（已验证可用的格式）
    - 在有限篇幅内嵌入反幻觉约束和关键平法速查
    """

    if component_type == 'beam':
        component_label = "梁"
        analysis_task = (
            "1)上部纵筋的规格和根数（若有分排如2/4需相加）"
            " 2)下部纵筋的规格和根数"
            " 3)是否有腰筋（G或N开头），有则写根数，无则写0"
            " 4)箍筋的直径、加密区间距和非加密区间距、肢数。"
        )
        example = "例：上部筋2C25→top_bars_total=2，Φ8@100/200(2)→stirrup_dense=100,stirrup_normal=200,stirrup_legs=2"
        json_block = '{"top_bars_total": 0, "bottom_bars_total": 0, "waist_bars": 0, "stirrup_dense": 0, "stirrup_normal": 0, "stirrup_legs": 0}'

    elif component_type == 'slab':
        component_label = "楼板"
        analysis_task = "1)受力钢筋的规格 2)间距标注数值（@后面的数字）。"
        example = "例：C10@150→design_spacing=150"
        json_block = '{"design_spacing": 0}'

    elif component_type == 'wall':
        component_label = "剪力墙"
        analysis_task = "1)水平分布筋规格和间距 2)竖向分布筋规格和间距。若只标一个间距则水平竖向相同。"
        example = "例：Φ10@200→design_spacing=200"
        json_block = '{"design_spacing": 0}'

    else:  # column
        component_label = "柱"
        analysis_task = (
            "1)截面尺寸（若分段标注如200+200需相加）。"
            "2)角筋的规格和根数。请独立、仔细辨认角筋标注文字，绝不可与中部筋的规格混淆！"
            "3)中部筋的规格和根数。"
            "4)纵筋总数（仅需将角筋与中部筋的【根数】相加，不要合并规格）。"
            "5)箍筋的直径、加密区与非加密区间距（如A8@100/200则加密=100，非加密=200）。"
        )
        example = "例：角筋4C25，中部筋8C20，总数12根→corner_bars=4,middle_bars=8,total_bars=12"
        json_block = '{"corner_bars": 0, "middle_bars": 0, "total_bars": 0, "stirrup_dense": 0, "stirrup_normal": 0}'

    prompt = f"""这是一张【{component_label}】的CAD截面配筋图。请仔细看图，完成以下两步。

第一步 - 分析报告：
逐项读取图中的标注信息，写出你的判断依据。只提取图中可见标注，看不到的填0，不要猜测。
{analysis_task}
{example}

第二步 - 填写JSON：
根据你在第一步中分析出的数字填入JSON。你在报告里写了什么数字，JSON里就必须填同样的数字！数值为纯整数不带单位。
```json
{json_block}
```"""

    return prompt


# =============================================
# 核心解析函数（双轨制返回：report + extracted_data）
# =============================================

def parse_cad_image(image_data: bytes, component_type: str = 'column') -> dict:
    """
    解析 CAD 截图，根据构件类型提取平法参数。

    返回双轨结构：
    - report: Markdown 格式的 AI 审图推理报告
    - extracted_data: 从 JSON 代码块提取的结构化数据字典

    Args:
        image_data: CAD 截图的二进制数据
        component_type: 构件类型 (column / beam / slab / wall)

    Returns:
        dict: {"success": True, "report": str, "extracted_data": dict, ...}
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
            model=GLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            # 修改后
                            "image_url": {
                                "url": img_base64
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
            max_tokens=1024,
        )

        raw_response = response.choices[0].message.content.strip()

        # ===== 白盒调试日志：打印完整原始回复 =====
        print("=" * 60)
        print(f"[VLM·白盒调试] 构件={component_type}")
        print(f"[VLM·白盒调试] 原始回复 raw_response:")
        print(raw_response)
        print("=" * 60)

        # ===== 究极鲁棒 JSON 提取 =====
        extracted_data = {}
        analysis_report = raw_response
        json_str = ""

        # 尝试 1: 标准 Markdown ```json``` 格式提取
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            # 从原文中移除整个 JSON 代码块，剩余的就是报告
            analysis_report = (raw_response[:json_match.start()] + raw_response[json_match.end():]).strip()
            print("[VLM] 标准 ```json``` 格式匹配成功")
        else:
            # 尝试 2: 暴力兜底提取（找到第一个 { 和最后一个 }）
            print("[VLM] 未找到标准 ```json``` 格式，启动暴力正则搜索...")
            fallback_match = re.search(r'\{[\s\S]*\}', raw_response)
            if fallback_match:
                json_str = fallback_match.group(0).strip()
                # 从原文中移除 JSON 部分，剩余的就是报告
                analysis_report = (raw_response[:fallback_match.start()] + raw_response[fallback_match.end():]).strip()
                print(f"[VLM] 暴力提取到候选 JSON 片段（长度={len(json_str)}）")
            else:
                print("[VLM] 警告: 彻底未能找到任何类似 JSON 的结构！")

        # 清理报告中可能残留的格式标记
        analysis_report = re.sub(r'</?output_format>', '', analysis_report)
        analysis_report = re.sub(r'```\w*\s*```', '', analysis_report)
        analysis_report = analysis_report.strip()

        # 解析 JSON
        try:
            if json_str:
                # 清理可能存在的不可见字符、控制字符、BOM
                json_str = json_str.strip().replace('\ufeff', '')
                # 移除 JSON 中的单行注释（// ...）
                json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)
                extracted_data = json.loads(json_str)
                print(f"[VLM] 成功提取 JSON: {extracted_data}")
        except json.JSONDecodeError as e:
            print(f"[VLM] JSON 解析失败! 提取到的字符串为: {json_str}")
            print(f"[VLM] 错误原因: {e}")
            # 不中断程序，返回空字典，让前端能够继续显示报告

        # ===== 构建双轨返回 =====
        # 兜底：如果报告为空（模型只输出了 JSON），自动生成摘要
        if not analysis_report and extracted_data:
            summary_lines = ["**AI 自动提取结果（模型未生成分析报告）：**", ""]
            for k, v in extracted_data.items():
                summary_lines.append(f"- **{k}**: {v}")
            analysis_report = "\n".join(summary_lines)
            print("[VLM] 报告为空，已从 JSON 数据自动生成摘要")
        elif not analysis_report:
            analysis_report = "模型未生成分析报告，请查看下方参数是否已自动填充。"

        result = {
            "success": True,
            "component_type": component_type,
            "report": analysis_report,
            "extracted_data": extracted_data,
            "raw_response": raw_response
        }

        # 兼容旧前端：将 extracted_data 的字段也平铺到顶层
        result.update(extracted_data)

        return result

    except Exception as e:
        print(f"[VLM] 调用失败: {str(e)}")
        return {
            "success": False,
            "error": f"大模型调用失败: {str(e)}",
            "report": "",
            "extracted_data": {}
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
            model=GLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            # 修改后
                            "image_url": {
                                "url": img_base64
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
# JSON 提取工具（兜底用）
# =============================================

def _extract_json(text: str) -> Optional[dict]:
    """从大模型返回的文本中提取 JSON 对象（兜底方案）"""
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
