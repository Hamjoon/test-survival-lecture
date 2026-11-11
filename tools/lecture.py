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
TARGETS = ["AnyOfValidator", "OneOfValidator"]

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
        if "\t" in line:
            st, m = line.split("\t")
            res[m] = st
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
    shutil.copytree(JSV / "src/test/resources", out_dir)
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
