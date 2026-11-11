import org.junit.platform.engine.TestExecutionResult;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.*;
import org.junit.platform.launcher.core.*;
import java.util.*;
import static org.junit.platform.engine.discovery.DiscoverySelectors.*;

/** Runs test methods selected by "fqcn#methodName" (no parameter types needed).
 *  Parameterized and dynamic invocations of one method are folded into one result:
 *  fail if any invocation failed, pass if any passed, skip otherwise.
 *  Prints one line per method: STATUS<TAB>fqcn#method */
public class MethodRunner {
    public static void main(String[] args) {
        Launcher launcher = LauncherFactory.create();
        for (String spec : args) {
            String cls = spec.substring(0, spec.indexOf('#'));
            String name = spec.substring(spec.indexOf('#') + 1);
            TestPlan plan = launcher.discover(LauncherDiscoveryRequestBuilder.request()
                    .selectors(selectClass(cls)).build());
            List<String> ids = new ArrayList<>();
            for (TestIdentifier root : plan.getRoots())
                for (TestIdentifier t : plan.getDescendants(root))
                    t.getSource().ifPresent(s -> {
                        if (s instanceof MethodSource && ((MethodSource) s).getMethodName().equals(name)
                                && ((MethodSource) s).getClassName().equals(cls))
                            ids.add(t.getUniqueId());
                    });
            if (ids.isEmpty()) { System.out.println("absent\t" + spec); continue; }
            final int[] count = new int[3]; // pass, fail, skip
            TestExecutionListener l = new TestExecutionListener() {
                public void executionFinished(TestIdentifier id, TestExecutionResult r) {
                    TestExecutionResult.Status s = r.getStatus();
                    if (s == TestExecutionResult.Status.FAILED) count[1]++;          // failed test or container
                    else if (!id.isTest()) return;
                    else if (s == TestExecutionResult.Status.SUCCESSFUL) count[0]++;
                    else count[2]++;                                                // aborted (assumption) = skip
                }
                public void executionSkipped(TestIdentifier id, String reason) { if (id.isTest()) count[2]++; }
            };
            LauncherDiscoveryRequestBuilder b = LauncherDiscoveryRequestBuilder.request();
            for (String id : ids) b.selectors(selectUniqueId(id));
            launcher.execute(b.build(), l);
            String st = count[1] > 0 ? "fail" : count[0] > 0 ? "pass" : "skip";
            System.out.println(st + "\t" + spec);
        }
    }
}
