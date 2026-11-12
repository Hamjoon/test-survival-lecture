"""Builds data/ktester/tasks.json and import_dict.json with the KTester replication package's own code.

Inputs:
  - KTester package checkout (https://github.com/SYSUSELab/KTester, or the Hamjoon/KTester fork branch
    tool/ktester-runtime, which only adds portability fixes): <ktester>/code
  - KTester project index of json-schema-validator 1.1.0 (json/, codegraph/, lucene/), built earlier with the
    package's PreProcessor and IndexBuilder: <ds>/project_index
  - The project at 1.1.0 laid out as the package expects: <ds>/projects/json-schema-validator
    (src/main, src/test-original/java, target/classes, libs/, dependencies.txt, pom.xml)

Steps (no model calls):
  1. List the public methods of the target classes from the index and write dataset_meta.json.
  2. Run the package's DatasetPrepare to get each focal method's class code and test class name.
  3. Run the package's CodeSearcher for the framework context and the usage context.
Methods of the nested class ValidationMessage.Builder are dropped: DatasetPrepare returns them without class code.

Usage: python3 prep/ktester_context.py <ktester checkout> <ds dir> <lecture repo>
"""
import json, sys

TARGETS = ["com.networknt.schema.SpecVersionDetector", "com.networknt.schema.ValidationMessage",
           "com.networknt.schema.ValidationMessage.Builder"]
KEEP = ["id", "package", "class", "test-class", "method-name", "source-path", "focal-method", "class-code"]


def main(ktester, ds, repo):
    import jpype
    code = f"{ktester}/code"
    index = json.load(open(f"{ds}/project_index/json/json-schema-validator.json"))
    methods = []
    for c in TARGETS:
        for name, sigs in index["source"][c]["methods"].items():
            for s in sigs:
                s = s["signature"] if isinstance(s, dict) else s
                if s.strip().startswith("public"):
                    methods.append(c + "." + name + s.split(name, 1)[1])
    json.dump([dict(project_name="json-schema-validator", put_path="projects/json-schema-validator",
                    method_name_to_idx={m: i for i, m in enumerate(methods)})], open(f"{ds}/dataset_meta.json", "w"))
    json.dump({"json-schema-validator": {"project-name": "json-schema-validator",
                                         "project-url": "projects/json-schema-validator", "focal-methods": []}},
              open(f"{ds}/dataset_info.json", "w"))
    jpype.startJVM(jpype.getDefaultJVMPath(), "-Xmx4g",
                   classpath=[f"{code}/Java/project-info-process.jar", f"{code}/Java/project-index-builder.jar"])
    jpype.JClass("DatasetPrepare").main([ds])
    sys.path.insert(0, code)
    from tools.code_search import CodeSearcher
    tasks = [t for t in json.load(open(f"{ds}/dataset_info.json"))["json-schema-validator"]["focal-methods"]
             if t["class-code"]]
    searcher = CodeSearcher(f"{ds}/projects/json-schema-validator", "json-schema-validator", f"{ds}/project_index", "10")
    out = []
    for t in tasks:
        row = {k: t[k] for k in KEEP}
        row["init_context"] = searcher.collect_construct_context(t["class"], t["method-name"], t["source-path"])
        row["usage_context"] = searcher.collect_usage_context(t["class"], t["method-name"])
        out.append(row)
    json.dump(out, open(f"{repo}/data/ktester/tasks.json", "w"), indent=1, ensure_ascii=False)
    json.dump(index["import_dict"], open(f"{repo}/data/ktester/import_dict.json", "w"), ensure_ascii=False)
    print(len(methods), "public methods,", len(out), "with class code")


if __name__ == "__main__":
    main(*sys.argv[1:4])
