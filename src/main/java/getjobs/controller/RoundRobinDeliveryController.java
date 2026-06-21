package getjobs.controller;

import getjobs.infrastructure.python.PythonExecutionService;
import getjobs.modules.getjobs.service.RoundRobinDeliveryService;
import getjobs.modules.getjobs.service.RoundRobinResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/delivery")
@RequiredArgsConstructor
public class RoundRobinDeliveryController {

    private final RoundRobinDeliveryService roundRobinDeliveryService;
    private final PythonExecutionService pythonExecutionService;

    @PostMapping("/round-robin")
    public ResponseEntity<Map<String, Object>> executeRoundRobinDelivery(
            @RequestParam(name = "keyword", defaultValue = "java") String keyword,
            @RequestParam(name = "count", defaultValue = "5") int count,
            @RequestParam(name = "autoSubmit", defaultValue = "false") boolean autoSubmit,
            @RequestParam(name = "dryRun", defaultValue = "false") boolean dryRun,
            @RequestParam(name = "objective", required = false) String objective) {
        log.info("Received round-robin delivery request: keyword={}, count={}, autoSubmit={}, dryRun={}",
                keyword, count, autoSubmit, dryRun);

        try {
            RoundRobinResult result = roundRobinDeliveryService.executeRoundRobinDelivery(
                    keyword, count, autoSubmit, dryRun, objective);

            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("keyword", result.getKeyword());
            response.put("totalDelivered", result.getTotalDelivered());
            response.put("totalRounds", result.getTotalRounds());
            response.put("startTime", result.getStartTime());
            response.put("endTime", result.getEndTime());
            response.put("platformResults", result.getPlatformResults());
            response.put("autoSubmit", autoSubmit);
            response.put("dryRun", dryRun);

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Round-robin delivery failed", e);

            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("message", "Round-robin delivery failed: " + e.getMessage());
            return ResponseEntity.internalServerError().body(response);
        }
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getDeliveryStatus() {
        Map<String, Object> response = new HashMap<>();

        boolean pythonReady = pythonExecutionService.checkPythonEnvironment();
        boolean depsReady = pythonExecutionService.checkDependencies();

        response.put("success", true);
        response.put("pythonReady", pythonReady);
        response.put("dependenciesReady", depsReady);
        response.put("ready", pythonReady && depsReady);

        return ResponseEntity.ok(response);
    }
}
