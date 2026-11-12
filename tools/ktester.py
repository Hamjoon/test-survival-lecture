"""KTester (Li et al., ICSE 2026) generation steps for lecture.ipynb.

The steps follow the public replication package (https://github.com/SYSUSELab/KTester, commit fce83f1):
  1. test class framework generation   (procedure/generate_code.py: generate_testclass_framework)
  2. multi-view test case design         (generate_case_then_code: condition, io, exception)
  3. test method transformation          (generate_case_then_code: gencode)
  4. test class integration              (editcode.TestClassUpdator in project-info-process.jar)
  5. test class refinement               (procedure/post_process.py: CodeRepairer.check_test_class)

What differs from the package:
  - The model is called through Gemini instead of the OpenAI SDK.
  - The project knowledge (context) is read from data/ktester/tasks.json. It was produced once with the
    package's own CodeSearcher on json-schema-validator 1.1.0 (see prep/), instead of being searched at run time.
  - Tests are compiled and run with the notebook's classpath (project classes, project dependencies, JUnit,
    Mockito), the same runner used for every group in this notebook.
The jar, the Java code editor (tools/code_analysis.py) and the prompt templates are the package's files, unchanged.
"""
import copy, json, os, pathlib, re, shutil, subprocess, sys

import lecture as L

KTESTER_COMMIT = "fce83f1a4b9aa3f1d54598b62027bc17bb585383"
RAW = f"https://raw.githubusercontent.com/SYSUSELab/KTester/{KTESTER_COMMIT}/code"
KT = L.WORK / "ktester-package"
TEMPLATES = L.REPO / "data/prompts/ktester"
TASKS = L.REPO / "data/ktester/tasks.json"
IMPORTS = L.REPO / "data/ktester/import_dict.json"

FIX_TRIES = 5            # paper: "We limited automatic repair iterations to 5"
TEMPERATURE = 0.5        # paper and package settings
CASE_VIEWS = [("condition", "condition4case_cov.j2"), ("io", "io4case_guide.j2"), ("exception", "exception4case_check.j2")]


# ------------------------------------------------------------------ setup
def setup():
    """Download the package's jar and Java code editor, install their Python dependencies."""
    KT.mkdir(parents=True, exist_ok=True)
    for f in ["Java/project-info-process.jar", "tools/code_analysis.py"]:
        dest = KT / pathlib.Path(f).name
        if not dest.exists():
            L.sh(f"curl -sSfL -o {dest} {RAW}/{f}", quiet=True)
    L.sh(f"{sys.executable} -m pip install -q tree-sitter==0.24.0 tree_sitter_java==0.23.5 JPype1==1.6.0 Jinja2", quiet=True)
    print("KTester 공개 저장소 파일:", sorted(p.name for p in KT.iterdir()))


def _jvm():
    import jpype
    if not jpype.isJVMStarted():
        jpype.startJVM(jpype.getDefaultJVMPath(), "-Xmx2g", classpath=[str(KT / "project-info-process.jar")])
    return jpype


def _editor():
    if str(KT) not in sys.path:
        sys.path.insert(0, str(KT))
    from code_analysis import JavaCodeEditor
    return JavaCodeEditor()


def _render(template, content):
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    return env.get_template(template).render(content)


def load_tasks():
    return json.loads(TASKS.read_text())


# ------------------------------------------------------------------ model output handling (tools/llm_api.py)
def filter_code(output):
    """Java code from a ```java block. An unfinished block loses its last @Test and gets closing braces."""
    m = re.findall(r"```(?:[jJ]ava)?\n+([\s\S]*?)\n```", output, re.DOTALL)
    if m:
        return m[0]
    m = re.findall(r"```(?:[jJ]ava)?\n+([\s\S]*?)$", output, re.DOTALL)
    if not m:
        return ""
    code = m[0]
    last = code.rfind("@Test")
    code = code[:last] if last != -1 else code
    if code.count("{") > code.count("}"):
        code += "}" * (code.count("{") - code.count("}"))
    return code


def parse_json(response):
    text = re.sub(r" //.*", "", response)
    m = re.findall(r"```(?:[jJ]son)?\n+([\s\S]*?)\n```", text, re.DOTALL)
    if m:
        text = max(m, key=len)
    return json.loads(text)


def check_class_name(code, test_class_name):
    """Rename the generated class to the expected test class name (post_process.check_class_name)."""
    found = re.findall(r"class ([\w$/\s.]+)(<.*>)?( extends [\w]+)?", code)
    if found and found[0][0] != test_class_name:
        code = code.replace(found[0][0], test_class_name)
    return code


class FormattedTestcase:
    """Merge test case groups from the three views; skip a case whose inputs equal an existing one."""
    def __init__(self):
        self.group_cases = {}

    def merge(self, data):
        groups = []
        def walk(x):
            if isinstance(x, dict):
                if isinstance(x.get("cases"), list) and x["cases"]:
                    groups.append(x)
                else:
                    for v in x.values():
                        walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(data)
        for g in groups:
            name = g.get("group", "unnamed")
            exist = self.group_cases.setdefault(name, [])
            for case in g["cases"]:
                same = any(len(case.get("input", [])) == len(e.get("input", [])) and
                           all(a.get("parameter") == b.get("parameter") and a.get("value") == b.get("value")
                               for a, b in zip(case.get("input", []), e.get("input", [])))
                           for e in exist)
                if not same:
                    exist.append(case)

    def to_list(self):
        return [{"group": g, "cases": c} for g, c in self.group_cases.items()]

    def __str__(self):
        return str(self.to_list())

    def count(self):
        return sum(len(c) for c in self.group_cases.values())


# ------------------------------------------------------------------ compile and run one test class
class Runner:
    """Compile one generated test class and run it, as JavaRunner/CodeRepairer do in the package."""
    def __init__(self, task, t_cp, work):
        self.task = task
        self.fqcn = task["test-class"]
        self.name = self.fqcn.split(".")[-1]
        self.src = work / "src" / pathlib.Path(*self.fqcn.split(".")[:-1]) / f"{self.name}.java"
        self.out = work / "classes"
        self.cp = [L.JSV / "target/classes"] + list(t_cp) + L.TEST_LIBS

    def write(self, code):
        self.src.parent.mkdir(parents=True, exist_ok=True)
        self.src.write_text(code)

    def compile(self):
        shutil.rmtree(self.out, ignore_errors=True)
        self.out.mkdir(parents=True)
        r = subprocess.run(["javac", "-nowarn", "-encoding", "UTF-8", "-d", str(self.out),
                            "-cp", os.pathsep.join(map(str, self.cp)), str(self.src)], text=True, capture_output=True)
        return r.returncode == 0, r.stderr

    def _launch(self, extra, timeout):
        cmd = ["java", "-jar", L.LAUNCHER, "--disable-banner", "--disable-ansi-colors", "--fail-if-no-tests",
               "--class-path", os.pathsep.join(map(str, [self.out] + self.cp)), "--select-class", self.fqcn] + extra
        return subprocess.run(cmd, cwd=L.JSV, text=True, capture_output=True, timeout=timeout, errors="ignore")

    def run(self, timeout=120):
        try:
            r = self._launch([], timeout)
        except subprocess.TimeoutExpired:
            return False, f"Time takes too long while executing test class {self.fqcn}"
        info = f"{r.stderr}\n{r.stdout}"
        return (r.returncode == 0 or bool(re.findall(r"([0-9]+) tests started", info))), info

    def run_verbose(self, timeout=60):
        try:
            r = self._launch(["--details", "verbose"], timeout)
            return f"{r.stderr}\n{r.stdout}"
        except subprocess.TimeoutExpired as e:
            return f"{e.stderr or ''}\n{e.stdout or ''}"

    def compile_and_execute(self):
        """Returns (state, feedback, pass rate). state: pass | compilation | execution."""
        ok, err = self.compile()
        if not ok:
            return "compilation", err, -2.0
        ok, info = self.run()
        rate = -1.0
        if ok:
            try:
                started = int(re.findall(r"([0-9]+) tests started", info)[0])
                passed = int(re.findall(r"([0-9]+) tests successful", info)[0])
                if started > 0:
                    rate = passed / started
            except Exception:
                pass
        if not ok or rate < 0.9:
            return "execution", info, rate
        return "pass", "", rate


# ------------------------------------------------------------------ refinement (post_process.CodeRepairer)
def parse_compile_feedback(feedback, src):
    """[(line, message, rule)] for rule repair and [(line, message)] for LLM repair."""
    rule, llm = [], []
    for part in feedback.split(f"{src}:"):
        if ": error: " not in part:
            continue
        head, msg = part.split(": error: ", 1)
        try:
            line = int(head) - 1
        except ValueError:
            continue
        if "cannot find symbol" in msg:
            rule.append((line, msg, "unresolved"))
        elif "unreported exception" in msg:
            rule.append((line, msg, "exception"))
        elif msg.startswith("class") and "is already defined" in msg:
            rule.append((line, msg, "inner_class"))
        llm.append((line, msg))
    return rule, llm


def repair_by_rules(code, errors, import_dict):
    """Add missing imports, drop broken imports, declare exceptions, merge duplicate inner classes."""
    ed = _editor()
    ed.parse(code)
    remove, add, exc, inner = [], set(), [], False
    for line, msg, kind in errors:
        if kind == "unresolved":
            g = re.findall(r"symbol:\s+(class|variable) (.*)", msg)
            if g:
                add.update(import_dict.get(g[0][1].strip(), []))
            if "import " in msg:
                remove.append(line)
        elif kind == "exception":
            exc.append(line)
        elif kind == "inner_class":
            inner = True
    if exc:
        ed.add_exception(exc)
    if remove:
        ed.remove_lines(remove)
    if add:
        ed.add_imports(list(add))
    new = ed.get_code()
    if inner:
        new = str(_jvm().JClass("editcode.TestClassSterilizer").main([new, "inner_class"]))
    return new


def check_timeout_cases(runner, code):
    """Remove the test method that was running when the class timed out."""
    for line in reversed(runner.run_verbose().splitlines()):
        if line.startswith("| | +-- "):
            name = line.replace("| | +-- ", "").split("(")[0]
            ed = _editor()
            ed.parse(code)
            start, end, names = ed.get_test_case_position()
            if name in names:
                i = names.index(name)
                ed.remove_lines([start[i], end[i]])          # as in the package
                return ed.get_code()
    return code


def clean_error_cases(errors, code):
    """Comment out the test methods that still contain compile errors."""
    ed = _editor()
    ed.parse(code)
    start, end, _ = ed.get_test_case_position()
    lines = [line for line, _ in errors]
    for line in lines.copy():
        for i in range(len(start)):
            if start[i] <= line <= end[i]:
                lines.append([start[i], end[i]])
                break
    ed.comment_code(lines)
    return ed.get_code()


# ------------------------------------------------------------------ one focal method
def generate_one(client, model, task, t_cp, log_dir):
    """Run the five steps for one focal method. Returns the final test class and a summary."""
    calls = {"framework": 0, "case design": 0, "transformation": 0, "repair": 0}
    log_dir.mkdir(parents=True, exist_ok=True)
    def ask(step, prompt, json_mode=False):
        calls[step] += 1
        n = sum(calls.values())
        (log_dir / f"{n:02d}-{step.replace(' ', '_')}-prompt.md").write_text(prompt)
        text = L.call_llm(client, model, prompt, temperature=TEMPERATURE, json_mode=json_mode)
        (log_dir / f"{n:02d}-{step.replace(' ', '_')}-response.md").write_text(text)
        return text

    test_name = task["test-class"].split(".")[-1]
    focal_class = task["class"].split(".")[-1]

    # 1. test class framework generation
    prompt = _render("init_structure.j2", {"method_name": task["method-name"], "class_name": test_name,
                                           "class_code": task["class-code"], "package_name": task["package"],
                                           "context_dict": task["init_context"]})
    init_class = check_class_name(filter_code(ask("framework", prompt)), test_name)

    # 2. multi-view test case design (condition branch, functionality, exception)
    cases = FormattedTestcase()
    content = {"method_name": task["method-name"], "class_name": focal_class,
               "class_code": task["class-code"], "context_dict": task["usage_context"]}
    for _, template in CASE_VIEWS:
        prompt = _render(template, content).replace("<cases_json>", str(cases))
        try:
            cases.merge(parse_json(ask("case design", prompt, json_mode=True)))
        except Exception as e:
            print(f"    케이스 JSON을 읽지 못함({template}): {type(e).__name__}")

    # 3. test method transformation
    prompt = _render("gencode_from_case.j2", content)
    prompt = prompt.replace("<initial_class>", init_class).replace("<cases_json>", str(cases))
    code = filter_code(ask("transformation", prompt))

    # 4. test class integration (package jar)
    jvm = _jvm()
    updator = jvm.JClass("editcode.TestClassUpdator")
    try:
        code = str(updator.main([init_class.strip(), code.lstrip(), init_class.strip().splitlines()[0]]))
    except Exception as e:
        print(f"    integration 실패, 생성된 코드를 그대로 씀: {type(e).__name__}")

    # 5. test class refinement
    import_dict = json.loads(IMPORTS.read_text())
    runner = Runner(task, t_cp, L.WORK / "ktester-work" / task["id"])
    half = FIX_TRIES // 2
    versions, rates = [code], []
    runner.write(code)
    state, feedback, rate = runner.compile_and_execute()
    rates.append(rate)
    count = 0
    while state != "pass" and count < FIX_TRIES:
        if state == "compilation":
            rule, _ = parse_compile_feedback(feedback, runner.src)
            code = repair_by_rules(code, rule, import_dict)
            runner.write(code)
            state, feedback, rate = runner.compile_and_execute()
        if state != "pass":
            if state == "execution" and "Time takes too long" in feedback:
                code = check_timeout_cases(runner, code)
                runner.write(code)
                state, feedback, rate = runner.compile_and_execute()
                if state == "pass":
                    count += 1
                    versions.append(code)
                    rates.append(rate)
                    break
            prompt = _render("post_process.j2", {state: True, "code_to_fix": code, "feedback": feedback[:8000],
                                                 "context_dict": task["usage_context"]})
            fixed = filter_code(ask("repair", prompt))
            try:
                code = str(updator.main([code, fixed, "true", str(log_dir / "repair.tmp")]))
            except Exception:
                code = fixed or code
            runner.write(code)
            state, feedback, rate = runner.compile_and_execute()
            if state == "compilation" and count >= half:
                _, llm_errors = parse_compile_feedback(feedback, runner.src)
                commented = clean_error_cases(llm_errors, code)
                runner.write(commented)
                c_state, c_feedback, c_rate = runner.compile_and_execute()
                if c_rate > rate:
                    state, feedback, rate, code = c_state, c_feedback, c_rate, commented
        versions.append(code)
        rates.append(rate)
        count += 1
    best = max(rates)
    final = versions[rates.index(best)] if best >= 0 else versions[-1]
    return final, {"focal method": task["id"], "케이스": cases.count(), "호출": sum(calls.values()),
                   "수리 라운드": count, "최종 통과율": round(best, 2) if best >= 0 else best}


def generate_ktester(client, model, t_cp, use_saved=False, only=None):
    """Generate one test class per focal method. Final classes go to GEN/ktester/<class>/<id>.txt
    (as a java code block, so the same check as Ouedraogo can read them). Existing results are kept."""
    out = L.GEN / "ktester"
    if use_saved:
        shutil.copytree(L.REPO / "data/generated/ktester", out, dirs_exist_ok=True)
        print("저장된 결과를 불러왔습니다:", out)
        return []
    summaries = []
    for task in load_tasks():
        if only and task["id"] not in only:
            continue
        path = out / task["class"].split(".")[-1] / f"{task['id']}.txt"
        if path.exists():
            print(f"  {task['id']}: 이미 있음")
            continue
        final, summary = generate_one(client, model, task, t_cp, L.GEN / "ktester-log" / task["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"```java\n{final}\n```\n")
        summaries.append(summary)
        print(f"  {task['id']}: 호출 {summary['호출']}회, 케이스 {summary['케이스']}개, "
              f"수리 {summary['수리 라운드']}회, 통과율 {summary['최종 통과율']}")
    return summaries
