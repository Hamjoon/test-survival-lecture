"""Helper functions for lecture.ipynb.

The notebook calls these so that each cell stays short. Every function mirrors one step of the
weekly experiment: build production code, compile tests, run test methods, measure line coverage.
"""
import json, os, pathlib, re, shutil, subprocess, sys, xml.etree.ElementTree as ET

IN_COLAB = "google.colab" in sys.modules
JDK17 = "/usr/lib/jvm/java-17-openjdk-amd64"
REPO = pathlib.Path(__file__).resolve().parent.parent          # the lecture repository
WORK = pathlib.Path("/content/lecture" if IN_COLAB else os.path.expanduser("~/lecture-work"))
LIB = WORK / "lib"
HELPERS = WORK / "helpers"

# json-schema-validator settings
JSV = WORK / "json-schema-validator"
JSV_URL = "https://github.com/networknt/json-schema-validator.git"
T_TAG = "1.1.0"
PKG_DIR = "com/networknt/schema"
TARGETS = ["ValidationMessage", "SpecVersionDetector"]

LAUNCHER = JACOCO_AGENT = JACOCO_CLI = None
TEST_LIBS = []

TOOLS_POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>lecture</groupId><artifactId>tools</artifactId><version>1</version>
  <dependencies>
    <dependency><groupId>org.junit.platform</groupId><artifactId>junit-platform-console-standalone</artifactId><version>1.9.3</version></dependency>
    <dependency><groupId>junit</groupId><artifactId>junit</artifactId><version>4.13.2</version></dependency>
    <dependency><groupId>org.mockito</groupId><artifactId>mockito-core</artifactId><version>5.11.0</version></dependency>
    <dependency><groupId>org.mockito</groupId><artifactId>mockito-junit-jupiter</artifactId><version>5.11.0</version>
      <exclusions><exclusion><groupId>org.junit.jupiter</groupId><artifactId>*</artifactId></exclusion></exclusions></dependency>
    <dependency><groupId>org.jacoco</groupId><artifactId>org.jacoco.agent</artifactId><version>0.8.12</version><classifier>runtime</classifier></dependency>
    <dependency><groupId>org.jacoco</groupId><artifactId>org.jacoco.cli</artifactId><version>0.8.12</version><classifier>nodeps</classifier>
      <exclusions><exclusion><groupId>*</groupId><artifactId>*</artifactId></exclusion></exclusions></dependency>
  </dependencies>
</project>"""


# ------------------------------------------------------------------ shell and setup
def sh(cmd, check=True, quiet=False):
    """Run a shell command and return its output."""
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    out = (r.stdout + r.stderr).strip()
    if not quiet and out:
        print(out)
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {cmd}\n{out[-2000:]}")
    return out


def install_java():
    """Install JDK 17 and Maven on Colab and put JDK 17 first on PATH."""
    if not IN_COLAB:
        print("주의: 이 노트북은 Colab 기준입니다. 다른 환경에서는 JDK 17과 Maven이 미리 설치돼 있어야 합니다.")
    if IN_COLAB and not (os.path.isdir(JDK17) and shutil.which("mvn")):
        sh("apt-get update -qq && apt-get install -y -qq openjdk-17-jdk-headless maven > /dev/null", quiet=True)
    if os.path.isdir(JDK17):
        os.environ["JAVA_HOME"] = JDK17
        os.environ["PATH"] = f"{JDK17}/bin:" + os.environ["PATH"]
    print(sh("java -version 2>&1 | grep -i 'version'", quiet=True))
    print(sh("mvn -v 2>&1 | head -1", quiet=True))


def setup_tools():
    """Download the jars used to run tests (via a small pom.xml) and compile MethodRunner."""
    global LAUNCHER, JACOCO_AGENT, JACOCO_CLI, TEST_LIBS
    for d in [WORK, LIB, WORK / "tools", HELPERS]:
        d.mkdir(parents=True, exist_ok=True)
    (WORK / "tools" / "pom.xml").write_text(TOOLS_POM)
    sh(f"cd {WORK / 'tools'} && mvn -q dependency:copy-dependencies -DoutputDirectory={LIB}")
    jar = lambda prefix: str(next(LIB.glob(prefix + "*.jar")))
    LAUNCHER = jar("junit-platform-console-standalone")
    JACOCO_AGENT = jar("org.jacoco.agent")
    JACOCO_CLI = jar("org.jacoco.cli")
    TEST_LIBS = [str(p) for p in sorted(LIB.glob("*.jar")) if "jacoco" not in p.name]
    sh(f"javac -nowarn -d {HELPERS} -cp {LAUNCHER} {REPO / 'tools/MethodRunner.java'}")
    for p in sorted(LIB.glob("*.jar")):
        print(p.name)


# ------------------------------------------------------------------ compile, run, coverage
def compile_java(src_dir, out_dir, classpath):
    """javac every .java file under src_dir. Returns (ok, error text)."""
    files = [str(p) for p in pathlib.Path(src_dir).rglob("*.java")]
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["javac", "-nowarn", "-encoding", "UTF-8", "-d", str(out_dir),
                        "-cp", os.pathsep.join(map(str, classpath))] + files,
                       text=True, capture_output=True)
    return r.returncode == 0, r.stderr


def run_methods(classpath, methods, jacoco_exec=None, cwd=None):
    """Run test methods ("package.Class#method") with MethodRunner.
    Parameterized and dynamic invocations of one method count as one method:
    fail if any invocation fails. Returns {method: pass|fail|skip|absent}."""
    cmd = ["java"]
    if jacoco_exec:
        cmd.append(f"-javaagent:{JACOCO_AGENT}=destfile={jacoco_exec}")
    cmd += ["-cp", os.pathsep.join(list(map(str, classpath)) + [LAUNCHER, str(HELPERS)]), "MethodRunner"]
    cmd += list(methods)
    r = subprocess.run(cmd, cwd=cwd or JSV, text=True, capture_output=True, timeout=1800)
    res = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0] in ("pass", "fail", "skip", "absent"):
            res[parts[1]] = parts[0]          # other lines are output printed by the tests
    return res


def line_coverage(jacoco_exec, classes_dir, source_dir):
    """{(package/File.java, line): covered?} for every executable line, from a JaCoCo exec file."""
    xml_path = pathlib.Path(jacoco_exec).with_suffix(".xml")
    sh(f"java -jar {JACOCO_CLI} report {jacoco_exec} --classfiles {classes_dir} "
       f"--sourcefiles {source_dir} --xml {xml_path}", quiet=True)
    lines = {}
    for pkg in ET.parse(xml_path).getroot().iter("package"):
        for sf in pkg.iter("sourcefile"):
            for ln in sf.iter("line"):
                lines[(pkg.get("name") + "/" + sf.get("name"), int(ln.get("nr")))] = int(ln.get("ci")) > 0
    return lines


def demo():
    """Small example (data/demo): compile, run two tests with JaCoCo, report covered lines."""
    src = REPO / "data/demo"
    out = WORK / "demo"
    shutil.rmtree(out, ignore_errors=True)
    ok_p, _ = compile_java(src / "src", out / "classes", TEST_LIBS)
    ok_t, _ = compile_java(src / "test", out / "test-classes", TEST_LIBS + [out / "classes"])
    print("컴파일: production", ok_p, "/ test", ok_t)
    ex = out / "jacoco.exec"
    res = run_methods([out / "classes", out / "test-classes"] + TEST_LIBS,
                      ["shop.PriceCalculatorTest#appliesDiscount", "shop.PriceCalculatorTest#wrongExpectation"],
                      jacoco_exec=ex, cwd=out)
    print("실행 결과:", res)
    cov = line_coverage(ex, out / "classes", src / "src")
    calc = {ln: c for (f, ln), c in cov.items() if f.endswith("PriceCalculator.java")}
    print("PriceCalculator 실행된 줄:", sorted(ln for ln, c in calc.items() if c))
    print("PriceCalculator 실행 안 된 줄:", sorted(ln for ln, c in calc.items() if not c))


# ------------------------------------------------------------------ json-schema-validator
def checkout_t():
    """Clone json-schema-validator and check out t."""
    if not JSV.exists():
        sh(f"git clone -q --filter=blob:none {JSV_URL} {JSV}")
    sh(f"git -C {JSV} checkout -q {T_TAG}")
    print("t:", sh(f"git -C {JSV} log -1 --format='%h %ad %s' --date=short", quiet=True))


def build_production(src_root):
    """Compile production code with Maven. Returns the dependency classpath without JUnit jars
    (the console launcher brings its own JUnit)."""
    sh(f"cd {src_root} && mvn -q -DskipTests compile dependency:build-classpath -Dmdep.outputFile=cp.txt")
    jars = (pathlib.Path(src_root) / "cp.txt").read_text().strip().split(os.pathsep)
    return [j for j in jars if not re.search(r"junit-|opentest4j|apiguardian", os.path.basename(j))]


def outline(class_name, root=None):
    """Print the class and method declarations of a target class with line numbers."""
    path = pathlib.Path(root or JSV) / "src/main/java" / PKG_DIR / f"{class_name}.java"
    decl = re.compile(r"^\s*(public|protected|private)?\s*(static\s+)?(final\s+)?[\w<>\[\],.? ]+\s+\w+\s*\([^;]*$"
                      r"|^\s*public\s+class\s")
    lines = path.read_text().splitlines()
    print(f"{path.name} ({len(lines)}줄)")
    for n, line in enumerate(lines, 1):
        if decl.match(line) and not line.strip().startswith(("return", "if", "for", "while", "new", "else")):
            print(f"  {n:4d}  {line.strip().rstrip('{').strip()}")
    print()


def load_dev_scope():
    """The precomputed Dev(scope) list (made by prep/dev_scope.py)."""
    return json.loads((REPO / "data/json-schema-validator/dev-scope.json").read_text())


def compile_dev_tests(prod_classes, classpath, out_dir):
    """Compile t's Dev test sources (unchanged) against the given production classes.
    Files that fail are dropped and the rest is compiled again, until it compiles.
    Returns the dropped test classes: all their methods count as compile failures."""
    out_dir = pathlib.Path(out_dir)
    src = out_dir.parent / (out_dir.name + "-src")
    for d in (out_dir, src):
        shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(JSV / "src/test/resources", out_dir)            # test resources, as in pom.xml
    shutil.copytree(JSV / "src/test/suite", out_dir, dirs_exist_ok=True)
    shutil.copytree(JSV / "src/test/java", src)
    dropped = set()
    while True:
        ok, err = compile_java(src, out_dir, [prod_classes] + list(classpath) + [LAUNCHER])
        if ok:
            return dropped
        bad = set(re.findall(r"^(\S+\.java):\d+: error", err, re.M))
        if not bad:
            raise RuntimeError(err[-2000:])
        for b in bad:
            p = pathlib.Path(b)
            dropped.add(str(p.relative_to(src).with_suffix("")).replace("/", "."))
            p.unlink()


def target_coverage(jacoco_exec, classes_dir, src_dir):
    """{class: (covered lines, executable lines)} for the target classes."""
    cov = line_coverage(jacoco_exec, classes_dir, src_dir)
    out = {}
    for c in TARGETS:
        lines = [v for (f, _), v in cov.items() if f == f"{PKG_DIR}/{c}.java"]
        out[c] = (sum(lines), len(lines))
    return out


def print_coverage(cov):
    for c, (hit, total) in cov.items():
        print(f"  {c}: 실행 가능한 줄 {total}개 중 {hit}개 ({hit / total:.1%})")


# ------------------------------------------------------------------ LLM generation (shared)
GEN = WORK / "generated"
_last_call = [0.0]


def call_llm(client, model, prompt, temperature=0.7, max_tokens=16384, min_interval=5.0, tries=5):
    """One Gemini call. Waits between calls to stay under the free-tier per-minute limit.
    Retries when the per-minute limit is hit (HTTP 429) or the model is busy (HTTP 5xx, e.g.
    "high demand"), waiting 30, 60, 90 ... seconds."""
    import time
    from google.genai import types, errors
    for attempt in range(1, tries + 1):
        wait = _last_call[0] + min_interval - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        try:
            r = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens))
            return r.text or ""
        except (errors.ClientError, errors.ServerError) as e:
            code = getattr(e, "code", None)
            retry = code == 429 or (code is not None and code >= 500)
            if not retry or attempt == tries:
                raise
            reason = "호출 한도" if code == 429 else "모델 혼잡"
            print(f"    {reason}({code}). {30 * attempt}초 뒤 다시 시도합니다 ({attempt}/{tries - 1})")
            time.sleep(30 * attempt)


def save_responses(group):
    """Zip the raw responses of a group (to download from Colab)."""
    zip_path = shutil.make_archive(str(WORK / f"{group}-responses"), "zip", GEN / group)
    if IN_COLAB:
        from google.colab import files
        files.download(zip_path)
    print(zip_path)


# ------------------------------------------------------------------ Ouedraogo
TECHNIQUES = ["ZSL", "FSL", "CoT", "ToT", "GToT"]
PROMPTS = REPO / "data/prompts/ouedraogo"


def render_ouedraogo(technique, class_name, source):
    """Fill one of the five prompt templates with the class name and its full source."""
    values = {"{class_name}": class_name, "{source_code}": source,
              "{fewshot_example}": (PROMPTS / "fewshot_example.txt").read_text()}
    template = (PROMPTS / f"{technique}.txt").read_text()
    return "".join(values.get(p, p) for p in re.split(r"(\{class_name\}|\{source_code\}|\{fewshot_example\})", template))


def generate_ouedraogo(client, model, use_saved=False):
    """Ask the model for one test file per (target class, technique): 2 x 5 = 10 calls.
    Responses are saved under GEN/ouedraogo/<class>/<technique>.txt. Existing responses are kept,
    so the cell can be re-run after an interruption. use_saved=True copies the saved responses
    from the lecture repository instead of calling the model."""
    out = GEN / "ouedraogo"
    if use_saved:
        shutil.copytree(REPO / "data/generated/ouedraogo", out, dirs_exist_ok=True)
        print("저장된 응답을 불러왔습니다:", out)
        return
    for c in TARGETS:
        source = (JSV / "src/main/java" / PKG_DIR / f"{c}.java").read_text()
        for t in TECHNIQUES:
            path = out / c / f"{t}.txt"
            if path.exists():
                print(f"  {c} {t}: 이미 있음")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            text = call_llm(client, model, render_ouedraogo(t, c, source))
            path.write_text(text)
            print(f"  {c} {t}: 응답 {len(text):,}자")


# ------------------------------------------------------------------ checking generated tests at t
MARKER = re.compile(r"^\s*(?:\*\*|__|`)?###Test (START|END)#{2,3}(?:\*\*|__|`)?\s*$")


def extract_test(text):
    """Code between ###Test START## and ###Test END##; otherwise the longest fenced block that
    looks like a JUnit test. Markdown fence lines are dropped. Returns None if nothing is found."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if (m := MARKER.match(l)) and m[1] == "START"), None)
    end = next((i for i in range(start + 1, len(lines)) if (m := MARKER.match(lines[i])) and m[1] == "END"),
               None) if start is not None else None
    if start is not None and end is not None:
        body = lines[start + 1:end]
    else:
        blocks, cur = [], None
        for l in lines:
            if l.strip().startswith("```"):
                if cur is None:
                    cur = []
                else:
                    if "@Test" in "\n".join(cur):
                        blocks.append(cur)
                    cur = None
            elif cur is not None:
                cur.append(l)
        if not blocks:
            return None
        body = max(blocks, key=len)
    code = "\n".join(l for l in body if not l.strip().startswith("```")).strip()
    return code + "\n" if re.search(r"\bclass\s+\w+", code) else None


def _mask(code):
    """Blank out comments and string/char literals (keeps offsets) so braces can be matched."""
    return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)), code, flags=re.S)


def test_methods(code):
    """{method name: body without whitespace} for methods annotated with @Test (JUnit 4 or 5)."""
    masked = _mask(code)
    found = {}
    for m in re.finditer(r"@(Test|ParameterizedTest|TestFactory|RepeatedTest)\b", masked):
        d = re.compile(r"(\w+)\s*\([^)]*\)\s*(throws\s+[\w.,\s]+)?\{").search(masked, m.end())
        if not d:
            continue
        i, depth = d.end() - 1, 0
        for j in range(i, len(masked)):
            depth += {"{": 1, "}": -1}.get(masked[j], 0)
            if depth == 0:
                found.setdefault(d.group(1), re.sub(r"\s+", "", code[i:j + 1]))
                break
    return found


def check_generated_at_t(group, t_cp):
    """For every saved response of a group: extract the test file, compile it on its own against t,
    run its test methods once at t, and keep the passing ones. Methods whose body is identical to an
    earlier kept method are removed. Returns (one row per response, kept methods)."""
    import hashlib
    rows, kept, seen = [], [], set()
    base = WORK / "llm" / group
    shutil.rmtree(base, ignore_errors=True)
    order = lambda p: (p.parent.name, TECHNIQUES.index(p.stem) if p.stem in TECHNIQUES else 99, p.stem)
    for resp in sorted((GEN / group).rglob("*.txt"), key=order):
        key = f"{resp.parent.name}/{resp.stem}"
        row = {"응답": key, "추출": "", "컴파일": "", "메서드": 0, "t 통과": 0, "중복 제외 후": 0, "컴파일 오류(첫 줄)": ""}
        rows.append(row)
        code = extract_test(resp.read_text())
        if code is None:
            row["추출"] = "실패"
            continue
        row["추출"] = "성공"
        name = re.search(r"\bpublic\s+class\s+(\w+)", code) or re.search(r"\bclass\s+(\w+)", code)
        pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", code, re.M)
        fqcn = (pkg[1] + "." if pkg else "") + name[1]
        d = base / key.replace("/", "-")
        src = d / "src" / (pkg[1].replace(".", "/") if pkg else "") / f"{name[1]}.java"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(code)
        ok, err = compile_java(d / "src", d / "classes", [JSV / "target/classes"] + t_cp + TEST_LIBS)
        row["컴파일"] = "성공" if ok else "실패"
        methods = test_methods(code)
        row["메서드"] = len(methods)
        if not ok:
            lines = err.splitlines()
            i = next((k for k, l in enumerate(lines) if "error:" in l), None)
            msg = lines[i].split("error:", 1)[-1].strip() if i is not None else ""
            if i is not None and msg == "cannot find symbol":
                sym = next((l.split("symbol:", 1)[1].strip() for l in lines[i + 1:i + 4] if "symbol:" in l), "")
                msg = f"{msg}: {sym}"
            row["컴파일 오류(첫 줄)"] = msg[:90]
            continue
        res = run_methods([d / "classes", JSV / "target/classes"] + t_cp + TEST_LIBS,
                          [f"{fqcn}#{m}" for m in methods])
        passed = [m for m in methods if res.get(f"{fqcn}#{m}") == "pass"]
        row["t 통과"] = len(passed)
        for m in passed:
            h = hashlib.sha256(methods[m].encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            kept.append({"group": group, "response": key, "dir": str(d), "method": f"{fqcn}#{m}"})
            row["중복 제외 후"] += 1
    return rows, kept


def show_table(rows):
    """Display rows as a table (pandas when available)."""
    try:
        import pandas as pd
        from IPython.display import display
        display(pd.DataFrame(rows).fillna(""))
    except ImportError:
        for r in rows:
            print(r)
