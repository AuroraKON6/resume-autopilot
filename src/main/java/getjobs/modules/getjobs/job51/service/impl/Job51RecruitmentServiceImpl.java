package getjobs.modules.getjobs.job51.service.impl;

import com.github.openjson.JSONArray;
import com.github.openjson.JSONObject;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.Cookie;
import getjobs.common.enums.RecruitmentPlatformEnum;
import getjobs.common.dto.ConfigDTO;
import getjobs.common.util.PageHealthChecker;
import getjobs.infrastructure.playwright.PlaywrightService;
import getjobs.modules.getjobs.boss.dto.JobDTO;
import getjobs.modules.getjobs.job51.service.playwright.Job51ApiMonitorService;
import getjobs.modules.getjobs.job51.service.Job51ElementLocators;
import getjobs.modules.getjobs.service.JobFilterService;
import getjobs.repository.JobRepository;
import getjobs.repository.UserProfileRepository;
import getjobs.repository.entity.ConfigEntity;
import getjobs.repository.entity.JobEntity;
import getjobs.modules.getjobs.service.AbstractRecruitmentService;
import getjobs.modules.getjobs.service.ConfigService;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 51job招聘服务实现
 *
 * @author loks666
 *         项目链接: <a href=
 *         "https://github.com/loks666/get_jobs">https://github.com/loks666/get_jobs</a>
 */
@Slf4j
@Service
public class Job51RecruitmentServiceImpl extends AbstractRecruitmentService {

    private static final String HOME_URL = RecruitmentPlatformEnum.JOB_51.getHomeUrl();
    private static final String LOGIN_URL = "https://login.51job.com/login.php";
    private static final String SEARCH_JOB_URL = "https://we.51job.com/pc/search?";

    private final PlaywrightService playwrightService;
    private final Job51ApiMonitorService job51ApiMonitorService;
    private final JobFilterService jobFilterService;
    private final JobRepository jobRepository;
    private Page page;

    public Job51RecruitmentServiceImpl(ConfigService configService,
            UserProfileRepository userProfileRepository,
            PlaywrightService playwrightService,
            Job51ApiMonitorService job51ApiMonitorService,
            JobFilterService jobFilterService,
            JobRepository jobRepository) {
        super(configService, userProfileRepository);
        this.playwrightService = playwrightService;
        this.job51ApiMonitorService = job51ApiMonitorService;
        this.jobFilterService = jobFilterService;
        this.jobRepository = jobRepository;
    }

    @PostConstruct
    public void init() {
        this.page = playwrightService.getPage(RecruitmentPlatformEnum.JOB_51);
    }

    @Override
    public RecruitmentPlatformEnum getPlatform() {
        return RecruitmentPlatformEnum.JOB_51;
    }

    @Override
    public boolean login() {
        log.info("开始51job登录检查");

        try {
            // 使用Playwright打开网站
            page.navigate(HOME_URL);

            // 检查是否需要登录
            if (isLoginRequired()) {
                log.info("需要登录，开始登录流程");
                return performLogin();
            } else {
                log.info("51job已登录");
                return true;
            }
        } catch (Exception e) {
            log.error("51job登录失败", e);
            return false;
        }
    }

    @Override
    public List<JobDTO> collectJobs() {
        log.info("开始执行51job岗位采集操作");
        List<JobDTO> allJobDTOS = new ArrayList<>();

        // 从数据库加载平台配置
        ConfigDTO config = loadPlatformConfig();
        if (config == null) {
            log.warn("51job配置未找到，跳过岗位采集");
            return allJobDTOS;
        }

        // 记录采集开始时间，用于统计新增岗位数量
        LocalDateTime collectionStartTime = LocalDateTime.now();

        try {
            // 启动API监控服务
            job51ApiMonitorService.startMonitoring();

            for (String cityCode : config.getCityCodeCodes()) {
                // 检查任务是否被终止
                checkTerminateRequested();

                for (String keyword : config.getKeywordsList()) {
                    // 检查任务是否被终止
                    checkTerminateRequested();

                    collectJobsByCity(cityCode, keyword, config);
                }
            }

            // 等待一段时间确保所有API响应都被处理完毕
            try {
                Thread.sleep(3000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw e;
            }

            // 统计采集期间新增的岗位数量
            LocalDateTime collectionEndTime = LocalDateTime.now();
            long collectedJobCount = jobRepository.countByPlatformAndCreatedAtBetween(
                    "51job", collectionStartTime, collectionEndTime);

            log.info("51job岗位采集完成，共采集{}个岗位", collectedJobCount);
            return allJobDTOS;

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("51job岗位采集被终止");
            return allJobDTOS;
        } catch (Exception e) {
            log.error("51job岗位采集失败", e);
            return allJobDTOS;
        }
    }

    private void collectJobsByCity(String cityCode, String keyword, ConfigDTO config) {
        String searchParams = buildSearchParams(cityCode, config);
        String fullUrl = SEARCH_JOB_URL + searchParams;
        log.info("开始采集，城市: {}，关键词: {}，URL: {}", cityCode, keyword, fullUrl);

        // 使用新页面采集（主页面的Playwright请求状态已被WAF破坏）
        Page searchPage = page.context().newPage();
        try {
            searchPage.setDefaultTimeout(30000);

            // 设置请求头，模拟真实浏览器访问，绕过WAF检测
            java.util.Map<String, String> headers = new java.util.HashMap<>();
            headers.put("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8");
            headers.put("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
            headers.put("Accept-Encoding", "gzip, deflate, br");
            headers.put("Cache-Control", "no-cache");
            headers.put("Pragma", "no-cache");
            headers.put("Sec-Ch-Ua", "\"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\", \"Not-A.Brand\";v=\"99\"");
            headers.put("Sec-Ch-Ua-Mobile", "?0");
            headers.put("Sec-Ch-Ua-Platform", "\"Windows\"");
            headers.put("Sec-Fetch-Dest", "document");
            headers.put("Sec-Fetch-Mode", "navigate");
            headers.put("Sec-Fetch-Site", "none");
            headers.put("Sec-Fetch-User", "?1");
            headers.put("Upgrade-Insecure-Requests", "1");
            searchPage.setExtraHTTPHeaders(headers);

            // 在新页面上注册API监控服务，以便拦截搜索API响应
            job51ApiMonitorService.registerResponseMonitorOnPage(searchPage);

            // WAF绕过：先访问首页建立cookie
            log.info("WAF绕过：访问51job首页");
            try {
                searchPage.navigate(HOME_URL, new Page.NavigateOptions().setTimeout(20000));
            } catch (Exception e) {
                log.warn("首页导航异常: {}", e.getMessage());
            }
            try { searchPage.waitForLoadState(com.microsoft.playwright.options.LoadState.DOMCONTENTLOADED,
                    new Page.WaitForLoadStateOptions().setTimeout(10000)); } catch (Exception ignored) {}
            log.info("首页URL: {}", searchPage.url());
            try { Thread.sleep(5000); } catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }

            // 导航到搜索页面
            log.info("WAF绕过：导航到搜索页面: {}", fullUrl);
            try {
                searchPage.navigate(fullUrl, new Page.NavigateOptions().setTimeout(20000));
            } catch (Exception e) {
                log.warn("搜索页导航异常: {}", e.getMessage());
            }
            try { searchPage.waitForLoadState(com.microsoft.playwright.options.LoadState.DOMCONTENTLOADED,
                    new Page.WaitForLoadStateOptions().setTimeout(15000)); } catch (Exception ignored) {}
            log.info("搜索页导航后URL: {}", searchPage.url());
            try { Thread.sleep(8000); } catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }
            log.info("等待后URL: {}", searchPage.url());

            // reload让搜索API在WAF cookie已设置后重新发起
            log.info("WAF绕过：reload页面触发搜索API");
            try {
                searchPage.reload(new Page.ReloadOptions()
                        .setWaitUntil(com.microsoft.playwright.options.WaitUntilState.NETWORKIDLE));
            } catch (Exception e) {
                log.warn("reload异常: {}", e.getMessage());
            }
            // 等待更长时间，确保页面完全加载
            try { Thread.sleep(20000); } catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }

            // 滚动页面加载更多内容
            try {
                searchPage.evaluate("window.scrollTo(0, document.body.scrollHeight)");
                Thread.sleep(3000);
                searchPage.evaluate("window.scrollTo(0, 0)");
                Thread.sleep(2000);
            } catch (Exception e) {
                log.warn("滚动页面异常: {}", e.getMessage());
            }

            // 保存截图用于调试
            try {
                searchPage.screenshot(new Page.ScreenshotOptions().setPath(
                    java.nio.file.Paths.get("logs/51job_debug_" + System.currentTimeMillis() + ".png")));
                log.info("截图已保存");
            } catch (Exception e) {
                log.warn("截图保存失败: {}", e.getMessage());
            }

            // 检查页面是否有搜索结果
            // 先打印页面URL和body内容用于调试
            log.info("当前页面URL: {}", searchPage.url());
            try {
                String bodyPreview = searchPage.evaluate("document.body ? document.body.innerText.substring(0, 500) : 'no body'").toString();
                log.info("页面body前500字符: {}", bodyPreview);
            } catch (Exception e) {
                log.warn("获取body失败: {}", e.getMessage());
            }

            boolean hasResults = checkPageHasSearchResults(searchPage, keyword);
            log.info("页面搜索结果检查: hasResults={}, keyword={}", hasResults, keyword);

            if (!hasResults) {
                log.warn("页面无搜索结果，城市: {}，关键词: {}", cityCode, keyword);
                return;
            }

            // 从页面DOM提取职位数据并保存
            int savedCount = extractAndSaveJobsFromPage(searchPage, keyword);
            log.info("城市: {}，关键词: {} 的51job岗位采集完成，保存 {} 个职位", cityCode, keyword, savedCount);

        } catch (Exception e) {
            log.error("采集51job岗位失败: 城市={}, 关键词={}", cityCode, keyword, e);
        } finally {
            try { searchPage.close(); } catch (Exception ignored) {}
        }
    }

    /**
     * 检查页面是否有搜索结果（通过JS检查DOM内容）
     */
    private boolean checkPageHasSearchResults(Page page, String keyword) {
        try {
            String result = page.evaluate(
                    "(() => {" +
                    "  const body = document.body ? document.body.innerText : '';" +
                    "  const hasSalary = body.includes('元/月') || body.includes('千/月') || body.includes('万/月') || /\\d+[千万]-\\d+[万千元]/.test(body);" +
                    "  const keywordLower = '" + keyword.toLowerCase() + "';" +
                    "  const hasKeywordJobs = body.toLowerCase().includes(keywordLower) && hasSalary;" +
                    "  const hasWaf = body.includes('aliyun_waf') || body.includes('punish');" +
                    "  return JSON.stringify({hasKeywordJobs: hasKeywordJobs, hasWaf: hasWaf, bodyLength: body.length});" +
                    "})()"
            ).toString();

            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            @SuppressWarnings("unchecked")
            java.util.Map<String, Object> info = mapper.readValue(result, java.util.Map.class);
            boolean hasKeywordJobs = Boolean.TRUE.equals(info.get("hasKeywordJobs"));
            boolean hasWaf = Boolean.TRUE.equals(info.get("hasWaf"));
            log.info("页面状态: hasKeywordJobs={}, hasWaf={}, bodyLength={}", hasKeywordJobs, hasWaf, info.get("bodyLength"));
            return hasKeywordJobs && !hasWaf;
        } catch (Exception e) {
            log.warn("检查页面搜索结果失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 从页面DOM提取职位数据并保存到数据库
     * 通过JS在页面中提取职位列表的结构化数据
     */
    @SuppressWarnings("unchecked")
    private int extractAndSaveJobsFromPage(Page page, String keyword) {
        try {
            // 先检查DOM中有哪些元素
            try {
                String domInfo = page.evaluate(
                    "(() => {" +
                    "  const selectors = ['[data-jobid]', '.joblist-item', '.j_joblist .e', '.jt .job_item', '.joblist .job_item', '.sensorsname', '.job_name', '.company_name', '.sal'];" +
                    "  const info = {};" +
                    "  selectors.forEach(s => { info[s] = document.querySelectorAll(s).length; });" +
                    "  info['bodyLength'] = document.body ? document.body.innerText.length : 0;" +
                    "  info['allLinks'] = document.querySelectorAll('a').length;" +
                    "  return JSON.stringify(info);" +
                    "})()"
                ).toString();
                log.info("DOM元素统计: {}", domInfo);
            } catch (Exception e) {
                log.warn("DOM统计失败: {}", e.getMessage());
            }

            String jsonResult = page.evaluate(
                    "(() => {" +
                    "  const items = document.querySelectorAll('[data-jobid], .joblist-item, .j_joblist .e, .jt .job_item, .joblist .job_item, .sensorsname');" +
                    "  const jobs = [];" +
                    "  items.forEach(item => {" +
                    "    const titleEl = item.querySelector('.jname .job_name, .t .job_name, a.job_name, .title a, h2 a, .job_name, .title');" +
                    "    const companyEl = item.querySelector('.cname .company_name, .t2 .company_name, .company_name, .title .company, .comp_name');" +
                    "    const salaryEl = item.querySelector('.sal, .salary, .j_salary, .job_salary');" +
                    "    const areaEl = item.querySelector('.d.at, .area, .j_area, .job_area');" +
                    "    const linkEl = item.querySelector('a[href]');" +
                    "    if (titleEl) {" +
                    "      jobs.push({" +
                    "        title: titleEl.textContent.trim()," +
                    "        company: companyEl ? companyEl.textContent.trim() : ''," +
                    "        salary: salaryEl ? salaryEl.textContent.trim() : ''," +
                    "        area: areaEl ? areaEl.textContent.trim() : ''," +
                    "        href: linkEl ? linkEl.href : ''," +
                    "        jobId: item.getAttribute('data-jobid') || ''" +
                    "      });" +
                    "    }" +
                    "  });" +
                    "  return JSON.stringify(jobs);" +
                    "})()"
            ).toString();

            java.util.List<java.util.Map<String, String>> jobs =
                    new com.fasterxml.jackson.databind.ObjectMapper().readValue(jsonResult,
                            new com.fasterxml.jackson.databind.ObjectMapper().getTypeFactory().constructCollectionType(
                                    java.util.List.class, java.util.Map.class));

            if (jobs.isEmpty()) {
                log.warn("DOM提取未找到职位数据，尝试备用选择器");
                return extractJobsWithFallbackSelector(page, keyword);
            }

            int savedCount = 0;
            for (java.util.Map<String, String> job : jobs) {
                String jobId = job.getOrDefault("jobId", "");
                String title = job.getOrDefault("title", "");
                String company = job.getOrDefault("company", "");
                String salary = job.getOrDefault("salary", "");
                String area = job.getOrDefault("area", "");
                String href = job.getOrDefault("href", "");

                if (title.isEmpty()) continue;

                // 检查是否已存在
                if (jobId != null && !jobId.isEmpty() && jobRepository.existsByEncryptJobId(jobId)) {
                    continue;
                }

                JobEntity entity = new JobEntity();
                entity.setEncryptJobId(jobId);
                entity.setJobTitle(title);
                entity.setCompanyName(company);
                entity.setSalaryDesc(salary);
                entity.setWorkArea(area);
                entity.setJobUrl(href);
                entity.setPlatform("51job");
                jobRepository.save(entity);
                savedCount++;
                log.info("保存职位: {} - {} - {}", title, company, salary);
            }
            return savedCount;
        } catch (Exception e) {
            log.error("从页面DOM提取职位数据失败", e);
            return 0;
        }
    }

    /**
     * 备用选择器提取职位数据
     */
    private int extractJobsWithFallbackSelector(Page page, String keyword) {
        try {
            // 尝试通过文本内容提取
            String jsonResult = page.evaluate(
                    "(() => {" +
                    "  const body = document.body.innerText;" +
                    "  const lines = body.split('\\n').filter(l => l.trim().length > 0);" +
                    "  const jobs = [];" +
                    "  for (let i = 0; i < lines.length; i++) {" +
                    "    const line = lines[i].trim();" +
                    "    if (/\\d+[万千元]+.*\\//.test(line) || /面议/.test(line)) {" +
                    "      // 可能是薪资行，前面的行可能是职位名" +
                    "      const title = i > 0 ? lines[i-1].trim() : '';" +
                    "      const company = i > 1 ? lines[i-2].trim() : '';" +
                    "      if (title.length > 2 && title.length < 50) {" +
                    "        jobs.push({title, company, salary: line});" +
                    "      }" +
                    "    }" +
                    "  }" +
                    "  return JSON.stringify(jobs.slice(0, 50));" +
                    "})()"
            ).toString();

            java.util.List<java.util.Map<String, String>> jobs =
                    new com.fasterxml.jackson.databind.ObjectMapper().readValue(jsonResult,
                            new com.fasterxml.jackson.databind.ObjectMapper().getTypeFactory().constructCollectionType(
                                    java.util.List.class, java.util.Map.class));

            int savedCount = 0;
            for (java.util.Map<String, String> job : jobs) {
                String title = job.getOrDefault("title", "");
                String company = job.getOrDefault("company", "");
                String salary = job.getOrDefault("salary", "");
                if (title.isEmpty() || title.length() < 2) continue;

                JobEntity entity = new JobEntity();
                entity.setJobTitle(title);
                entity.setCompanyName(company);
                entity.setSalaryDesc(salary);
                entity.setPlatform("51job");
                jobRepository.save(entity);
                savedCount++;
                log.info("保存职位(备用): {} - {} - {}", title, company, salary);
            }
            return savedCount;
        } catch (Exception e) {
            log.error("备用选择器提取失败", e);
            return 0;
        }
    }

    @Override
    public List<JobDTO> collectRecommendJobs() {
        log.info("开始51job推荐岗位采集");
        List<JobDTO> recommendJobDTOS = new ArrayList<>();

        // 记录采集开始时间，用于统计新增岗位数量
        LocalDateTime collectionStartTime = LocalDateTime.now();

        try {
            // 启动API监控服务
            job51ApiMonitorService.startMonitoring();

            // 使用新页面采集推荐岗位
            Page recommendPage = page.context().newPage();
            try {
                recommendPage.setDefaultTimeout(30000);

                // 导航到51job首页（推荐岗位通常在首页展示）
                log.info("WAF绕过：访问51job首页获取推荐岗位");
                try {
                    recommendPage.navigate(HOME_URL, new Page.NavigateOptions().setTimeout(20000));
                } catch (Exception e) {
                    log.warn("首页导航异常: {}", e.getMessage());
                }
                try {
                    recommendPage.waitForLoadState(
                            com.microsoft.playwright.options.LoadState.DOMCONTENTLOADED,
                            new Page.WaitForLoadStateOptions().setTimeout(10000));
                } catch (Exception ignored) {
                }

                // 等待页面加载完成
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return recommendJobDTOS;
                }

                // 检查是否有推荐岗位区域
                boolean hasRecommendJobs = checkPageHasRecommendJobs(recommendPage);
                log.info("页面推荐岗位检查: hasRecommendJobs={}", hasRecommendJobs);

                if (hasRecommendJobs) {
                    // 从页面DOM提取推荐职位数据并保存
                    int savedCount = extractAndSaveRecommendJobsFromPage(recommendPage);
                    log.info("51job推荐岗位采集完成，保存 {} 个职位", savedCount);
                } else {
                    log.info("页面未找到推荐岗位区域");
                }

            } finally {
                try {
                    recommendPage.close();
                } catch (Exception ignored) {
                }
            }

            // 等待一段时间确保所有API响应都被处理完毕
            try {
                Thread.sleep(3000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw e;
            }

            // 统计采集期间新增的岗位数量
            LocalDateTime collectionEndTime = LocalDateTime.now();
            long collectedJobCount = jobRepository.countByPlatformAndCreatedAtBetween(
                    "51job", collectionStartTime, collectionEndTime);

            log.info("51job推荐岗位采集完成，共采集{}个岗位", collectedJobCount);

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("51job推荐岗位采集被终止");
        } catch (Exception e) {
            log.error("51job推荐岗位采集失败", e);
        }

        return recommendJobDTOS;
    }

    /**
     * 检查页面是否有推荐岗位区域
     */
    private boolean checkPageHasRecommendJobs(Page page) {
        try {
            String result = page.evaluate(
                    "(() => {" +
                    "  const body = document.body ? document.body.innerText : '';" +
                    "  const hasRecommend = body.includes('推荐职位') || body.includes('猜你喜欢') || body.includes('为你推荐') || body.includes('推荐岗位');" +
                    "  const hasSalary = body.includes('元/月') || body.includes('千/月') || body.includes('万/月');" +
                    "  return JSON.stringify({hasRecommend: hasRecommend, hasSalary: hasSalary, bodyLength: body.length});" +
                    "})()"
            ).toString();

            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            @SuppressWarnings("unchecked")
            java.util.Map<String, Object> info = mapper.readValue(result, java.util.Map.class);
            boolean hasRecommend = Boolean.TRUE.equals(info.get("hasRecommend"));
            boolean hasSalary = Boolean.TRUE.equals(info.get("hasSalary"));
            log.info("推荐岗位状态: hasRecommend={}, hasSalary={}, bodyLength={}", hasRecommend, hasSalary, info.get("bodyLength"));
            return hasRecommend && hasSalary;
        } catch (Exception e) {
            log.warn("检查页面推荐岗位失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 从页面DOM提取推荐职位数据并保存到数据库
     */
    @SuppressWarnings("unchecked")
    private int extractAndSaveRecommendJobsFromPage(Page page) {
        try {
            String jsonResult = page.evaluate(
                    "(() => {" +
                    "  const items = document.querySelectorAll('[data-jobid], .joblist-item, .j_joblist .e, .jt .job_item, .joblist .job_item, .sensorsname, .recommend-job-item, .job-item');" +
                    "  const jobs = [];" +
                    "  items.forEach(item => {" +
                    "    const titleEl = item.querySelector('.jname .job_name, .t .job_name, a.job_name, .title a, h2 a, .job_name, .title');" +
                    "    const companyEl = item.querySelector('.cname .company_name, .t2 .company_name, .company_name, .title .company, .comp_name');" +
                    "    const salaryEl = item.querySelector('.sal, .salary, .j_salary, .job_salary');" +
                    "    const areaEl = item.querySelector('.d.at, .area, .j_area, .job_area');" +
                    "    const linkEl = item.querySelector('a[href]');" +
                    "    if (titleEl) {" +
                    "      jobs.push({" +
                    "        title: titleEl.textContent.trim()," +
                    "        company: companyEl ? companyEl.textContent.trim() : ''," +
                    "        salary: salaryEl ? salaryEl.textContent.trim() : ''," +
                    "        area: areaEl ? areaEl.textContent.trim() : ''," +
                    "        href: linkEl ? linkEl.href : ''," +
                    "        jobId: item.getAttribute('data-jobid') || ''" +
                    "      });" +
                    "    }" +
                    "  });" +
                    "  return JSON.stringify(jobs);" +
                    "})()"
            ).toString();

            java.util.List<java.util.Map<String, String>> jobs =
                    new com.fasterxml.jackson.databind.ObjectMapper().readValue(jsonResult,
                            new com.fasterxml.jackson.databind.ObjectMapper().getTypeFactory().constructCollectionType(
                                    java.util.List.class, java.util.Map.class));

            int savedCount = 0;
            for (java.util.Map<String, String> job : jobs) {
                String jobId = job.getOrDefault("jobId", "");
                String title = job.getOrDefault("title", "");
                String company = job.getOrDefault("company", "");
                String salary = job.getOrDefault("salary", "");
                String area = job.getOrDefault("area", "");
                String href = job.getOrDefault("href", "");

                if (title.isEmpty()) continue;

                // 检查是否已存在
                if (jobId != null && !jobId.isEmpty() && jobRepository.existsByEncryptJobId(jobId)) {
                    continue;
                }

                JobEntity entity = new JobEntity();
                entity.setEncryptJobId(jobId);
                entity.setJobTitle(title);
                entity.setCompanyName(company);
                entity.setSalaryDesc(salary);
                entity.setWorkArea(area);
                entity.setJobUrl(href);
                entity.setPlatform("51job");
                jobRepository.save(entity);
                savedCount++;
                log.info("保存推荐职位: {} - {} - {}", title, company, salary);
            }
            return savedCount;
        } catch (Exception e) {
            log.error("从页面DOM提取推荐职位数据失败", e);
            return 0;
        }
    }

    @Override
    public List<JobDTO> filterJobs(List<JobDTO> jobDTOS) {
        // 从数据库获取51job平台的配置
        ConfigDTO config = loadPlatformConfig();
        if (config == null) {
            log.warn("51job配置未找到，跳过过滤");
            return jobDTOS;
        }

        return jobFilterService.filterJobs(jobDTOS, config);
    }

    @Override
    public int deliverJobs(List<JobDTO> jobDTOS) {
        log.info("开始执行51job岗位投递操作，待投递岗位数量: {}", jobDTOS.size());

        // 在新标签页中打开岗位详情
        try (Page jobPage = page.context().newPage()) {

            AtomicInteger count = new AtomicInteger();

            try {
                jobDTOS.forEach(jobDTO -> {

                    jobPage.navigate(jobDTO.getHref());
                    // 执行投递
                    Job51ElementLocators.clickApplyJobButton(jobPage);
                    count.getAndIncrement();

                    // 添加3-5秒随机延迟，避免投递过快
                    try {
                        int randomSeconds = new Random().nextInt(3) + 3; // 3-5秒
                        TimeUnit.SECONDS.sleep(randomSeconds);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }

                });

                return count.get(); // 暂时返回0，等待具体实现

            } catch (Exception e) {
                log.error("51job岗位投递失败", e);
                return count.get();
            }
        }
    }

    @Override
    public boolean isDeliveryLimitReached() {
        try {
            // 检查页面是否出现投递限制提示
            TimeUnit.SECONDS.sleep(1);

            // 通过JS检查页面是否包含投递限制相关文本
            String result = page.evaluate(
                    "(() => {" +
                    "  const body = document.body ? document.body.innerText : '';" +
                    "  const hasLimit = body.includes('已达上限') || body.includes('投递上限') || body.includes('今日投递') || body.includes('投递次数已用完');" +
                    "  const hasDialog = document.querySelector('.el-dialog, .modal, [role=\"dialog\"]') !== null;" +
                    "  return JSON.stringify({hasLimit: hasLimit, hasDialog: hasDialog});" +
                    "})()"
            ).toString();

            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            @SuppressWarnings("unchecked")
            java.util.Map<String, Object> info = mapper.readValue(result, java.util.Map.class);
            boolean isLimit = Boolean.TRUE.equals(info.get("hasLimit"));

            if (isLimit) {
                log.warn("51job投递限制：今日投递已达上限");
            }

            return isLimit;
        } catch (Exception e) {
            log.debug("51job投递限制检查异常: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public void saveData(String dataPath) {
        log.info("保存51job Cookie数据: {}", dataPath);
        try {
            saveCookieToConfig();
        } catch (Exception e) {
            log.error("51job数据保存失败", e);
        }
    }

    // ==================== 私有辅助方法 ====================

    /**
     * 构建完整的搜索参数字符串
     * 基于URL:
     * https://we.51job.com/pc/search?jobArea=030200&keyword=java&salary=16000-20000&workYear=05&degree=04&companySize=03&companyType=04
     *
     * @param cityCode 城市代码
     * @param config   配置信息
     * @return 完整的搜索参数字符串
     */
    private String buildSearchParams(String cityCode, ConfigDTO config) {
        StringBuilder params = new StringBuilder();

        try {
            // 必需参数
            params.append("jobArea=").append(cityCode);

            // 关键词需要URL编码
            String keywords = config.getKeywords() != null ? config.getKeywords().trim() : "";
            params.append("&keyword=").append(URLEncoder.encode(keywords, StandardCharsets.UTF_8));

            // 可选参数 - 薪资范围 (如: 16000-20000)
            appendParameterIfNotEmpty(params, "salary", config.getSalary());

            // 可选参数 - 工作年限 (如: 05表示5年以上)
            appendParameterIfNotEmpty(params, "workYear", config.getExperience());

            // 可选参数 - 学历要求 (如: 04表示本科)
            appendParameterIfNotEmpty(params, "degree", config.getDegree());

            // 可选参数 - 公司规模 (如: 03表示100-499人)
            appendParameterIfNotEmpty(params, "companySize", config.getScale());

            // 可选参数 - 公司类型 (如: 04表示民营公司)
            appendParameterIfNotEmpty(params, "companyType", config.getCompanyType());

            // 其他可能的参数
            // industrytype - 行业类型
            appendParameterIfNotEmpty(params, "industrytype", config.getIndustry());

            // jobtype - 职位类型
            appendParameterIfNotEmpty(params, "jobtype", config.getJobType());

        } catch (Exception e) {
            log.error("构建搜索参数失败", e);
            // 返回基础参数
            return "jobArea=" + cityCode + "&keyword=" +
                    (config.getKeywords() != null ? config.getKeywords() : "");
        }

        log.debug("构建的搜索参数: {}", params.toString());
        return params.toString();
    }

    /**
     * 添加参数到StringBuilder（如果参数值不为空）
     *
     * @param params     参数构建器
     * @param paramName  参数名
     * @param paramValue 参数值
     */
    private void appendParameterIfNotEmpty(StringBuilder params, String paramName, String paramValue) {
        if (paramValue != null && !paramValue.trim().isEmpty()) {
            try {
                params.append("&").append(paramName).append("=")
                        .append(URLEncoder.encode(paramValue.trim(), StandardCharsets.UTF_8));
            } catch (Exception e) {
                log.warn("编码参数失败: {}={}", paramName, paramValue, e);
                // 如果编码失败，使用原始值
                params.append("&").append(paramName).append("=").append(paramValue.trim());
            }
        }
    }

    /**
     * 检查是否需要登录
     */
    private boolean isLoginRequired() {
        try {
            // 检查是否存在登录按钮
            if (Job51ElementLocators.hasLoginElement(page)) {
                log.debug("检测到登录按钮，需要登录");
                return true; // 需要登录
            }

            return false;
        } catch (Exception e) {
            log.error("登录状态检查出错", e);
            return true; // 出错时默认需要登录
        }
    }

    /**
     * 执行登录操作
     */
    @SneakyThrows
    private boolean performLogin() {
        page.navigate(LOGIN_URL);
        TimeUnit.SECONDS.sleep(3);

        try {
            // 检查是否已经登录
            if (Job51ElementLocators.isUserLoggedIn(page)) {
                log.info("检测到已登录状态");
                return true;
            }
        } catch (Exception ignored) {
        }

        log.info("等待用户手动登录...");

        boolean login = false;

        while (!login) {
            try {
                // 判断登录页登录元素是否还存在
                if (Job51ElementLocators.hasPasswordLoginElement(page)) {
                    login = true;
                    log.info("登录成功");
                }
            } catch (Exception e) {
                // 登录检查异常，继续等待
                log.debug("登录状态检查异常，继续等待: {}", e.getMessage());
            }

            // 等待一段时间后再次检查
            TimeUnit.SECONDS.sleep(3);
        }

        return true;
    }

    /**
     * 等待页面完全加载
     * 等待分页元素和职位列表元素出现，确保页面内容完全加载
     */
    private void waitForPageLoad(Page page) {
        try {
            log.info("等待页面加载完成...");

            // 等待DOM加载完成
            page.waitForLoadState();

            // 等待分页元素出现（最多等待10秒）
            try {
                page.waitForSelector("ul.el-pager", new Page.WaitForSelectorOptions().setTimeout(10000));
                log.info("分页元素已加载");
            } catch (Exception e) {
                log.warn("分页元素加载超时，可能页面没有分页或加载失败: {}", e.getMessage());
            }

            // 额外等待一段时间，确保JS完全执行完毕
            TimeUnit.SECONDS.sleep(2);

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("等待页面加载被中断: {}", e.getMessage());
        } catch (Exception e) {
            log.error("等待页面加载时发生错误: {}", e.getMessage());
            // 发生错误时也等待一段时间
            try {
                TimeUnit.SECONDS.sleep(3);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
        }
    }

    /**
     * 等待页面内容加载
     * 在点击分页后等待新页面内容加载完成
     */
    private void waitForPageContentLoad(Page page) {
        try {
            log.debug("等待页面内容更新...");

            // 等待网络空闲，确保数据加载完成
            page.waitForLoadState();

            // 等待职位列表内容更新
            try {
                page.waitForSelector("div.joblist .joblist-item", new Page.WaitForSelectorOptions().setTimeout(5000));
                log.debug("职位列表内容已更新");
            } catch (Exception e) {
                log.warn("职位列表内容更新超时: {}", e.getMessage());
            }

            // 短暂等待确保页面稳定
            TimeUnit.SECONDS.sleep(1);

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("等待页面内容加载被中断: {}", e.getMessage());
        } catch (Exception e) {
            log.error("等待页面内容加载时发生错误: {}", e.getMessage());
            // 发生错误时也等待一段时间
            try {
                TimeUnit.SECONDS.sleep(2);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
        }
    }

    /**
     * WAF反爬绕过策略
     * 51job使用阿里云WAF保护搜索API，直接访问搜索页会被拦截。
     * 策略：先访问首页让WAF challenge JS执行并设置cookie，再导航到搜索页，最后reload使搜索API在WAF cookie已设置后重新发起。
     *
     * @param searchUrl 搜索页完整URL
     */
    /**
     * 保存Cookie到配置实体
     */
    private void saveCookieToConfig() {
        try {
            ConfigEntity config = loadPlatformConfigEntity();
            if (config == null) {
                config = new ConfigEntity();
            }

            String cookieJson = getCurrentCookiesAsJson();
            config.setCookieData(cookieJson);
            config.setPlatformType(getPlatform().getPlatformCode());
            configService.save(config);
            log.info("51job Cookie已保存到配置实体");
        } catch (Exception e) {
            log.error("保存51job Cookie到配置失败", e);
        }
    }

    /**
     * 获取当前浏览器Cookie并转换为JSON字符串
     */
    private String getCurrentCookiesAsJson() {
        try {
            List<Cookie> cookies = page.context().cookies();
            JSONArray jsonArray = new JSONArray();

            for (Cookie cookie : cookies) {
                JSONObject jsonObject = new JSONObject();
                jsonObject.put("name", cookie.name);
                jsonObject.put("value", cookie.value);
                jsonObject.put("domain", cookie.domain);
                jsonObject.put("path", cookie.path);
                if (cookie.expires != null) {
                    jsonObject.put("expires", cookie.expires);
                }
                jsonObject.put("secure", cookie.secure);
                jsonObject.put("httpOnly", cookie.httpOnly);
                jsonArray.put(jsonObject);
            }

            return jsonArray.toString();
        } catch (Exception e) {
            log.error("获取51job当前Cookie失败", e);
            return "[]";
        }
    }
}
