# KTester 프롬프트 예시: `SpecVersionDetector.detect(JsonNode)`
노트북 4-1에서 Gemini(`gemini-3.5-flash-lite`)로 실제로 주고받은 프롬프트와 응답입니다. 이 focal method는 다섯 단계를 모두 거쳤습니다(골격 1회, 케이스 설계 3회, 코드 생성 1회, 수리 1회). 4단계 integration은 모델을 부르지 않고 jar로 합칩니다.
프롬프트에서 무엇이 어떤 지식인지:
- **프로젝트 지식**(인덱스에서 꺼냄): 1단계 프롬프트의 `@input{context information}` 아래 항목(생성자, 매개변수 클래스, focal method 호출 예시 등)과 2·3·5단계의 `dependent classes`, `api document`, `return type` 항목
- **테스트 지식**: 2단계 프롬프트 세 개의 지시문. 각각 분기(condition branch-driven), 기능·경계(functionality-driven), 예외(exception-oriented) 관점으로 케이스를 설계하게 함
- `<cases_json>` 자리에는 앞 관점에서 나온 케이스가 들어가 겹치지 않게 합니다.

## 호출 1: 1. test class framework generation

### 프롬프트

````text
You are tasked with creating a framework for a test class in Java. Now analyze the following information carefully:

1. The method that needs to be tested and its parameters.
2. The constructor of the target class and its parameters.
3. Any dependencies or external resources used by the target class.

Based on this analysis, complete the test class template in the provided structure:

1. Initialize necessary fields and dependencies within setupBeforeAll() and setupBeforeEach().
2. Handle any required cleanup in teardownAfterEach() and teardownAfterAll().
3. Make sure not to invoke any private methods or fields of the target class and dependent class.
4. Refer to the "given" phase in the existing test class for guidance.
5. Add necessary import statements and ensure there are no syntax errors in the generated code.

@input{focal method and target class}
Here is the code of focal method, `detect(JsonNode)`, with the focal class `SpecVersionDetector_detect_Test`:
```Java
package com.networknt.schema;
import com.networknt.schema.SpecVersion.VersionFlag;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.stream.StreamSupport;
import java.util.Optional;
import java.util.Objects;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.stream.Stream;
import java.util.Map;
public final class SpecVersionDetector {
    protected static final Map<String, VersionFlag> supportedVersions = new HashMap<>();
    private static final String SCHEMA_TAG = "$schema";
    public static VersionFlag detect(JsonNode jsonNode) {
        return detectOptionalVersion(jsonNode).orElseThrow(() -> new JsonSchemaException(("'" + SpecVersionDetector.SCHEMA_TAG) + "' tag is not present"));
    }
public static Optional<VersionFlag> detectOptionalVersion(JsonNode jsonNode);
    public static Optional<VersionFlag> detectOptionalVersion(String schemaUri);
    public static VersionFlag detectVersion(JsonNode jsonNode, Path specification, VersionFlag defaultVersion);
    public static Optional<VersionFlag> detectVersionFromPath(Path path);
}
```


@input{context information}

api document of class com.networknt.schema.SpecVersionDetector: 

 * This class is used to detect schema version
 *
 * @author Subhajitdas298
 * @since 25/06/20
 

constructors for class `com.networknt.schema.SpecVersionDetector`: 
params: 
body:
```java
    private SpecVersionDetector() {
        // Prevent instantiation of this utility class
    }

```

existing test class: 
```java
package com.networknt.schema;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.io.IOException;
import java.io.InputStream;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SpecVersionDetectorTest {

    private static final ObjectMapper mapper = new ObjectMapper();

    @ParameterizedTest
    @CsvSource({
            "draft4,       V4",
            "draft6,       V6",
            "draft7,       V7",
            "draft2019-09, V201909",
            "draft2020-12, V202012"
    })
    void detectVersion(String resourceDirectory, SpecVersion.VersionFlag expectedFlag) throws IOException {
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream(resourceDirectory + "/schemaTag.json");
        JsonNode node = mapper.readTree(in);
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        assertEquals(expectedFlag, flag);
    }

    @ParameterizedTest
    @CsvSource({
            "data/schemaTag.json,        'http://json-schema.org/draft-03/schema#' is unrecognizable schema",
            "data/schemaTagMissing.json, '$schema' tag is not present"
    })
    void detectInvalidSchemaVersion(String schemaPath, String expectedError) throws IOException {
        InputStream in = Thread.currentThread().getContextClassLoader().getResourceAsStream(schemaPath);
        JsonNode node = mapper.readTree(in);
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> SpecVersionDetector.detect(node));
        assertEquals(expectedError, exception.getMessage());
    }

    @Test
    void detectOptionalSpecVersion() throws IOException {
        InputStream in = Thread.currentThread().getContextClassLoader().getResourceAsStream(
                "data/schemaTagMissing.json");
        JsonNode node = mapper.readTree(in);
        Optional<SpecVersion.VersionFlag> flag = SpecVersionDetector.detectOptionalVersion(node);
        assertEquals(Optional.empty(), flag);
    }
}

```



@input{test class template}
```java
package com.networknt.schema;

import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.junit.jupiter.api.Assertions.*;
import org.mockito.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
// Add other imports if necessary

@ExtendWith(MockitoExtension.class)
class SpecVersionDetector_detect_Test {
    @BeforeAll
    static void setupBeforeAll() {
    }

    @BeforeEach
    void setupBeforeEach() {
    }

    @AfterEach
    void teardownAfterEach() {
    }

    @AfterAll
    static void teardownAfterAll() {
    }
}
```

@output{initial test class}: now consider the invoke examples output the code wrapped in a Markdown code block ```java at the beginning and ``` at the end.
````

### 응답

````text
```java
package com.networknt.schema;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.junit.jupiter.api.Assertions.*;
import org.mockito.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.io.InputStream;

@ExtendWith(MockitoExtension.class)
class SpecVersionDetector_detect_Test {

    private ObjectMapper mapper;

    @BeforeAll
    static void setupBeforeAll() {
        // Initialization before all tests if needed
    }

    @BeforeEach
    void setupBeforeEach() {
        mapper = new ObjectMapper();
    }

    @AfterEach
    void teardownAfterEach() {
        // Cleanup after each test if needed
    }

    @AfterAll
    static void teardownAfterAll() {
        // Cleanup after all tests if needed
    }

    @Test
    void testDetectValidSchema() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("draft4/schemaTag.json");
        JsonNode node = mapper.readTree(in);

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectMissingSchemaTagThrowsException() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("data/schemaTagMissing.json");
        JsonNode node = mapper.readTree(in);

        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }
}
```
````

## 호출 2: 2. test case design (condition branch-driven)

### 프롬프트

````text
As a professional Java software testing expert, your task is to generate test cases for a focal method.

You will be provided with:
1. The focal method that needs testing.
2. Basic information of the target class to which the focus method belongs, including fields and methods.

Ensure the generated test cases meet the following requirements:

Test Coverage Requirements:
- Create test cases to cover all conditional branches in the target method, including `if`, `else if`, `else`, `switch`, and `case` statements.

Output Format:
- Organize the test cases by its functions logically.
- Include input parameters, expected output, and a description for each test case.
- Use empty list `[]` for the input when a test case does not require input parameters.
- Provide an expected return value for each test case, or specify the behavior that should be verified if there's no return value.
- Clearly describe the intention of each test case in the description.

Follow the JSON format provided here for the output:
```json
[
    {
        "group": "test name",
        "cases": [
            {
                "input": [
                    {
                        "parameter": "param name",
                        "value": "param value"
                    }
                ],
                "expected": "expected exception or behavior",
                "description": "test scenario description"
            }
        ]
    },
    {...}
]
```
@input{focal method and target class}
Here is the code of focal method, `detect(JsonNode)`, with the focal class `SpecVersionDetector`:
```Java
package com.networknt.schema;
import com.networknt.schema.SpecVersion.VersionFlag;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.stream.StreamSupport;
import java.util.Optional;
import java.util.Objects;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.stream.Stream;
import java.util.Map;
public final class SpecVersionDetector {
    protected static final Map<String, VersionFlag> supportedVersions = new HashMap<>();
    private static final String SCHEMA_TAG = "$schema";
    public static VersionFlag detect(JsonNode jsonNode) {
        return detectOptionalVersion(jsonNode).orElseThrow(() -> new JsonSchemaException(("'" + SpecVersionDetector.SCHEMA_TAG) + "' tag is not present"));
    }
public static Optional<VersionFlag> detectOptionalVersion(JsonNode jsonNode);
    public static Optional<VersionFlag> detectOptionalVersion(String schemaUri);
    public static VersionFlag detectVersion(JsonNode jsonNode, Path specification, VersionFlag defaultVersion);
    public static Optional<VersionFlag> detectVersionFromPath(Path path);
}
```

@output{test cases}: output the test cases in the JSON format:
````

### 응답

````text
[
    {
        "group": "detectTest",
        "cases": [
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{\"\\$schema\": \"https://json-schema.org/draft/2020-12/schema\"}"
                    }
                ],
                "expected": "VersionFlag.V202012",
                "description": "Test detect method when valid schema tag is present returning a version flag."
            },
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{}"
                    }
                ],
                "expected": "JsonSchemaException",
                "description": "Test detect method when schema tag is missing throwing a JsonSchemaException."
            }
        ]
    }
]
````

## 호출 3: 2. test case design (functionality-driven)

### 프롬프트

````text
As a professional Java software testing expert, your task is to generate test cases for a focal method.

Guidelines:
1. Analyze the method's functionality and identify possible input combinations including normal cases and boundary conditions.
2. Review the provided existing test cases. Avoid duplication and create new test cases for untested input combinations.

Context Provided:
1. The focal method that needs testing.
2. Relevant code and metadata for the class containing the method, including fields and other methods.
3. The existing test cases (in JSON format) to help avoid redundancy.

Output Instructions:
- Organize the test cases by the name of the test function (group).
- Each test case must include:
    - input: A list of parameter names and values. Use an empty list `[]` if no input is required.
    - expected: The return value or expected observable behavior.
    - description: A clear and concise explanation of the scenario and the intent of the test case.

Maintain the following strict JSON format:
```json
[
    {
        "group": "test name",
        "cases": [
            {
                "input": [
                    {
                        "parameter": "param name",
                        "value": "param value"
                    }
                ],
                "expected": "expected exception or behavior",
                "description": "test scenario description"
            }
        ]
    },
    {...}
]
```

@input{focal method and target class}
Here is the code of focal method, `detect(JsonNode)`, with the focal class `SpecVersionDetector`:
```Java
package com.networknt.schema;
import com.networknt.schema.SpecVersion.VersionFlag;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.stream.StreamSupport;
import java.util.Optional;
import java.util.Objects;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.stream.Stream;
import java.util.Map;
public final class SpecVersionDetector {
    protected static final Map<String, VersionFlag> supportedVersions = new HashMap<>();
    private static final String SCHEMA_TAG = "$schema";
    public static VersionFlag detect(JsonNode jsonNode) {
        return detectOptionalVersion(jsonNode).orElseThrow(() -> new JsonSchemaException(("'" + SpecVersionDetector.SCHEMA_TAG) + "' tag is not present"));
    }
public static Optional<VersionFlag> detectOptionalVersion(JsonNode jsonNode);
    public static Optional<VersionFlag> detectOptionalVersion(String schemaUri);
    public static VersionFlag detectVersion(JsonNode jsonNode, Path specification, VersionFlag defaultVersion);
    public static Optional<VersionFlag> detectVersionFromPath(Path path);
}
```

@input{existing test case}
here's the existing test cases:
```json
[{'group': 'detectTest', 'cases': [{'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "https://json-schema.org/draft/2020-12/schema"}'}], 'expected': 'VersionFlag.V202012', 'description': 'Test detect method when valid schema tag is present returning a version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{}'}], 'expected': 'JsonSchemaException', 'description': 'Test detect method when schema tag is missing throwing a JsonSchemaException.'}]}]
```

@output{test cases}: output the test cases in the JSON format:
````

### 응답

````text
[
    {
        "group": "detectTest",
        "cases": [
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{\"\\$schema\": \"http://json-schema.org/draft-07/schema#\"}"
                    }
                ],
                "expected": "VersionFlag.V7",
                "description": "Test detect method with Draft 7 schema tag returning V7 version flag."
            },
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{\"\\$schema\": \"http://json-schema.org/draft-04/schema#\"}"
                    }
                ],
                "expected": "VersionFlag.V4",
                "description": "Test detect method with Draft 4 schema tag returning V4 version flag."
            },
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{\"\\$schema\": \"https://json-schema.org/draft/2019-09/schema\"}"
                    }
                ],
                "expected": "VersionFlag.V201909",
                "description": "Test detect method with Draft 2019-09 schema tag returning V201909 version flag."
            },
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{\"\\$schema\": \"unsupported-uri\"}"
                    }
                ],
                "expected": "JsonSchemaException",
                "description": "Test detect method with unsupported schema URI throwing a JsonSchemaException."
            }
        ]
    }
]
````

## 호출 4: 2. test case design (exception-oriented)

### 프롬프트

````text
You are a professional software tester. Write test cases for a focal method in a target class.

**Instructions:**
1. Analyze method behavior and identify ALL possible exception scenarios
2. Design test cases that trigger each identified exception
3. Follow existing test case structure, Avoid duplication and create new test cases for uncovered exception scenarios

Test Case Format:
1. Group test cases by test function name
2. Each test case MUST include:
   - Input parameters with values (use empty list `[]` if none)
   - Expected exception or observable behavior
   - Clear description of test scenario
3. Return empty array if no exception scenarios found

Output Schema (STRICT JSON format):
```json
[
    {
        "group": "test name",
        "cases": [
            {
                "input": [
                    {
                        "parameter": "param name",
                        "value": "param value"
                    }
                ],
                "expected": "expected exception or behavior",
                "description": "test scenario description"
            }
        ]
    },
    {...}
]
```

@input{focal method and target class}
Here is the code of focal method, `detect(JsonNode)`, with the focal class `SpecVersionDetector`:
```Java
package com.networknt.schema;
import com.networknt.schema.SpecVersion.VersionFlag;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.stream.StreamSupport;
import java.util.Optional;
import java.util.Objects;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.stream.Stream;
import java.util.Map;
public final class SpecVersionDetector {
    protected static final Map<String, VersionFlag> supportedVersions = new HashMap<>();
    private static final String SCHEMA_TAG = "$schema";
    public static VersionFlag detect(JsonNode jsonNode) {
        return detectOptionalVersion(jsonNode).orElseThrow(() -> new JsonSchemaException(("'" + SpecVersionDetector.SCHEMA_TAG) + "' tag is not present"));
    }
public static Optional<VersionFlag> detectOptionalVersion(JsonNode jsonNode);
    public static Optional<VersionFlag> detectOptionalVersion(String schemaUri);
    public static VersionFlag detectVersion(JsonNode jsonNode, Path specification, VersionFlag defaultVersion);
    public static Optional<VersionFlag> detectVersionFromPath(Path path);
}
```
@input{existing test case}
here's the existing test cases:
```json
[{'group': 'detectTest', 'cases': [{'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "https://json-schema.org/draft/2020-12/schema"}'}], 'expected': 'VersionFlag.V202012', 'description': 'Test detect method when valid schema tag is present returning a version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{}'}], 'expected': 'JsonSchemaException', 'description': 'Test detect method when schema tag is missing throwing a JsonSchemaException.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "http://json-schema.org/draft-07/schema#"}'}], 'expected': 'VersionFlag.V7', 'description': 'Test detect method with Draft 7 schema tag returning V7 version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "http://json-schema.org/draft-04/schema#"}'}], 'expected': 'VersionFlag.V4', 'description': 'Test detect method with Draft 4 schema tag returning V4 version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "https://json-schema.org/draft/2019-09/schema"}'}], 'expected': 'VersionFlag.V201909', 'description': 'Test detect method with Draft 2019-09 schema tag returning V201909 version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "unsupported-uri"}'}], 'expected': 'JsonSchemaException', 'description': 'Test detect method with unsupported schema URI throwing a JsonSchemaException.'}]}]
```

@output{test cases}: output the test cases in the JSON format:
````

### 응답

````text
[
    {
        "group": "detectTest",
        "cases": [
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "null"
                    }
                ],
                "expected": "NullPointerException",
                "description": "Test detect method when jsonNode is null throwing a NullPointerException."
            },
            {
                "input": [
                    {
                        "parameter": "jsonNode",
                        "value": "{\"\\$schema\": null}"
                    }
                ],
                "expected": "JsonSchemaException",
                "description": "Test detect method when schema tag value is null throwing a JsonSchemaException."
            }
        ]
    }
]
````

## 호출 5: 3. test method transformation

### 프롬프트

````text
You are a professional Java software testing expert. Your task is to generate high-quality unit test code for a focal method, using **JUnit5** and **Mockito** libraries. 

You'll be provided with:
1. The focal method to test.
2. The target class's structure (fields and methods).
3. A pre-defined test class framework with `@Before`/`@After` methods.
4. Test cases in JSON format.
5. Any relevant context.

**Requirements:**

Code Quality:
- Include clear comments explaining each test scenario.
- Ensure code is clean, understandable, and maintainable.
- Do not directly access private methods or fields. **Use reflection if the focal method is private.**
- Include all necessary imports; code must be free of syntax errors.

**Test Structure:**
- Follow the given test class framework; do not modify `@Before`/`@After` methods.
- Create one test function per test case group, ensuring all cases are covered.
- Use parameterized tests where appropriate.
- Reinitialize variables inside test functions if `@Setup` values don't fit.
- Properly mock and set up dependencies.

@input{focal method and target class}
Here is the code of focal method, `detect(JsonNode)`, with the focal class `SpecVersionDetector`:
```Java
package com.networknt.schema;
import com.networknt.schema.SpecVersion.VersionFlag;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.stream.StreamSupport;
import java.util.Optional;
import java.util.Objects;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.stream.Stream;
import java.util.Map;
public final class SpecVersionDetector {
    protected static final Map<String, VersionFlag> supportedVersions = new HashMap<>();
    private static final String SCHEMA_TAG = "$schema";
    public static VersionFlag detect(JsonNode jsonNode) {
        return detectOptionalVersion(jsonNode).orElseThrow(() -> new JsonSchemaException(("'" + SpecVersionDetector.SCHEMA_TAG) + "' tag is not present"));
    }
public static Optional<VersionFlag> detectOptionalVersion(JsonNode jsonNode);
    public static Optional<VersionFlag> detectOptionalVersion(String schemaUri);
    public static VersionFlag detectVersion(JsonNode jsonNode, Path specification, VersionFlag defaultVersion);
    public static Optional<VersionFlag> detectVersionFromPath(Path path);
}
```

@input{initial test class framework}
```Java
package com.networknt.schema;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.junit.jupiter.api.Assertions.*;
import org.mockito.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.io.InputStream;

@ExtendWith(MockitoExtension.class)
class SpecVersionDetector_detect_Test{

    private ObjectMapper mapper;

    @BeforeAll
    static void setupBeforeAll() {
        // Initialization before all tests if needed
    }

    @BeforeEach
    void setupBeforeEach() {
        mapper = new ObjectMapper();
    }

    @AfterEach
    void teardownAfterEach() {
        // Cleanup after each test if needed
    }

    @AfterAll
    static void teardownAfterAll() {
        // Cleanup after all tests if needed
    }

    @Test
    void testDetectValidSchema() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("draft4/schemaTag.json");
        JsonNode node = mapper.readTree(in);

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectMissingSchemaTagThrowsException() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("data/schemaTagMissing.json");
        JsonNode node = mapper.readTree(in);

        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }
}
```

@input{existing test case}
here's the existing test cases:
```json
[{'group': 'detectTest', 'cases': [{'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "https://json-schema.org/draft/2020-12/schema"}'}], 'expected': 'VersionFlag.V202012', 'description': 'Test detect method when valid schema tag is present returning a version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{}'}], 'expected': 'JsonSchemaException', 'description': 'Test detect method when schema tag is missing throwing a JsonSchemaException.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "http://json-schema.org/draft-07/schema#"}'}], 'expected': 'VersionFlag.V7', 'description': 'Test detect method with Draft 7 schema tag returning V7 version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "http://json-schema.org/draft-04/schema#"}'}], 'expected': 'VersionFlag.V4', 'description': 'Test detect method with Draft 4 schema tag returning V4 version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "https://json-schema.org/draft/2019-09/schema"}'}], 'expected': 'VersionFlag.V201909', 'description': 'Test detect method with Draft 2019-09 schema tag returning V201909 version flag.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": "unsupported-uri"}'}], 'expected': 'JsonSchemaException', 'description': 'Test detect method with unsupported schema URI throwing a JsonSchemaException.'}, {'input': [{'parameter': 'jsonNode', 'value': 'null'}], 'expected': 'NullPointerException', 'description': 'Test detect method when jsonNode is null throwing a NullPointerException.'}, {'input': [{'parameter': 'jsonNode', 'value': '{"\\$schema": null}'}], 'expected': 'JsonSchemaException', 'description': 'Test detect method when schema tag value is null throwing a JsonSchemaException.'}]}]
```


@input{context information}

api document of class com.networknt.schema.SpecVersionDetector: 

 * This class is used to detect schema version
 *
 * @author Subhajitdas298
 * @since 25/06/20
 

api document of method detect(JsonNode): 

     * Detects schema version based on the schema tag: if the schema tag is not present, throws
     * {@link JsonSchemaException} with the corresponding message, otherwise - returns the detected spec version.
     *
     * @param jsonNode JSON Node to read from
     * @return Spec version if present, otherwise throws an exception
     

return type: 
com.networknt.schema.SpecVersion.VersionFlag

dependent classes: 
class `com.networknt.schema.SpecVersionDetector`:
	dependent fields:
		java.lang.String com.networknt.schema.SpecVersionDetector.SCHEMA_TAG;
	related functions:
		method `public static Optional<VersionFlag> detectOptionalVersion(JsonNode)` returns `java.util.Optional<com.networknt.schema.SpecVersion.VersionFlag>`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Detects schema version based on the schema tag: if the schema tag is not present, returns an empty {@link
     * Optional} value, otherwise - returns the detected spec version wrapped into {@link Optional}.
     *
     * @param jsonNode JSON Node to read from
     * @return Spec version if present, otherwise empty
     ;
		method `public static VersionFlag detectVersion(JsonNode, Path, VersionFlag)` returns `com.networknt.schema.SpecVersion.VersionFlag`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`;
class `com.networknt.schema.JsonSchemaFactory`:
	related functions:
		method `private JsonMetaSchema fromId(String)` returns `com.networknt.schema.JsonMetaSchema`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`;
		method `private JsonMetaSchema findMetaSchemaForSchema(JsonNode)` returns `com.networknt.schema.JsonMetaSchema`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`;
class `com.networknt.schema.JsonSchema`:
	related functions:
		method `private void updateThisAsSubschema(URI)` returns `void`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Creates a new parent schema from the current state and updates this object to refer to the subschema instead.
     ;
class `com.networknt.schema.BaseJsonValidator`:
	related functions:
		method `protected static void registerAndMergeDiscriminator(DiscriminatorContext, ObjectNode, JsonSchema, String)` returns `void`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Rolls up all nested and compatible discriminators to the root discriminator of the type. Detects attempts to redefine
     * the <code>propertyName</code> or mappings.
     *
     * @param currentDiscriminatorContext the currently active {@link DiscriminatorContext}
     * @param discriminator               the discriminator to use for the check
     * @param schema                      the value of the <code>discriminator/propertyName</code> field
     * @param at                          the logging prefix
     ;
class `com.networknt.org.apache.commons.validator.routines.InetAddressValidator`:
	related functions:
		method `public static InetAddressValidator getInstance()` returns `com.networknt.org.apache.commons.validator.routines.InetAddressValidator`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Returns the singleton instance of this validator.
     *
     * @return the singleton instance of this validator
     ;



@output{test class}: output the code wrapped in a Markdown code block ```java at the beginning and ``` at the end.
````

### 응답

````text
```java
package com.networknt.schema;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.junit.jupiter.api.Assertions.*;
import org.mockito.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.io.InputStream;

@ExtendWith(MockitoExtension.class)
class SpecVersionDetector_detect_Test{

    private ObjectMapper mapper;

    @BeforeAll
    static void setupBeforeAll() {
        // Initialization before all tests if needed
    }

    @BeforeEach
    void setupBeforeEach() {
        mapper = new ObjectMapper();
    }

    @AfterEach
    void teardownAfterEach() {
        // Cleanup after each test if needed
    }

    @AfterAll
    static void teardownAfterAll() {
        // Cleanup after all tests if needed
    }

    @Test
    void testDetectValidSchema() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("draft4/schemaTag.json");
        JsonNode node = mapper.readTree(in);

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectMissingSchemaTagThrowsException() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("data/schemaTagMissing.json");
        JsonNode node = mapper.readTree(in);

        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }

    @Test
    void testDetectVersion202012() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"https://json-schema.org/draft/2020-12/schema\"}");

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V202012, flag);
    }

    @Test
    void testDetectEmptyNodeThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{}");

        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }

    @Test
    void testDetectDraft7() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-07/schema#\"}");

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V7, flag);
    }

    @Test
    void testDetectDraft4() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-04/schema#\"}");

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectVersion201909() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"https://json-schema.org/draft/2019-09/schema\"}");

        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);

        // Then
        assertEquals(SpecVersion.VersionFlag.V201909, flag);
    }

    @Test
    void testDetectUnsupportedUriThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"unsupported-uri\"}");

        // When & Then
        assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
    }

    @Test
    void testDetectNullNodeThrowsNullPointerException() {
        // When & Then
        assertThrows(NullPointerException.class, () -> {
            SpecVersionDetector.detect(null);
        });
    }

    @Test
    void testDetectNullSchemaTagValueThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": null}");

        // When & Then
        assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
    }
}
```
````

## 호출 6: 5. test class refinement (LLM 수리)

### 프롬프트

````text



You are an experienced Java developer tasked with fixing a piece of code that contains execution errors. Your task is to resolve these issues after analyzing the code and its execution feedback.

Use the following steps to guide your analysis and correction process:
1. Review the provided Java code for any logical errors.
2. Analyze the execution feedback to understand the specific errors and their locations within the code.
3. Apply necessary corrections to the code based on the feedback, and output the compelete correct code.
The Java code you need to fix is provided below:
```java
package com.networknt.schema;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.junit.jupiter.api.Assertions.*;
import org.mockito.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import java.io.IOException;
import java.io.InputStream;

@ExtendWith(MockitoExtension.class)
class SpecVersionDetector_detect_Test {

    private ObjectMapper mapper;

    @BeforeEach
    void setupBeforeEach() {
        mapper = new ObjectMapper();
    }

    @Test
    void testDetectValidSchema() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader().getResourceAsStream("draft4/schemaTag.json");
        JsonNode node = mapper.readTree(in);
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectMissingSchemaTagThrowsException() throws IOException {
        // Given
        InputStream in = Thread.currentThread().getContextClassLoader().getResourceAsStream("data/schemaTagMissing.json");
        JsonNode node = mapper.readTree(in);
        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }

    @Test
    void testDetectVersion202012() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"https://json-schema.org/draft/2020-12/schema\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V202012, flag);
    }

    @Test
    void testDetectEmptyNodeThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{}");
        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }

    @Test
    void testDetectDraft7() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-07/schema#\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V7, flag);
    }

    @Test
    void testDetectDraft4() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-04/schema#\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectVersion201909() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"https://json-schema.org/draft/2019-09/schema\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V201909, flag);
    }

    @Test
    void testDetectUnsupportedUriThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"unsupported-uri\"}");
        // When & Then
        assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
    }

    @Test
    void testDetectNullNodeThrowsNullPointerException() {
        // When & Then
        assertThrows(NullPointerException.class, () -> {
            SpecVersionDetector.detect(null);
        });
    }

    @Test
    void testDetectNullSchemaTagValueThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": null}");
        // When & Then
        assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
    }
}

```

Corresponding execution feedback:
```
OpenJDK 64-Bit Server VM warning: Sharing is only supported for boot loader classes because bootstrap classpath has been appended

╷
├─ JUnit Jupiter ✔
│  └─ SpecVersionDetector_detect_Test ✔
│     ├─ testDetectValidSchema() ✘ argument "in" is null
│     ├─ testDetectNullNodeThrowsNullPointerException() ✔
│     ├─ testDetectDraft4() ✔
│     ├─ testDetectDraft7() ✔
│     ├─ testDetectNullSchemaTagValueThrowsException() ✔
│     ├─ testDetectUnsupportedUriThrowsException() ✔
│     ├─ testDetectVersion201909() ✔
│     ├─ testDetectVersion202012() ✔
│     ├─ testDetectEmptyNodeThrowsException() ✔
│     └─ testDetectMissingSchemaTagThrowsException() ✘ argument "in" is null
├─ JUnit Vintage ✔
└─ JUnit Platform Suite ✔

Failures (2):
  JUnit Jupiter:SpecVersionDetector_detect_Test:testDetectValidSchema()
    MethodSource [className = 'com.networknt.schema.SpecVersionDetector_detect_Test', methodName = 'testDetectValidSchema', methodParameterTypes = '']
    => java.lang.IllegalArgumentException: argument "in" is null
       com.fasterxml.jackson.databind.ObjectMapper._assertNotNull(ObjectMapper.java:4980)
       com.fasterxml.jackson.databind.ObjectMapper.readTree(ObjectMapper.java:3198)
       com.networknt.schema.SpecVersionDetector_detect_Test.testDetectValidSchema(SpecVersionDetector_detect_Test.java:28)
       java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
       java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:77)
       java.base/jdk.internal.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
       java.base/java.lang.reflect.Method.invoke(Method.java:569)
       org.junit.platform.commons.util.ReflectionUtils.invokeMethod(ReflectionUtils.java:727)
       org.junit.jupiter.engine.execution.MethodInvocation.proceed(MethodInvocation.java:60)
       org.junit.jupiter.engine.execution.InvocationInterceptorChain$ValidatingInvocation.proceed(InvocationInterceptorChain.java:131)
       [...]
  JUnit Jupiter:SpecVersionDetector_detect_Test:testDetectMissingSchemaTagThrowsException()
    MethodSource [className = 'com.networknt.schema.SpecVersionDetector_detect_Test', methodName = 'testDetectMissingSchemaTagThrowsException', methodParameterTypes = '']
    => java.lang.IllegalArgumentException: argument "in" is null
       com.fasterxml.jackson.databind.ObjectMapper._assertNotNull(ObjectMapper.java:4980)
       com.fasterxml.jackson.databind.ObjectMapper.readTree(ObjectMapper.java:3198)
       com.networknt.schema.SpecVersionDetector_detect_Test.testDetectMissingSchemaTagThrowsException(SpecVersionDetector_detect_Test.java:39)
       java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
       java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:77)
       java.base/jdk.internal.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
       java.base/java.lang.reflect.Method.invoke(Method.java:569)
       org.junit.platform.commons.util.ReflectionUtils.invokeMethod(ReflectionUtils.java:727)
       org.junit.jupiter.engine.execution.MethodInvocation.proceed(MethodInvocation.java:60)
       org.junit.jupiter.engine.execution.InvocationInterceptorChain$ValidatingInvocation.proceed(InvocationInterceptorChain.java:131)
       [...]

Test run finished after 2035 ms
[         4 containers found      ]
[         0 containers skipped    ]
[         4 containers started    ]
[         0 containers aborted    ]
[         4 containers successful ]
[         0 containers failed     ]
[        10 tests found           ]
[         0 tests skipped         ]
[        10 tests started         ]
[         0 tests aborted         ]
[         8 tests successful      ]
[         2 tests failed          ]


```


And you can use the following related information to assist you in your analysis and correction:

api document of class com.networknt.schema.SpecVersionDetector: 

 * This class is used to detect schema version
 *
 * @author Subhajitdas298
 * @since 25/06/20
 

api document of method detect(JsonNode): 

     * Detects schema version based on the schema tag: if the schema tag is not present, throws
     * {@link JsonSchemaException} with the corresponding message, otherwise - returns the detected spec version.
     *
     * @param jsonNode JSON Node to read from
     * @return Spec version if present, otherwise throws an exception
     

return type: 
com.networknt.schema.SpecVersion.VersionFlag

dependent classes: 
class `com.networknt.schema.SpecVersionDetector`:
	dependent fields:
		java.lang.String com.networknt.schema.SpecVersionDetector.SCHEMA_TAG;
	related functions:
		method `public static Optional<VersionFlag> detectOptionalVersion(JsonNode)` returns `java.util.Optional<com.networknt.schema.SpecVersion.VersionFlag>`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Detects schema version based on the schema tag: if the schema tag is not present, returns an empty {@link
     * Optional} value, otherwise - returns the detected spec version wrapped into {@link Optional}.
     *
     * @param jsonNode JSON Node to read from
     * @return Spec version if present, otherwise empty
     ;
		method `public static VersionFlag detectVersion(JsonNode, Path, VersionFlag)` returns `com.networknt.schema.SpecVersion.VersionFlag`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`;
class `com.networknt.schema.JsonSchemaFactory`:
	related functions:
		method `private JsonMetaSchema fromId(String)` returns `com.networknt.schema.JsonMetaSchema`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`;
		method `private JsonMetaSchema findMetaSchemaForSchema(JsonNode)` returns `com.networknt.schema.JsonMetaSchema`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`;
class `com.networknt.schema.JsonSchema`:
	related functions:
		method `private void updateThisAsSubschema(URI)` returns `void`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Creates a new parent schema from the current state and updates this object to refer to the subschema instead.
     ;
class `com.networknt.schema.BaseJsonValidator`:
	related functions:
		method `protected static void registerAndMergeDiscriminator(DiscriminatorContext, ObjectNode, JsonSchema, String)` returns `void`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Rolls up all nested and compatible discriminators to the root discriminator of the type. Detects attempts to redefine
     * the <code>propertyName</code> or mappings.
     *
     * @param currentDiscriminatorContext the currently active {@link DiscriminatorContext}
     * @param discriminator               the discriminator to use for the check
     * @param schema                      the value of the <code>discriminator/propertyName</code> field
     * @param at                          the logging prefix
     ;
class `com.networknt.org.apache.commons.validator.routines.InetAddressValidator`:
	related functions:
		method `public static InetAddressValidator getInstance()` returns `com.networknt.org.apache.commons.validator.routines.InetAddressValidator`, related with `com.networknt.schema.SpecVersionDetector.detect(JsonNode)`, api document: 
     * Returns the singleton instance of this validator.
     *
     * @return the singleton instance of this validator
     ;



Now you should output the corrected Java code wrapped in a Markdown code block ```java at the beginning and ``` at the end:
````

### 응답

````text
```java
package com.networknt.schema;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import static org.junit.jupiter.api.Assertions.*;
import org.mockito.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import java.io.IOException;
import java.io.InputStream;

@ExtendWith(MockitoExtension.class)
class SpecVersionDetector_detect_Test {

    private ObjectMapper mapper;

    @BeforeEach
    void setupBeforeEach() {
        mapper = new ObjectMapper();
    }

    @Test
    void testDetectValidSchema() throws IOException {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-04/schema#\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectMissingSchemaTagThrowsException() throws IOException {
        // Given
        JsonNode node = mapper.readTree("{}");
        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }

    @Test
    void testDetectVersion202012() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"https://json-schema.org/draft/2020-12/schema\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V202012, flag);
    }

    @Test
    void testDetectEmptyNodeThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{}");
        // When & Then
        JsonSchemaException exception = assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
        assertEquals("'$schema' tag is not present", exception.getMessage());
    }

    @Test
    void testDetectDraft7() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-07/schema#\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V7, flag);
    }

    @Test
    void testDetectDraft4() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"http://json-schema.org/draft-04/schema#\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V4, flag);
    }

    @Test
    void testDetectVersion201909() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"https://json-schema.org/draft/2019-09/schema\"}");
        // When
        SpecVersion.VersionFlag flag = SpecVersionDetector.detect(node);
        // Then
        assertEquals(SpecVersion.VersionFlag.V201909, flag);
    }

    @Test
    void testDetectUnsupportedUriThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": \"unsupported-uri\"}");
        // When & Then
        assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
    }

    @Test
    void testDetectNullNodeThrowsNullPointerException() {
        // When & Then
        assertThrows(NullPointerException.class, () -> {
            SpecVersionDetector.detect(null);
        });
    }

    @Test
    void testDetectNullSchemaTagValueThrowsException() throws Exception {
        // Given
        JsonNode node = mapper.readTree("{\"$schema\": null}");
        // When & Then
        assertThrows(JsonSchemaException.class, () -> {
            SpecVersionDetector.detect(node);
        });
    }
}
```
````
