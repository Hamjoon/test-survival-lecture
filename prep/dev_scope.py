"""Builds data/json-schema-validator/dev-scope.json (the Dev(scope) list used by the notebook).

How the list is made:
  1. At t (json-schema-validator 1.1.0) list every Dev test method in src/test/java
     (@Test, @ParameterizedTest, @TestFactory, @RepeatedTest).
  2. Run each method alone in its own JVM with the JaCoCo agent (tools/MethodRunner.java).
  3. Keep the methods that pass and execute at least one line of a target class.

Usage (after building the project at t with `mvn -DskipTests test-compile`):
  python3 prep/dev_scope.py <jsv checkout at t> <classpath file> <jar dir> <out dir>
  - classpath file: one line, ':'-separated; target/test-classes, target/classes, the project's
    dependencies without JUnit jars, the JUnit console standalone jar, and the compiled MethodRunner.
  - jar dir: holds org.jacoco.agent-*-runtime.jar and org.jacoco.cli-*-nodeps.jar.
"""
import json, pathlib, re, subprocess, sys, xml.etree.ElementTree as ET

TARGETS = ["com/networknt/schema/ValidationMessage.java", "com/networknt/schema/SpecVersionDetector.java"]
ANNOTATIONS = ("@Test", "@ParameterizedTest", "@TestFactory", "@RepeatedTest")
METHOD = re.compile(r"[\w<>\[\]?,\s]+\s(\w+)\s*\(")


def list_test_methods(test_root):
    """fqcn#method for every annotated test method. Skips annotation arguments
    (they may contain braces or parentheses, e.g. @CsvSource({...}))."""
    found = []
    for f in sorted(test_root.rglob("*.java")):
        lines = f.read_text().splitlines()
        pkg = next(re.match(r"package\s+([\w.]+);", l).group(1) for l in lines if l.startswith("package "))
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if any(re.match(re.escape(a) + r"\b", s) for a in ANNOTATIONS):
                depth = 0
                j = i
                while j < len(lines):
                    t = lines[j].strip()
                    if depth == 0 and not t.startswith("@") and t:
                        m = METHOD.match(t)
                        if m:
                            found.append(f"{pkg}.{f.stem}#{m.group(1)}")
                        break
                    depth += t.count("(") - t.count(")")
                    j += 1
                i = j
            i += 1
    return sorted(set(found))


def main(repo, cp_file, jar_dir, out):
    repo, jar_dir, out = pathlib.Path(repo), pathlib.Path(jar_dir), pathlib.Path(out)
    cp = pathlib.Path(cp_file).read_text().strip()
    agent = next(jar_dir.glob("org.jacoco.agent*.jar"))
    cli = next(jar_dir.glob("org.jacoco.cli*.jar"))
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    methods = list_test_methods(repo / "src/test/java")
    print(len(methods), "Dev test methods", flush=True)
    rows = []
    for i, spec in enumerate(methods):
        ex, xml = work / f"{i}.exec", work / f"{i}.xml"
        ex.unlink(missing_ok=True)
        r = subprocess.run(["java", f"-javaagent:{agent}=destfile={ex}", "-cp", cp, "MethodRunner", spec],
                           cwd=repo, capture_output=True, text=True, timeout=600)
        out_lines = [l for l in r.stdout.splitlines() if l.split("\t")[0] in ("pass", "fail", "skip", "absent")]
        status = out_lines[-1].split("\t")[0] if out_lines else "error"
        hits = {}
        if ex.exists():
            subprocess.run(["java", "-jar", str(cli), "report", str(ex), "--classfiles",
                            str(repo / "target/classes"), "--xml", str(xml)], capture_output=True)
            for p in ET.parse(xml).getroot().iter("package"):
                for sf in p.iter("sourcefile"):
                    path = p.get("name") + "/" + sf.get("name")
                    if path in TARGETS:
                        n = sum(1 for l in sf.iter("line") if int(l.get("ci")) > 0)
                        if n:
                            hits[path.split("/")[-1].removesuffix(".java")] = n
        rows.append({"method": spec, "status": status, "target_lines": hits})
        print(i, status, spec, hits, flush=True)
    (out / "dev-all.json").write_text(json.dumps(rows, indent=1))
    scope = [r for r in rows if r["status"] == "pass" and r["target_lines"]]
    (out / "dev-scope.json").write_text(json.dumps(
        {"t": "1.1.0", "targets": [t.split("/")[-1][:-5] for t in TARGETS],
         "dev_methods_total": len(rows),
         "dev_methods_pass": sum(r["status"] == "pass" for r in rows),
         "methods": scope}, indent=1))
    print(len(scope), "methods in Dev(scope)")


if __name__ == "__main__":
    main(*sys.argv[1:5])
