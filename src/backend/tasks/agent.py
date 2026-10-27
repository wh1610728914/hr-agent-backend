from backend.agents.candidate import CandidateProcessAgent
from backend.schemas.candidate import CandidateSchema
from backend.schemas.position import PositionSchema
from backend.schemas.user import UserSchema
from langchain.messages import HumanMessage


async def run_agent_test(
    candidate: CandidateSchema, position: PositionSchema, interview: UserSchema
):
    """"""
    async with CandidateProcessAgent(
        candidateInfo=candidate, positionInfo=position, interviewInfo=interview
    ) as agent:
        res = await agent.ainvoke(
            messages=[HumanMessage(content=f"""请评估以下候选人是否匹配该职位：

【职位信息】
- 岗位名称: {position.title}
- 职位描述: {position.description or '无'}
- 岗位要求: {position.requirements or '无'}
- 经验要求: {position.work_year} 年及以上
- 学历要求: {position.education.value}
- 薪资范围: {position.min_salary or '面议'} - {position.max_salary or '面议'}

【候选人信息】
- 姓名: {candidate.name}
- 性别: {candidate.gender.value}
- 出生日期: {candidate.birthday or '未提供'}
- 教育经历: {candidate.education_experience or '无'}
- 工作经历: {candidate.work_experience or '无'}
- 项目经验: {candidate.project_experience or '无'}
- 掌握技能: {candidate.skills or '无'}
- 自我评价: {candidate.self_evaluation or '无'}
- 其他信息: {candidate.other_information or '无'}
""")],
            thread_id=candidate.email,
        )
        print(res)
        return res
