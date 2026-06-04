"""
Interview question generator — creates customized questions based on
the candidate's resume and Yousky's company context.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_company_context() -> str:
    """Load the full company context for prompt use."""
    # Load JSON profile
    profile_path = BASE_DIR / "data" / "company_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    # Load markdown context
    md_path = BASE_DIR / "data" / "company_context.md"
    md_text = md_path.read_text(encoding="utf-8")

    return md_text


def build_question_prompt(resume_text: str, role: str, team: str) -> str:
    """Build the prompt for interview question generation."""
    company_context = load_company_context()

    return f"""你是一位资深的跨境电商/品牌出海领域的面试官。请根据以下信息，为候选人定制一套面试题。

## 公司背景
{company_context}

## 候选人简历
{resume_text[:5000]}

## 岗位信息
- 应聘岗位：{role}
- 所属团队：{team}

## 出题要求

请从两个维度设计面试题，每个维度至少4道题，总共10-15道题。题目必须紧密围绕候选人的简历经历和Yousky的实际业务场景。

### 维度一：能不能做（Can Do）— 能力与性格匹配

**业务硬技能（至少3题）**：
- 针对简历中的具体经验，设计与{role}相关的实操题
- 结合Yousky的实际业务场景（TikTok/Amazon/DTC/清洁家电品类）
- 包含具体的方法论考察和案例分析

**软实力（至少1题）**：
- 跨文化沟通能力（跨境电商必备）
- 数据思维与分析能力
- 创业团队适应性（小团队多角色）
- 自驱力与学习能力

### 维度二：愿不愿做（Will Do）— 兴趣与价值观匹配（至少3题）

**职业兴趣**：
- 对跨境电商/品牌出海/TikToK内容营销的真实热情
- 是否关注海外市场动态和消费者趋势

**价值取向**：
- 是否适应创业公司的快速节奏和不确定性
- 是否认同数据驱动、结果导向的文化
- 对扁平化管理和身兼多职的态度

**长期规划**：
- 个人职业目标与公司发展方向的契合度

## 输出格式

请按以下格式输出：

```
## 面试题 — {role}候选人

### 一、能不能做（Can Do）

#### 业务硬技能
**Q1.** [题目]
考察点：[简述]

**Q2.** [题目]
考察点：[简述]

...

#### 软实力
**Qn.** [题目]
考察点：[简述]

### 二、愿不愿做（Will Do）

#### 职业兴趣与价值观
**Qn.** [题目]
考察点：[简述]

...

### 三、综合情景题
**Qn.** [基于Yousky实际业务场景的综合题]
考察点：[简述]
```
"""
