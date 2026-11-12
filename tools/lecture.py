"""Helper functions for lecture.ipynb.

The notebook calls these so that each cell stays short. Every function mirrors one step of the
weekly experiment: build production code, compile tests, run test methods, measure line coverage.
"""
import json, os, pathlib, re, shutil, subprocess, sys, xml.etree.ElementTree as ET

IN_COLAB = "google.colab" in sys.modules
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


JDK_URL = "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"
MAVEN_URL = "https://repo1.maven.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.tar.gz"


def install_java(force=False):
    """Download JDK 17 (Temurin) and Maven 3.9 as archives and unpack them (Colab only).
    This is faster than apt, which refreshes all package lists and installs many extra packages."""
    import time
    t0 = time.time()
    tools = WORK / "jdk-maven"
    if not IN_COLAB and not force:
        print("주의: 이 노트북은 Colab 기준입니다. 다른 환경에서는 JDK 17과 Maven이 미리 설치돼 있어야 합니다.")
    elif not (tools / "jdk").exists() or not (tools / "maven").exists():
        tools.mkdir(parents=True, exist_ok=True)
        for name, url in (("jdk", JDK_URL), ("maven", MAVEN_URL)):
            d = tools / name
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir()
            sh(f"curl -sSfL '{url}' | tar xz -C {d} --strip-components=1", quiet=True)
    if (tools / "jdk").exists():
        os.environ["JAVA_HOME"] = str(tools / "jdk")
        os.environ["PATH"] = f"{tools / 'jdk'}/bin:{tools / 'maven'}/bin:" + os.environ["PATH"]
    print(sh("java -version 2>&1 | grep -i 'version'", quiet=True))
    print(sh("mvn -v 2>&1 | grep -i 'apache maven'", quiet=True))
    print(f"({time.time() - t0:.0f}초)")


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
    subprocess.run(["java", "-jar", JACOCO_CLI, "report", str(jacoco_exec), "--classfiles", str(classes_dir),
                    "--sourcefiles", str(source_dir), "--xml", str(xml_path)], check=True, capture_output=True)
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


def call_llm(client, model, prompt, temperature=0.7, max_tokens=16384, min_interval=5.0, tries=5, json_mode=False):
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
                config=types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens,
                                                   response_mime_type="application/json" if json_mode else None))
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
    looks like a JUnit test (has @Test, @ParameterizedTest, @TestFactory or @RepeatedTest). Markdown fence lines are dropped. Returns None if nothing is found."""
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
                    if re.search(r"@(Test|ParameterizedTest|TestFactory|RepeatedTest)\b", "\n".join(cur)):
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


# ------------------------------------------------------------------ survival over commits
COMMITS = [("#4", "5a94df7e914b90c185fb573b6e7a6b3fb5f2460b", "path 리팩토링"),
           ("#10", "7f1ec11b7a4b391577595e0d31d5825548c9a64f", "Draft 2020-12 지원, schema 조회 리팩토링"),
           ("#151", "e880dd0aa16a52098aa6eea25d688275ac1590d9", "2.x 대규모 리팩토링")]


def _artifact(jar):
    """Artifact name of a jar file name without its version (jackson-core-2.15.3.jar -> jackson-core)."""
    return re.sub(r"-\d.*$", "", os.path.basename(jar))


def _slug(name):
    """File-name-safe group name (Dev(scope) -> devscope, Ouédraogo -> ouedraogo)."""
    import unicodedata
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower())


def merge_classpath(commit_cp, t_cp):
    """The commit's dependencies, plus t's test-only dependencies the commit no longer declares."""
    have = {_artifact(j) for j in commit_cp}
    return list(commit_cp) + [j for j in t_cp if _artifact(j) not in have]


def build_commit(label, sha):
    """Check out a commit next to t (git worktree) and compile its production code."""
    d = WORK / "commits" / label.strip("#")
    if not (d / ".git").exists():
        shutil.rmtree(d, ignore_errors=True)
        sh(f"git -C {JSV} worktree add -f --detach {d} {sha}", quiet=True)
    return d, build_production(d)


def changed_lines(sha, file_rel):
    """Line numbers (in the commit's version) that the commit added or modified in one file."""
    out = sh(f"git -C {JSV} diff -U0 {sha}^ {sha} -- {file_rel}", quiet=True)
    lines = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", out, re.M):
        start, n = int(m[1]), int(m[2] if m[2] is not None else 1)
        lines.update(range(start, start + n))
    return lines


def _key(m):
    """A generated method is identified by its file and its name: two prompts can produce the same
    class and method name in different files."""
    return f"{m.get('dir', '')}|{m['method']}"


def run_groups_at(commit_dir, commit_cp, groups, alive, t_cp, exec_dir):
    """Run every group's alive methods at one commit, unchanged test sources from t.
    Returns {group: {key: pass|fail|compile-fail}}. JaCoCo data goes to exec_dir/<group>.exec."""
    prod = commit_dir / "target/classes"
    cp = merge_classpath(commit_cp, t_cp)
    exec_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for g, members in groups.items():
        ex = exec_dir / f"{_slug(g)}.exec"
        ex.unlink(missing_ok=True)
        todo = [m for m in members if _key(m) in alive[g]]
        res = {}
        if g == "Dev(scope)":
            dropped = compile_dev_tests(prod, cp, exec_dir / "dev-test-classes")
            ok = [m for m in todo if m["method"].split("#")[0] not in dropped]
            ran = run_methods([exec_dir / "dev-test-classes", prod] + cp, [m["method"] for m in ok], ex)
            for m in todo:
                res[_key(m)] = "compile-fail" if m not in ok else ran.get(m["method"], "fail")
        else:
            by_dir = {}
            for m in todo:
                by_dir.setdefault(m["dir"], []).append(m)
            for d, ms in by_dir.items():
                out = exec_dir / _slug(g) / pathlib.Path(d).name
                shutil.rmtree(out, ignore_errors=True)
                ok, _ = compile_java(pathlib.Path(d) / "src", out, [prod] + cp + TEST_LIBS)
                ran = run_methods([out, prod] + cp + TEST_LIBS, [m["method"] for m in ms], ex) if ok else {}
                for m in ms:
                    res[_key(m)] = ran.get(m["method"], "fail") if ok else "compile-fail"
        results[g] = res
    return results


def survive(groups, t_cp):
    """Cumulative survival at the three commits: a method that breaks once stays broken.
    Also changed-line coverage of the two target classes at each commit."""
    alive = {g: {_key(m) for m in ms} for g, ms in groups.items()}
    first_failure = {g: {} for g in groups}
    survival = [{"commit": "t", "날짜": "2023-12-15", **{g: len(a) for g, a in alive.items()}}]
    coverage = []
    for label, sha, desc in COMMITS:
        print(f"{label} {sha[:7]} {desc}: 빌드", end="", flush=True)
        d, cp = build_commit(label, sha)
        print(", 실행", end="", flush=True)
        run_dir = WORK / "commits" / f"run-{label.strip('#')}"
        res = run_groups_at(d, cp, groups, alive, t_cp, run_dir)
        for g, r in res.items():
            for k, st in r.items():
                if st != "pass":
                    alive[g].discard(k)
                    first_failure[g].setdefault(k, (label, "컴파일 실패" if st == "compile-fail" else "실행 실패"))
        date = sh(f"git -C {JSV} log -1 --format=%ad --date=short {sha}", quiet=True)
        survival.append({"commit": label, "날짜": date, **{g: len(a) for g, a in alive.items()}})
        # changed-line coverage: lines this commit added or modified in the target classes,
        # executed by the tests that entered this commit (alive before it)
        row, total = {"commit": label}, 0
        hits = {g: 0 for g in groups}
        for c in TARGETS:
            rel = f"src/main/java/{PKG_DIR}/{c}.java"
            if not (d / rel).exists():
                continue
            changed = changed_lines(sha, rel)
            executable = None
            for g in groups:
                ex = run_dir / f"{_slug(g)}.exec"
                lc = line_coverage(ex, d / "target/classes", d / "src/main/java") if ex.exists() else {}
                mine = {ln: v for (f, ln), v in lc.items() if f == f"{PKG_DIR}/{c}.java"}
                if executable is None and mine:
                    executable = changed & set(mine)
                hits[g] += sum(1 for ln in changed if mine.get(ln))
            total += len(executable or set())
        row["바뀐 실행 가능 줄"] = total
        for g in groups:
            row[g] = f"{hits[g]} ({hits[g] / total:.0%})" if total else "해당 없음"
        coverage.append(row)
        print(" 완료")
    return survival, coverage, first_failure


def survival_table(survival):
    """Counts with percentages of the count at t."""
    base = survival[0]
    rows = []
    for r in survival:
        rows.append({k: (f"{v} ({v / base[k]:.0%})" if k not in ("commit", "날짜") and base[k] else v) for k, v in r.items()})
    return rows


def failure_table(first_failure, groups):
    rows = []
    for g in groups:
        kinds = [k for _, k in first_failure[g].values()]
        rows.append({"집단": g, "깨진 테스트": len(kinds), "컴파일 실패": kinds.count("컴파일 실패"),
                     "실행 실패": kinds.count("실행 실패")})
    return rows
