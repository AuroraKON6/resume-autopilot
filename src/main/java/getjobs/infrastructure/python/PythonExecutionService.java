package getjobs.infrastructure.python;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class PythonExecutionService {

    @Value("${python.executable:${PYTHON_EXECUTABLE:}}")
    private String pythonExecutable;

    @Value("${python.scripts.dir:scripts}")
    private String scriptsDir;

    @Value("${python.timeout.seconds:900}")
    private int timeoutSeconds;

    @Value("${delivery.auto-submit:false}")
    private boolean autoSubmit;

    @Value("${delivery.dry-run:false}")
    private boolean dryRun;

    @Value("${delivery.max-steps:12}")
    private int maxSteps;

    public PythonResult executeScript(String scriptName, String... args) {
        log.info("Executing Python script: {} {}", scriptName, String.join(" ", args));

        String scriptPath = Paths.get(scriptsDir, scriptName).toString();
        List<String> command = new ArrayList<>();
        command.add(resolvePythonExecutable());
        command.add(scriptPath);
        for (String arg : args) {
            command.add(arg);
        }

        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.redirectErrorStream(true);
        processBuilder.directory(new File(System.getProperty("user.dir")));
        processBuilder.environment().put("PYTHONIOENCODING", "utf-8");
        processBuilder.environment().put("PYTHONUTF8", "1");

        try {
            Process process = processBuilder.start();

            StringBuilder output = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    log.info("[Python] {}", line);
                    output.append(line).append('\n');
                }
            }

            boolean completed = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            if (!completed) {
                process.destroyForcibly();
                return PythonResult.timeout(output.toString());
            }

            int exitCode = process.exitValue();
            if (exitCode == 0) {
                return PythonResult.success(output.toString());
            }
            return PythonResult.error(exitCode, output.toString());
        } catch (IOException e) {
            log.error("Failed to execute Python script: {}", e.getMessage());
            return PythonResult.error(-1, e.getMessage());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Python script execution was interrupted");
            return PythonResult.error(-1, "Execution interrupted");
        }
    }

    public PythonResult executeDelivery(String platform, String keyword, int count) {
        return executeDelivery(platform, keyword, count, autoSubmit, dryRun, null);
    }

    public PythonResult executeDelivery(
            String platform,
            String keyword,
            int count,
            boolean autoSubmit,
            boolean dryRun,
            String objective) {
        List<String> args = new ArrayList<>();
        args.add("--platform");
        args.add(platform);
        args.add("--keyword");
        args.add(keyword);
        args.add("--count");
        args.add(String.valueOf(count));
        args.add("--max-steps");
        args.add(String.valueOf(maxSteps));
        args.add("--objective");
        if (objective == null || objective.isBlank()) {
            args.add(String.format("Apply to up to %d suitable %s jobs on %s.", count, keyword, platform));
        } else {
            args.add(objective);
        }

        if (autoSubmit) {
            args.add("--auto-submit");
        }
        if (dryRun) {
            args.add("--dry-run");
        }

        return executeScript("mimo_ocr_agent.py", args.toArray(new String[0]));
    }

    public boolean checkPythonEnvironment() {
        try {
            ProcessBuilder processBuilder = new ProcessBuilder(resolvePythonExecutable(), "--version");
            processBuilder.redirectErrorStream(true);
            processBuilder.environment().put("PYTHONIOENCODING", "utf-8");
            Process process = processBuilder.start();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                log.info("Python version: {}", reader.readLine());
            }

            return process.waitFor() == 0;
        } catch (Exception e) {
            log.error("Python environment check failed: {}", e.getMessage());
            return false;
        }
    }

    private String resolvePythonExecutable() {
        if (pythonExecutable != null && !pythonExecutable.isBlank()) {
            return pythonExecutable;
        }

        File windowsVenvPython = Paths.get(
                System.getProperty("user.dir"), ".venv", "Scripts", "python.exe").toFile();
        if (windowsVenvPython.isFile()) {
            return windowsVenvPython.getAbsolutePath();
        }

        File unixVenvPython = Paths.get(
                System.getProperty("user.dir"), ".venv", "bin", "python").toFile();
        if (unixVenvPython.isFile()) {
            return unixVenvPython.getAbsolutePath();
        }

        return "python";
    }

    public boolean checkDependencies() {
        String[] requiredPackages = {"pyautogui", "PIL", "easyocr"};

        for (String pkg : requiredPackages) {
            try {
                ProcessBuilder processBuilder = new ProcessBuilder(
                        resolvePythonExecutable(), "-c", String.format("import %s; print('OK')", pkg));
                processBuilder.redirectErrorStream(true);
                processBuilder.environment().put("PYTHONIOENCODING", "utf-8");
                Process process = processBuilder.start();
                int exitCode = process.waitFor();

                if (exitCode != 0) {
                    log.error("Missing Python dependency: {}", pkg);
                    return false;
                }
            } catch (Exception e) {
                log.error("Python dependency check failed: {}", e.getMessage());
                return false;
            }
        }

        return true;
    }

    @Data
    public static class PythonResult {
        private boolean success;
        private int exitCode;
        private String output;
        private String error;
        private boolean timeout;

        public static PythonResult success(String output) {
            PythonResult result = new PythonResult();
            result.setSuccess(true);
            result.setExitCode(0);
            result.setOutput(output);
            return result;
        }

        public static PythonResult error(int exitCode, String error) {
            PythonResult result = new PythonResult();
            result.setSuccess(false);
            result.setExitCode(exitCode);
            result.setError(error);
            return result;
        }

        public static PythonResult timeout(String output) {
            PythonResult result = new PythonResult();
            result.setSuccess(false);
            result.setExitCode(-1);
            result.setOutput(output);
            result.setTimeout(true);
            result.setError("Execution timed out");
            return result;
        }
    }
}
