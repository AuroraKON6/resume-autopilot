package getjobs.modules.getjobs.web;

import com.microsoft.playwright.Page;
import com.microsoft.playwright.Response;
import getjobs.common.enums.RecruitmentPlatformEnum;
import getjobs.common.util.*;
import getjobs.infrastructure.playwright.PlaywrightService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

/**
 * 反爬虫分析控制器
 * 提供反爬虫检测、JS捕获、页面观测等分析功能的API接口
 */
@RestController
@RequestMapping("/api/anti-crawler")
public class AntiCrawlerAnalysisController {

    private static final Logger log = LoggerFactory.getLogger(AntiCrawlerAnalysisController.class);

    private final PlaywrightService playwrightService;

    public AntiCrawlerAnalysisController(PlaywrightService playwrightService) {
        this.playwrightService = playwrightService;
    }

    /**
     * 启动反爬虫观测器 - 监控指定平台的页面行为
     * 日志输出到 logs/playwright-observers/{platform}_observer_{timestamp}.log
     */
    @PostMapping("/observer/start")
    public ResponseEntity<Map<String, Object>> startObserver(@RequestParam("platform") String platform) {
        try {
            RecruitmentPlatformEnum platformEnum = RecruitmentPlatformEnum.valueOf(platform.toUpperCase());
            Page page = playwrightService.getPage(platformEnum);
            if (page == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "平台页面未初始化"));
            }

            PlaywrightPageObserver observer = new PlaywrightPageObserver();
            observer.attachObservers(page, platformEnum);
            observer.attachAntiCrawlerAnalyzer(page, platformEnum);

            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "message", "已启动 " + platformEnum.getPlatformName() + " 反爬虫观测器",
                    "logDir", PlaywrightPageObserver.getLogDirectory()
            ));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", "无效的平台名称: " + platform));
        } catch (Exception e) {
            log.error("启动反爬虫观测器失败", e);
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 启用JS捕获 - 捕获指定平台加载的所有JS文件
     * 文件保存到 logs/anti-crawler-analysis/captured-js/{timestamp}/
     */
    @PostMapping("/js-capture/start")
    public ResponseEntity<Map<String, Object>> startJsCapture(
            @RequestParam("platform") String platform,
            @RequestParam(value = "domains", required = false, defaultValue = "") String domains) {
        try {
            RecruitmentPlatformEnum platformEnum = RecruitmentPlatformEnum.valueOf(platform.toUpperCase());

            JsCaptureManager manager;
            if (domains != null && !domains.trim().isEmpty()) {
                String[] domainArray = domains.split(",");
                manager = playwrightService.enableJsCaptureForDomains(domainArray);
            } else {
                manager = playwrightService.enableJsCapture();
            }

            if (manager == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "JS捕获启动失败，BrowserContext可能未初始化"));
            }

            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "message", "已启动JS捕获",
                    "captureDir", manager.getCaptureDir().toAbsolutePath().toString()
            ));
        } catch (Exception e) {
            log.error("启动JS捕获失败", e);
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 启用完整反爬虫对抗方案（观测器+导航守卫+JS分析）
     */
    @PostMapping("/defense/enable")
    public ResponseEntity<Map<String, Object>> enableDefense(
            @RequestParam("platform") String platform,
            @RequestParam("targetUrl") String targetUrl) {
        try {
            RecruitmentPlatformEnum platformEnum = RecruitmentPlatformEnum.valueOf(platform.toUpperCase());
            Page page = playwrightService.getPage(platformEnum);
            if (page == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "平台页面未初始化"));
            }

            PlaywrightPageObserver observer = new PlaywrightPageObserver();
            observer.enableAntiCrawlerDefense(page, platformEnum, targetUrl);

            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "message", "已启用 " + platformEnum.getPlatformName() + " 反爬虫对抗方案",
                    "targetUrl", targetUrl
            ));
        } catch (Exception e) {
            log.error("启用反爬虫对抗方案失败", e);
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 导航到指定URL并记录响应信息（用于分析反爬虫机制）
     * 会记录：响应状态码、Content-Type、响应头、响应体前500字符
     */
    @PostMapping("/analyze-url")
    public ResponseEntity<Map<String, Object>> analyzeUrl(
            @RequestParam("platform") String platform,
            @RequestParam("url") String url) {
        try {
            RecruitmentPlatformEnum platformEnum = RecruitmentPlatformEnum.valueOf(platform.toUpperCase());
            Page page = playwrightService.getPage(platformEnum);
            if (page == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "平台页面未初始化"));
            }

            log.info("开始分析URL: {}", url);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("url", url);
            result.put("platform", platformEnum.getPlatformName());

            // 导航并捕获响应
            Response response = page.navigate(url);
            if (response != null) {
                result.put("status", response.status());
                result.put("contentType", response.headerValue("content-type"));

                // 记录关键响应头
                Map<String, String> headers = new LinkedHashMap<>();
                Map<String, String> allHeaders = response.headers();
                for (Map.Entry<String, String> entry : allHeaders.entrySet()) {
                    String name = entry.getKey().toLowerCase();
                    if (name.contains("punish") || name.contains("security") || name.contains("captcha")
                            || name.contains("set-cookie") || name.contains("location")
                            || name.contains("server") || name.contains("x-")) {
                        headers.put(entry.getKey(), entry.getValue());
                    }
                }
                result.put("suspiciousHeaders", headers);

                // 获取响应体（前1000字符）
                try {
                    String body = response.text();
                    result.put("bodyLength", body.length());
                    result.put("bodyPreview", body.substring(0, Math.min(1000, body.length())));
                    result.put("isHtml", body.contains("<html") || body.contains("<!DOCTYPE"));
                    result.put("isJson", body.trim().startsWith("{") || body.trim().startsWith("["));

                    // 检测反爬虫特征
                    Map<String, Boolean> features = new LinkedHashMap<>();
                    features.put("hasPunishCache", body.contains("punish") || body.contains("cache=hit"));
                    features.put("hasCaptcha", body.contains("captcha") || body.contains("验证码"));
                    features.put("hasSecurityCheck", body.contains("security") || body.contains("安全检查"));
                    features.put("hasRedirect", body.contains("location.replace") || body.contains("location.href"));
                    features.put("hasWebdriverCheck", body.contains("webdriver"));
                    features.put("hasAboutBlank", body.contains("about:blank"));
                    result.put("antiCrawlerFeatures", features);
                } catch (Exception e) {
                    result.put("bodyError", "无法读取响应体: " + e.getMessage());
                }
            } else {
                result.put("error", "导航失败，无响应");
            }

            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("分析URL失败", e);
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 获取已捕获的JS文件列表和观测器日志
     */
    @GetMapping("/reports")
    public ResponseEntity<Map<String, Object>> getReports() {
        Map<String, Object> result = new LinkedHashMap<>();

        // JS捕获目录
        try {
            Path captureBaseDir = Paths.get("logs/anti-crawler-analysis/captured-js");
            if (Files.exists(captureBaseDir)) {
                List<String> captureDirs = new ArrayList<>();
                try (var stream = Files.list(captureBaseDir)) {
                    stream.filter(Files::isDirectory)
                            .sorted(Comparator.reverseOrder())
                            .limit(5)
                            .forEach(dir -> captureDirs.add(dir.getFileName().toString()));
                }
                result.put("jsCaptureDirs", captureDirs);
            }
        } catch (Exception e) {
            result.put("jsCaptureError", e.getMessage());
        }

        // 观测器日志目录
        try {
            Path observerDir = Paths.get(PlaywrightPageObserver.getLogDirectory());
            if (Files.exists(observerDir)) {
                List<String> logFiles = new ArrayList<>();
                try (var stream = Files.list(observerDir)) {
                    stream.filter(p -> p.toString().endsWith(".log"))
                            .sorted(Comparator.reverseOrder())
                            .limit(10)
                            .forEach(p -> logFiles.add(p.getFileName().toString()));
                }
                result.put("observerLogs", logFiles);
            }
        } catch (Exception e) {
            result.put("observerLogError", e.getMessage());
        }

        return ResponseEntity.ok(result);
    }

    /**
     * 分析51job搜索：先访问首页建立WAF cookie，再搜索
     * 策略：首页→等待WAF→搜索页→等待结果→检查页面内容
     */
    @PostMapping("/analyze-51job-search")
    public ResponseEntity<Map<String, Object>> analyze51jobSearch(
            @RequestParam("keyword") String keyword,
            @RequestParam(value = "jobArea", required = false, defaultValue = "030200") String jobArea) {
        Page analysisPage = null;
        try {
            RecruitmentPlatformEnum platformEnum = RecruitmentPlatformEnum.JOB_51;
            Page mainPage = playwrightService.getPage(platformEnum);
            if (mainPage == null) {
                return ResponseEntity.badRequest().body(Map.of("error", "51job页面未初始化"));
            }

            Map<String, Object> result = new LinkedHashMap<>();

            // 在同一BrowserContext中创建新页面（共享cookie）
            analysisPage = mainPage.context().newPage();
            analysisPage.setDefaultTimeout(30000);

            // 第一步：先访问51job首页，让WAF建立cookie
            try {
                analysisPage.navigate("https://www.51job.com/", new Page.NavigateOptions().setTimeout(20000));
                analysisPage.waitForLoadState(com.microsoft.playwright.options.LoadState.DOMCONTENTLOADED,
                        new Page.WaitForLoadStateOptions().setTimeout(10000));
                Thread.sleep(5000); // 等待WAF挑战JS执行
                result.put("homepageLoaded", true);
            } catch (Exception e) {
                result.put("homepageError", e.getMessage());
            }

            // 第二步：导航到搜索页面
            String searchUrl = "https://we.51job.com/pc/search?jobArea=" + jobArea + "&keyword=" +
                    java.net.URLEncoder.encode(keyword, java.nio.charset.StandardCharsets.UTF_8);
            result.put("searchUrl", searchUrl);

            try {
                analysisPage.navigate(searchUrl, new Page.NavigateOptions().setTimeout(20000));
                analysisPage.waitForLoadState(com.microsoft.playwright.options.LoadState.DOMCONTENTLOADED,
                        new Page.WaitForLoadStateOptions().setTimeout(15000));
            } catch (Exception e) {
                result.put("searchNavError", e.getMessage());
            }

            // 等待WAF挑战JS执行
            Thread.sleep(8000);

            // 关键步骤：reload页面，让搜索API在WAF cookie已设置后重新发起
            try {
                analysisPage.reload(new Page.ReloadOptions()
                        .setWaitUntil(com.microsoft.playwright.options.WaitUntilState.DOMCONTENTLOADED));
            } catch (Exception e) {
                result.put("reloadError", e.getMessage());
            }

            // 等待reload后的页面渲染
            Thread.sleep(10000);

            // 第三步：检查页面最终状态
            result.put("currentUrl", analysisPage.url());
            try { result.put("pageTitle", analysisPage.title()); } catch (Exception ignored) {}

            // 通过JS检查页面内容
            try {
                String pageInfo = analysisPage.evaluate(
                        "(() => {" +
                        "  const body = document.body ? document.body.innerText : '';" +
                        "  const hasSalary = body.includes('元/月') || body.includes('千/月') || body.includes('万/月') || body.includes('面议') || /\\d+[千万]-\\d+[万千元]/.test(body);" +
                        "  const keywordLower = '" + keyword.toLowerCase() + "';" +
                        "  const hasKeywordJobs = body.toLowerCase().includes(keywordLower) && hasSalary;" +
                        "  const hasRecommended = body.includes('推荐职位') || body.includes('热门职位') || body.includes('小而美企业');" +
                        "  const hasWaf = body.includes('aliyun_waf') || body.includes('punish');" +
                        "  return JSON.stringify({" +
                        "    hasKeywordJobs: hasKeywordJobs," +
                        "    hasRecommended: hasRecommended," +
                        "    hasWaf: hasWaf," +
                        "    bodyLength: body.length," +
                        "    bodyPreview: body.substring(0, 1000)" +
                        "  });" +
                        "})()"
                ).toString();

                com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
                @SuppressWarnings("unchecked")
                Map<String, Object> pageInfoMap = mapper.readValue(pageInfo, Map.class);
                result.put("pageInfo", pageInfoMap);

                boolean hasKeywordJobs = Boolean.TRUE.equals(pageInfoMap.get("hasKeywordJobs"));
                boolean hasRecommended = Boolean.TRUE.equals(pageInfoMap.get("hasRecommended"));
                boolean hasWaf = Boolean.TRUE.equals(pageInfoMap.get("hasWaf"));

                if (hasKeywordJobs) {
                    result.put("success", true);
                    result.put("message", "搜索成功！页面有 '" + keyword + "' 相关的职位搜索结果");
                } else if (hasRecommended) {
                    result.put("success", false);
                    result.put("message", "页面只显示默认推荐职位，搜索API被WAF拦截（搜索结果未加载）");
                } else if (hasWaf) {
                    result.put("success", false);
                    result.put("message", "WAF挑战仍在进行中");
                } else {
                    result.put("success", false);
                    result.put("message", "页面无搜索结果");
                }
            } catch (Exception e) {
                result.put("pageInfoError", e.getMessage());
            }

            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("分析51job搜索页面失败", e);
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        } finally {
            if (analysisPage != null) {
                try { analysisPage.close(); } catch (Exception ignored) {}
            }
        }
    }

    /**
     * 读取指定的观测器日志内容
     */
    @GetMapping("/reports/observer-log")
    public ResponseEntity<Map<String, Object>> getObserverLog(@RequestParam("fileName") String fileName) {
        try {
            Path logPath = Paths.get(PlaywrightPageObserver.getLogDirectory(), fileName);
            if (!Files.exists(logPath)) {
                return ResponseEntity.badRequest().body(Map.of("error", "日志文件不存在: " + fileName));
            }

            String content = Files.readString(logPath);
            return ResponseEntity.ok(Map.of(
                    "fileName", fileName,
                    "content", content,
                    "size", content.length()
            ));
        } catch (Exception e) {
            log.error("读取日志文件失败", e);
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }
}
