# Ouédraogo et al. 프롬프트 5종
Ouédraogo et al. (EMSE 2026)이 쓴 프롬프트입니다. 저자에게 받은 재현 자료에서 그대로 옮겼고 오타도 원문 그대로입니다. 노트북은 `{class_name}`에 클래스 이름, `{source_code}`에 클래스 소스 전체, `{fewshot_example}`에 아래 예시를 넣어 씁니다.
| 이름 | 방식 |
|---|---|
| ZSL | Zero-shot. 역할과 과제만 주고 바로 테스트 파일을 요청 |
| FSL | Few-shot. 예시 클래스와 그 테스트 파일을 먼저 보여 줌 |
| CoT | Chain-of-thought. 메서드 나열, 기본 테스트, 경계·예외 테스트, 합치기의 단계를 지시 |
| ToT | Tree-of-thought. 전문가 세 명이 의견을 나누며 테스트를 만드는 상황을 지시 |
| GToT | ToT와 CoT의 단계를 합친 형태 |

## ZSL

```text
As a professional software tester who writes Java test methods, generate a complete Junit 4 test file ({class_name}Test.java) to comprehensively test all methods in the following class named {class_name}. Your output file must start with ###Test START## and finish with ###Test END##. Here is the source code:
{source_code}
```

## FSL

```text
As a professional software tester who writes Java test methods, consider the following examples:{fewshot_example}
Now, generate JUnit 4 test cases to comprehensively test all methods in the following class named {class_name}. Your output file must start with ###Test START## and finish with ###Test END##. Here is the source code:
{source_code}.
```

## CoT

```text
As a professional software tester who writes Java test methods, generate Junit 4 test cases to comprehensively test all methods in the following class named {class_name} by following these steps:
- Extract and list all the public methods including their signatures
- For each methods, generate a basic JUnit 4 test case that checks the method's functionality
- Given the source code of the class and the listed methods, identify potential edge cases and exception handling scenarios that should be tested
- Generate JUnit 4 test cases that specifically test for the identified edge cases and exceptions
- Merge all the individual test cases into a complete JUnit 4 test file ({class_name}Test.java) for the given Java class. The complete JUnit test file must start with ###Test START## and finish with ###Test END##
Here is the {class_name} class:
{source_code}
```

## ToT

```text
Imagine three different experts in software testing who are tasked with developing comprehensive JUnit 4 test cases for the following Java class. All experts will propose one test cases for each method, share it with the group, and then proceed to the next step. If any expert realizes they're wrong at any point, they leave.
The Java class is:
{source_code}
At the end they must propose one complete (including typical use cases, edge cases, and error scenarios) JUnit 4 test file ({class_name}Test.java) for the given Java class. The complete JUnit test file must start with ###Test START## and finish with ###Test END##
```

## GToT

```text
Imagine three different experts in software testing who are tasked with developing comprehensive JUnit 4 test cases for the following Java class.To comprehensively test all methods in the following class named {class_name} they must following these steps:
- Extract and list all the public methods including their signatures
- For each methods, generate a basic JUnit 4 test case that checks the method's functionality
- Given the source code of the class and the listed methods, identify potential edge cases and exception handling scenarios that should be tested
- Generate JUnit 4 test cases that specifically test for the identified edge cases and exceptions
- Merge all the individual test cases into a complete JUnit 4 test file ({class_name}Test.java) for the given Java class.All experts will propose one test cases for each method, share it with the group, and then proceed to the next step. If any expert realizes they're wrong at any point, they leave.
The Java class is:
{source_code}
At the end they must propose one complete (including typical use cases, edge cases, and error scenarios) JUnit 4 test file ({class_name}Test.java) for the given Java class. The complete JUnit test file must start with ###Test START## and finish with ###Test END##
```

## FSL 예시 (`{fewshot_example}`)

```java
//Example Java Class:
package org.apache.commons.cli;

final class Util {

    static final String[] EMPTY_STRING_ARRAY = {};

    static String stripLeadingAndTrailingQuotes(String str) {
        final int length = str.length();
        if (length > 1 && str.startsWith(""") && str.endsWith(""") && str.substring(1, length - 1).indexOf('"') == -1) {
            str = str.substring(1, length - 1);
        }

        return str;
    }

    static String stripLeadingHyphens(final String str) {
        if (str == null) {
            return null;
        }
        if (str.startsWith("--")) {
            return str.substring(2);
        }
        if (str.startsWith("-")) {
            return str.substring(1);
        }

        return str;
    }
}


//Corresponding JUnit 4 Test Cases:
package org.apache.commons.cli;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import org.junit.Test;

public class UtilTest {
    @Test
    public void testStripLeadingAndTrailingQuotes() {
        assertEquals("foo", Util.stripLeadingAndTrailingQuotes(""foo""));
        assertEquals("foo "bar"", Util.stripLeadingAndTrailingQuotes("foo "bar""));
        assertEquals(""foo" bar", Util.stripLeadingAndTrailingQuotes(""foo" bar"));
        assertEquals(""foo" and "bar"", Util.stripLeadingAndTrailingQuotes(""foo" and "bar""));
        assertEquals(""", Util.stripLeadingAndTrailingQuotes("""));
    }

    @Test
    public void testStripLeadingHyphens() {
        assertEquals("f", Util.stripLeadingHyphens("-f"));
        assertEquals("foo", Util.stripLeadingHyphens("--foo"));
        assertEquals("-foo", Util.stripLeadingHyphens("---foo"));
        assertNull(Util.stripLeadingHyphens(null));
    }
}
```
