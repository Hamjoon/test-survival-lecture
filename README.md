# LLM 생성 테스트는 코드 변화를 얼마나 버티는가

LLM으로 생성한 단위 테스트와 개발자가 작성한 테스트(Dev)를 같은 시점 t에서 준비하고, 이후 commit에서 테스트 소스를 고치지 않고 실행해 비교하는 강의용 Jupyter notebook입니다. 진행 중인 실험의 일부를 줄여서 직접 실행해 볼 수 있게 만들었습니다.

- 대상 프로젝트: [json-schema-validator](https://github.com/networknt/json-schema-validator) (Java), t = release 1.1.0
- 대상 클래스: `ValidationMessage`, `SpecVersionDetector`
- 생성 방식: Ouédraogo et al.(EMSE 2026)의 프롬프트 5종, KTester(Li et al., ICSE 2026)
- 비교 시점: commit #4, #10, #151

## 여는 방법

[Colab에서 열기](https://colab.research.google.com/github/Hamjoon/test-survival-lecture/blob/main/lecture.ipynb)

준비물은 Google 계정과 Gemini API 키입니다. 키는 [Google AI Studio](https://aistudio.google.com/apikey)에서 무료로 발급하고, Colab 왼쪽의 Secrets(열쇠 모양)에 `GEMINI_API_KEY`라는 이름으로 넣습니다. 결제를 켜지 않으면 요금은 나가지 않습니다. 한도는 키가 아니라 Google Cloud 프로젝트 단위로 걸립니다.

## 구성과 소요 시간

| 단계 | 내용 | 모델 호출 | 시간 |
|---|---|---|---|
| 1 | 환경 준비 (JDK 17, Maven, 테스트 실행 도구) | 1회 (키 확인) | 1~2분 |
| 2 | 대상 프로젝트 빌드, Dev 테스트 확인 | 없음 | 1~2분 |
| 3 | Ouédraogo 방식 생성과 t에서 확인 | 10회 | 2~3분 |
| 4 | KTester 방식 생성과 t에서 확인, 세 집단 coverage 비교 | 100~200회 | 30~50분 |
| 5 | commit 세 개에서 실행 (생존, 변경 줄 coverage) | 없음 | 2~5분 |
| 6 | 정리 | 없음 | |

3-1과 4-1에서 `USE_SAVED = True`로 바꾸면 모델을 부르지 않고 저장된 생성 결과(`data/generated/`)를 씁니다.

## 폴더

| 경로 | 내용 |
|---|---|
| `lecture.ipynb` | 강의 노트북 |
| `tools/lecture.py` | 빌드, 테스트 실행, coverage, 생존 측정 함수 |
| `tools/ktester.py` | KTester 다섯 단계 |
| `tools/MethodRunner.java` | 테스트 메서드를 이름으로 골라 실행 |
| `data/json-schema-validator/dev-scope.json` | 미리 고른 Dev 테스트 목록 (Dev(scope)) |
| `data/ktester/` | KTester 입력(미리 뽑은 프로젝트 지식) |
| `data/prompts/` | 두 방식의 프롬프트 템플릿 |
| `data/generated/` | 저장된 생성 결과 |
| `docs/` | 프롬프트 전문, KTester 단계 설명과 실제 프롬프트 예시 |
| `prep/` | 미리 만든 데이터를 만든 스크립트 |

## 참고 문헌

- Ouédraogo et al. Prompt Engineering in LLMs for Automated Unit Test Generation: A Large-Scale Study. Empirical Software Engineering 31:103, 2026. https://doi.org/10.1007/s10664-026-10840-4
- Li et al. Knowledge Matters: Injecting Project and Testing Knowledge into LLM-based Unit Test Generation. ICSE 2026. https://doi.org/10.1145/3744916.3787769, 공개 저장소 https://github.com/SYSUSELab/KTester
