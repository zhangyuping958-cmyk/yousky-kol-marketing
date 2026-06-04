"""
Answer evaluator — scores candidate answers against interview questions
and provides a pass/fail recommendation.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def build_evaluation_prompt(
    questions: str,
    answers: str,
    role: str,
    team: str,
    resume_summary: str,
) -> str:
    """Build the prompt for evaluating candidate answers."""
    company_context = (BASE_DIR / "data" / "company_context.md").read_text(encoding="utf-8")

    return f"""你是一位资深面试官，请根据以下信息对候选人的面试表现进行评分和评估。

## 公司背景
{company_context}

## 岗位信息
- 应聘岗位：{role}
- 所属团队：{team}

## 候选人简历摘要
{resume_summary[:1500]}

## 面试题目
{questions}

## 候选人口述回答（语音转文字）
{answers}

## 评分要求

对每道题的答案进行评分（1-5分）：
- 5分：回答优秀，超出预期，展现深度思考和丰富经验
- 4分：回答良好，准确切题，展现相关能力
- 3分：回答合格，基本达标，但缺乏亮点
- 2分：回答不足，理解偏差，经验欠缺
- 1分：回答很差，无法胜任

对每个答案给出简短点评（1-2句话）。

## 输出格式

```
## 面试评分卡

### 各题评分

| 题号 | 题目简述 | 得分 | 点评 |
|------|---------|------|------|
| Q1   | ...     | 4/5  | ...  |
| Q2   | ...     | 3/5  | ...  |
...

### 维度汇总

| 维度 | 平均分 | 评价 |
|------|--------|------|
| 业务硬技能 | X.X/5 | ... |
| 软实力     | X.X/5 | ... |
| 职业兴趣与价值观 | X.X/5 | ... |

### 综合评估

**总体均分**：X.X/5

**优势**：
- ...

**风险/不足**：
- ...

**匹配度分析**：
- 能不能做：[评价]
- 愿不愿做：[评价]

### 最终建议

**结果**：[通过 / 待定 / 不通过]

**理由**：[2-3句话说明决策依据]

**入职后关注点**（如通过）：[需要在哪些方面重点关注和培养]
```
"""
