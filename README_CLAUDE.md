# 🤖 Claude Code 프로젝트 가이드

이 프로젝트(`LawProject`)에서 **Claude Code**를 활용하여 개발 효율을 극대화하는 방법을 안내합니다.

## 1. 시작하기 (Setup)

터미널에서 아래 명령어를 입력하여 Claude Code를 실행할 수 있습니다.

```bash
claude
```

처음 실행 시 Anthropic 계정 로그인이 필요할 수 있습니다. 화면의 지시에 따라 인증을 완료해 주세요.

## 2. 주요 기능 및 활용 시나리오

Anthropic의 Claude Code는 단순히 코드 작성을 돕는 것을 넘어, 프로젝트 전체를 이해하고 복잡한 작업을 자율적으로 수행하는 **Agentic CLI**입니다.

### 🔍 프로젝트 구조 파악 및 질문
프로젝트에 처음 합류한 동료처럼 질문할 수 있습니다.
- `claude "이 프로젝트의 법률 상담 로직은 어디에 구현되어 있어?"`
- `claude "data 디렉토리 내의 user_simulator.py가 하는 역할이 뭐야?"`

### 🛠️ 코드 수정 및 리팩토링
파일 하나하나 열지 않고 터미널에서 바로 지시하세요.
- `claude "llm/prompts.py에 예외 처리 로직을 추가해줘"`
- `claude "app/state.py의 변수명을 더 명확하게 리팩토링해줘"`

### 📝 문서 자동 생성
- `claude "현재 구현된 RAG 전략을 바탕으로 설계 문서를 업데이트해줘"`

### 🛂 Git 워크플로우 자동화
Claude가 작업 내용을 요약하고 커밋 메시지도 작성해줍니다.
- `claude "작업 내용을 반영해서 'fix/prompt-logic' 브랜치에 커밋하고 푸시해줘"`

## 3. Antigravity(현재 AI)와의 차이점

| 특징 | Antigravity (VS Code Extension) | Claude Code (CLI Agent) |
| :--- | :--- | :--- |
| **인터페이스** | VS Code 내 통합 UI | 터미널 (Command Line) |
| **실행 환경** | 에디터 중심 | 터미널 및 인프라 제어 중심 |
| **강점** | 파일 편집 및 UI 기반 가이드 | 대규모 작업 자동화, Git 제어, 테스트 실행 |

> [!TIP]
> 두 도구는 상호 보완적입니다. VS Code에서는 Antigravity와 함께 코딩하고, 대규모 리팩토링이나 터미널 작업이 필요할 때는 Claude Code를 병행해 보세요!

## 4. 문제 해결 (Troubleshooting)

만약 `claude` 명령어가 인식되지 않는다면:
1. 터미널(PowerShell/CMD)을 껐다 켜보세요.
2. `npm install -g @anthropic-ai/claude-code` 명령어를 다시 실행해 보세요.
