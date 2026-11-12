# KTester 단계와 노트북 구현

KTester(Li et al., ICSE 2026, "Knowledge Matters: Injecting Project and Testing Knowledge into LLM-based Unit Test Generation")는 focal method(테스트할 메서드) 하나마다 테스트 클래스 하나를 만듭니다. 노트북의 `tools/ktester.py`는 논문 공개 저장소(https://github.com/SYSUSELab/KTester, commit `fce83f1`)의 흐름을 그대로 따릅니다.

## 두 가지 지식

- **프로젝트 지식**: 프로젝트 전체를 정적 분석해 만든 인덱스에서 꺼냅니다. 생성자, 매개변수 타입, focal method를 실제로 호출하는 코드 예시, 의존 클래스, 비슷한 메서드(Lucene 검색) 등입니다.
- **테스트 지식**: 세 관점(condition branch-driven, functionality-driven, exception-oriented)으로 테스트 케이스를 설계하게 합니다.

## 다섯 단계

| 단계 | 하는 일 | 모델 호출 | 템플릿 |
|---|---|---|---|
| 1. test class framework generation | 필드, setup·teardown이 있는 빈 테스트 클래스 | 1회 | `init_structure.j2` |
| 2. test case design | 세 관점에서 테스트 케이스를 JSON으로 설계, 앞 관점과 겹치는 케이스는 뺌 | 3회 | `condition4case_cov.j2`, `io4case_guide.j2`, `exception4case_check.j2` |
| 3. test method transformation | 케이스를 JUnit 5 테스트 메서드로 | 1회 | `gencode_from_case.j2` |
| 4. test class integration | 1단계 클래스에 3단계 메서드를 합침 | 없음 | jar의 `TestClassUpdator` |
| 5. test class refinement | 컴파일·실행 → 규칙 수리 → LLM 수리, 최대 5회. 가장 통과율이 높은 버전 채택 | 최대 5회 | `post_process.j2` |

5단계 규칙 수리: 빠진 import 추가(인덱스의 import 목록), 잘못된 import 삭제, 예외 선언 추가, 중복 내부 클래스 정리(jar의 `TestClassSterilizer`), 시간 초과 테스트 삭제, 3번째 라운드부터 컴파일 오류가 남은 테스트 메서드 주석 처리.

## 공개 저장소와 다른 점

- 모델: OpenAI SDK 대신 Gemini를 부릅니다. temperature는 논문과 같은 0.5입니다.
- 프로젝트 지식: 실행 중에 인덱스를 검색하지 않고, 공개 저장소의 `CodeSearcher`로 json-schema-validator 1.1.0에서 미리 뽑은 결과(`data/ktester/tasks.json`)를 씁니다. 입력 내용은 같습니다.
- 테스트 실행: 노트북의 모든 집단과 같은 classpath(프로젝트 클래스, 프로젝트 의존 jar, JUnit, Mockito)로 컴파일하고 실행합니다.
- 대상: 공개 저장소의 `DatasetPrepare`가 클래스 안의 클래스(`ValidationMessage.Builder`)는 클래스 코드를 비워 내보내서, 그 메서드 9개는 뺐습니다.

jar(`project-info-process.jar`), Java 코드 편집기(`tools/code_analysis.py`), 템플릿 6개는 공개 저장소의 파일을 바꾸지 않고 씁니다.
