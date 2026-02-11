from app.llm_factory import LLMFactory
from langchain.schema import HumanMessage, SystemMessage

USER_SIMULATOR_PROMPT = """너는 지금부터 [산업재해] 또는 [부당해고]를 겪은 40대 근로자 역할을 연기해야 한다.
절대 AI처럼 말하지 말고, 감정이 섞인 자연스러운 한국어로 대화하라.

[설정]
- 직업: 건설 일용직 또는 식당 주방 보조
- 상황: {scenario}
- 성격: 억울함을 호소하지만 법률 용어는 잘 모름.
- 목표: 상담원(AI)의 질문에 맞춰 상황을 조금씩 구체적으로 설명하되, 가끔은 동문서답도 하라.

[현재 대화 흐름]
상담원: {last_question}
"""

class UserSimulator:
    def __init__(self, scenario: str):
        self.scenario = scenario
        # User simulator uses fast model for testing efficiency
        self.llm = LLMFactory.create_llm("openai", model_name="gpt-4o-mini")
        self.history = []

    def generate_response(self, last_ai_message: str) -> str:
        prompt = USER_SIMULATOR_PROMPT.format(
            scenario=self.scenario,
            last_question=last_ai_message
        )
        
        # Add history to keep context (simplified)
        messages = [SystemMessage(content=prompt)]
        
        response = self.llm.invoke(messages)
        return response.content
