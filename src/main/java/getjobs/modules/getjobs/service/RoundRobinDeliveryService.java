package getjobs.modules.getjobs.service;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import getjobs.common.enums.RecruitmentPlatformEnum;
import getjobs.infrastructure.python.PythonExecutionService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Date;

@Slf4j
@Service
@RequiredArgsConstructor
public class RoundRobinDeliveryService {

    private final PythonExecutionService pythonExecutionService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final int DEFAULT_JOBS_PER_PLATFORM = 5;

    private static final PlatformTarget[] PLATFORM_TARGETS = {
            new PlatformTarget("boss", RecruitmentPlatformEnum.BOSS_ZHIPIN),
            new PlatformTarget("51job", RecruitmentPlatformEnum.JOB_51),
            new PlatformTarget("zhilian", RecruitmentPlatformEnum.ZHILIAN_ZHAOPIN),
            new PlatformTarget("liepin", RecruitmentPlatformEnum.LIEPIN)
    };

    public RoundRobinResult executeRoundRobinDelivery(String keyword) {
        return executeRoundRobinDelivery(keyword, DEFAULT_JOBS_PER_PLATFORM, false, false, null);
    }

    public RoundRobinResult executeRoundRobinDelivery(
            String keyword,
            int countPerPlatform,
            boolean autoSubmit,
            boolean dryRun,
            String objective) {
        int safeCount = Math.max(1, Math.min(countPerPlatform, 20));
        String agentObjective = buildObjective(keyword, safeCount, objective);

        RoundRobinResult result = new RoundRobinResult();
        result.setStartTime(new Date());
        result.setKeyword(keyword);

        int totalDelivered = 0;
        for (PlatformTarget target : PLATFORM_TARGETS) {
            log.info("Starting Mimo OCR agent for platform={}, keyword={}, count={}, autoSubmit={}, dryRun={}",
                    target.platformKey(), keyword, safeCount, autoSubmit, dryRun);

            PlatformResult platformResult = new PlatformResult();
            platformResult.setPlatformName(target.platformEnum().getPlatformName());

            try {
                PythonExecutionService.PythonResult pyResult = pythonExecutionService.executeDelivery(
                        target.platformKey(), keyword, safeCount, autoSubmit, dryRun, agentObjective);

                PythonOutput output = parsePythonOutput(pyResult.isSuccess() ? pyResult.getOutput() : pyResult.getError());
                platformResult.setAttempted(output.getAttempted() > 0 ? output.getAttempted() : safeCount);
                platformResult.setDelivered(output.getDelivered());
                platformResult.setSkipped(output.getSkipped());
                platformResult.setNeedsUserAction(output.isNeedsUserAction());

                if (!pyResult.isSuccess()) {
                    log.warn("Mimo OCR agent failed for platform={}, exitCode={}, error={}",
                            target.platformKey(), pyResult.getExitCode(), output.getError());
                    if (output.getAttempted() <= 0) {
                        platformResult.setAttempted(safeCount);
                        platformResult.setSkipped(safeCount);
                        platformResult.setNeedsUserAction(true);
                    }
                }

                totalDelivered += platformResult.getDelivered();
                log.info("Finished platform={}, delivered={}/{}",
                        target.platformKey(), platformResult.getDelivered(), platformResult.getAttempted());
            } catch (Exception e) {
                log.error("Mimo OCR agent exception for platform={}: {}", target.platformKey(), e.getMessage(), e);
                platformResult.setAttempted(safeCount);
                platformResult.setDelivered(0);
                platformResult.setSkipped(safeCount);
                platformResult.setNeedsUserAction(true);
            }

            result.getPlatformResults().add(platformResult);
            if (platformResult.isNeedsUserAction()) {
                log.info("Stopping round robin because platform={} needs user action", target.platformKey());
                break;
            }
        }

        result.setEndTime(new Date());
        result.setTotalDelivered(totalDelivered);
        result.setTotalRounds(1);
        return result;
    }

    private String buildObjective(String keyword, int countPerPlatform, String objective) {
        if (objective != null && !objective.isBlank()) {
            return objective;
        }
        return "Apply to up to " + countPerPlatform + " suitable jobs for keyword '" + keyword
                + "'. Use OCR text and screenshot context to decide the next safe step. "
                + "Skip unsuitable jobs and stop for login, verification, captcha, or unclear final submission.";
    }

    private PythonOutput parsePythonOutput(String output) {
        try {
            return objectMapper.readValue(extractJson(output), PythonOutput.class);
        } catch (Exception e) {
            log.warn("Failed to parse Python JSON output: {}", e.getMessage());
            PythonOutput fallback = new PythonOutput();
            fallback.setSuccess(false);
            fallback.setAttempted(0);
            fallback.setDelivered(0);
            fallback.setSkipped(0);
            fallback.setNeedsUserAction(true);
            fallback.setError(output);
            return fallback;
        }
    }

    private String extractJson(String output) {
        if (output == null || output.isBlank()) {
            return "{}";
        }
        int start = output.indexOf('{');
        int end = output.lastIndexOf('}');
        if (start >= 0 && end > start) {
            return output.substring(start, end + 1);
        }
        return "{}";
    }

    private record PlatformTarget(String platformKey, RecruitmentPlatformEnum platformEnum) {
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PythonOutput {
        private boolean success;
        private String platform;
        private String keyword;
        private int attempted;
        private int delivered;
        private int skipped;
        private boolean needsUserAction;
        private String error;
        private double duration;
        private String timestamp;
    }
}
