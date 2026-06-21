package getjobs.modules.getjobs.zhilian.service.impl;

import com.github.openjson.JSONArray;
import com.github.openjson.JSONObject;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.Cookie;
import getjobs.common.dto.ConfigDTO;
import getjobs.common.enums.RecruitmentPlatformEnum;
import getjobs.common.util.PageHealthChecker;
import getjobs.infrastructure.playwright.PlaywrightService;
import getjobs.modules.getjobs.boss.dto.JobDTO;
import getjobs.modules.getjobs.service.JobFilterService;
import getjobs.modules.getjobs.zhilian.service.playwright.ZhiLianApiMonitorService;
import getjobs.modules.getjobs.zhilian.service.ZhiLianElementLocators;
import getjobs.repository.JobRepository;
import getjobs.repository.UserProfileRepository;
import getjobs.repository.entity.ConfigEntity;
import getjobs.modules.getjobs.service.AbstractRecruitmentService;
import getjobs.modules.getjobs.service.ConfigService;
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
 * 智联招聘服务实现类
 * 
 * @author loks666
 *         项目链接: <a href=
 *         "https://github.com/loks666/get_jobs">https://github.com/loks666/get_jobs</a>
 */
@Slf4j
@Service
public class ZhiLianRecruitmentServiceImpl extends AbstractRecruitmentService {

    private static final String HOME_URL = RecruitmentPlatformEnum.ZHILIAN_ZHAOPIN.getHomeUrl();
    private static final String SEARCH_JOB_URL = "https://www.zhaopin.com/sou?";
    // https://www.zhaopin.com/sou?el=4&we=0510&et=2&sl=15001,25000&jl=763&kw=java

    private final PlaywrightService playwrightService;
    private final ZhiLianApiMonitorService zhiLianApiMonitorService;
    private final JobFilterService jobFilterService;
    private final JobRepository jobRepository;
    private Page page;

    public ZhiLianRecruitmentServiceImpl(ConfigService configService,
            UserProfileRepository userProfileRepository,
            PlaywrightService playwrightService,
            ZhiLianApiMonitorService zhiLianApiMonitorService,
            JobFilterService jobFilterService,
            JobRepository jobRepository) {
        super(configService, userProfileRepository);
        this.playwrightService = playwrightService;
        this.zhiLianApiMonitorService = zhiLianApiMonitorService;
        this.jobFilterService = jobFilterService;
        this.jobRepository = jobRepository;
    }

    @PostConstruct
    public void init() {
        this.page = playwrightService.getPage(RecruitmentPlatformEnum.ZHILIAN_ZHAOPIN);
    }

    @Override
    public RecruitmentPlatformEnum getPlatform() {
        return RecruitmentPlatformEnum.ZHILIAN_ZHAOPIN;
    }

    @Override
    public boolean login() {
        log.info("开始智联招聘登录检查");

        try {
            // 使用Playwright打开网站（带重试机制）
            PageHealthChecker.executeWithRetry(
                    page,
                    () -> {
                        page.navigate(HOME_URL);
                        return null;
                    },
                    "导航到智联招聘首页",
                    2 // 最多重试2次
            );

            // 检查是否需要登录
            if (ZhiLianElementLocators.isLoginRequired(page)) {
                log.info("需要登录，开始登录流程");
                return performLogin();
            } else {
                log.info("智联招聘已登录");
                return true;
            }
        } catch (Exception e) {
            log.error("智联招聘登录失败", e);
            return false;
        }
    }

    @Override
    public List<JobDTO> collectJobs() {
        log.info("开始智联招聘岗位采集");
        List<JobDTO> allJobDTOS = new ArrayList<>();

        // 从数据库加载平台配置
        ConfigDTO config = loadPlatformConfig();
        if (config == null) {
            log.warn("智联招聘配置未找到，跳过岗位采集");
            return allJobDTOS;
        }

        // 记录采集开始时间，用于统计新增岗位数量
        LocalDateTime collectionStartTime = LocalDateTime.now();

        try {
            // 启动API监控服务
            zhiLianApiMonitorService.startMonitoring();

            // 按城市和关键词搜索岗位
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
                    "zhilian", collectionStartTime, collectionEndTime);

            log.info("智联招聘岗位采集完成，共采集{}个岗位", collectedJobCount);
            return allJobDTOS;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("智联招聘岗位采集被终止");
            return allJobDTOS;
        } catch (Exception e) {
            log.error("智联招聘岗位采集失败", e);
            return allJobDTOS;
        }
    }

    @Override
    public List<JobDTO> collectRecommendJobs() {
        return List.of();
    }

    @Override
    public List<JobDTO> filterJobs(List<JobDTO> jobDTOS) {
        // 从数据库获取智联招聘平台的配置
        ConfigDTO config = loadPlatformConfig();
        if (config == null) {
            log.warn("智联招聘配置未找到，跳过过滤");
            return jobDTOS;
        }

        return jobFilterService.filterJobs(jobDTOS, config);
    }

    @Override
    public int deliverJobs(List<JobDTO> jobDTOS) {
        log.info("开始执行智联招聘岗位投递操作，待投递岗位数量: {}", jobDTOS.size());
        AtomicInteger successCount = new AtomicInteger(0);

        // 在新标签页中打开岗位详情
        try (Page jobPage = page.context().newPage()) {
            jobPage.setDefaultTimeout(30000); // 为新页面设置默认超时

            for (JobDTO jobDTO : jobDTOS) {
                try {
                    // 检查任务是否被终止
                    checkTerminateRequested();

                    log.info("正在投递岗位: {}", jobDTO.getJobName());

                    // 导航到岗位详情页（带重试机制）
                    PageHealthChecker.executeWithRetry(
                            jobPage,
                            () -> {
                                jobPage.navigate(jobDTO.getHref());
                                return null;
                            },
                            "导航到智联招聘岗位详情页",
                            2 // 最多重试2次
                    );

                    jobPage.waitForLoadState(); // 等待页面加载

                    // 投递完成会打开新页签，需要关闭新页签
                    Page popup = jobPage.waitForPopup(() -> {
                        // 执行投递
                        if (ZhiLianElementLocators.clickSummaryApplyButton(jobPage)) {
                            log.info("岗位投递成功: {}", jobDTO.getJobName());
                            successCount.getAndIncrement();
                        } else {
                            log.warn("岗位投递失败或已投递: {}", jobDTO.getJobName());
                        }
                    });

                    if (popup != null) {
                        popup.waitForLoadState(); // 等加载稳定

                        // 校验是否是"投递成功"页
                        boolean isDeliverySuccess = verifyDeliverySuccessPage(popup, jobDTO.getJobName());
                        if (isDeliverySuccess) {
                            log.info("投递成功页校验通过: {}", jobDTO.getJobName());
                        } else {
                            log.warn("投递成功页校验未通过: {}，URL: {}", jobDTO.getJobName(), popup.url());
                        }

                        popup.close(); // 关闭新页签
                    }

                    // 添加3-5秒随机延迟，避免投递过快
                    try {
                        int randomSeconds = new Random().nextInt(3) + 3; // 3-5秒
                        TimeUnit.SECONDS.sleep(randomSeconds);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }

                } catch (InterruptedException e) {
                    // 任务被终止，向外传播
                    throw e;
                } catch (Exception e) {
                    log.error("投递岗位 {} 时发生异常: {}", jobDTO.getJobName(), e.getMessage());
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("智联招聘岗位投递被终止，已成功投递: {}", successCount.get());
        } catch (Exception e) {
            log.error("智联招聘岗位投递过程中发生严重错误", e);
        }

        log.info("智联招聘岗位投递完成，成功投递 {} 个岗位", successCount.get());
        return successCount.get();
    }

    @Override
    public boolean isDeliveryLimitReached() {
        return false;
    }

    @Override
    public void saveData(String dataPath) {
        log.info("保存智联招聘 Cookie数据: {}", dataPath);
        try {
            saveCookieToConfig();
        } catch (Exception e) {
            log.error("智联招聘数据保存失败", e);
        }
    }

    // ==================== 私有辅助方法 ====================

    /**
     * 按城市采集岗位
     */
    private void collectJobsByCity(String cityCode, String keyword, ConfigDTO config) {
        String searchUrl = buildSearchUrl(cityCode, keyword, config);
        log.info("开始采集，城市: {}，关键词: {}，URL: {}", cityCode, keyword, searchUrl);

        try {
            // 导航到搜索页面（带重试机制）
            PageHealthChecker.executeWithRetry(
                    page,
                    () -> {
                        page.navigate(searchUrl);
                        return null;
                    },
                    "导航到智联招聘搜索页面",
                    2
            );

            // 等待页面加载
            page.waitForLoadState();

            int pageNumber = 1;
            while (ZhiLianElementLocators.clickPageNumber(page, pageNumber)) {
                log.info("正在处理第{}页数据", pageNumber);

                // 检查任务是否被终止
                checkTerminateRequested();

                // 等待5-10秒，确保API响应被拦截并完成数据入库
                try {
                    int waitSeconds = 5 + new Random().nextInt(6);
                    log.info("等待 {} 秒以完成数据采集和入库", waitSeconds);
                    TimeUnit.SECONDS.sleep(waitSeconds);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    log.warn("等待过程被中断");
                    break;
                }

                pageNumber++;
            }

            log.info("城市: {}，关键词: {} 的智联招聘岗位采集完成，共 {} 页", cityCode, keyword, pageNumber - 1);

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("智联招聘采集被中断: 城市={}, 关键词={}", cityCode, keyword);
        } catch (Exception e) {
            log.error("采集智联招聘岗位失败: 城市={}, 关键词={}", cityCode, keyword, e);
        }
    }

    /**
     * 构建搜索URL
     * 基于URL:
     * https://www.zhaopin.com/sou?el=4&we=0510&et=2&sl=15001,25000&jl=763&kw=java
     * 
     * @param cityCode 城市代码
     * @param keyword  关键词
     * @param config   配置信息
     * @return 完整的搜索URL
     */
    private String buildSearchUrl(String cityCode, String keyword, ConfigDTO config) {
        StringBuilder url = new StringBuilder(SEARCH_JOB_URL);

        try {
            // 必需参数
            // 关键词需要URL编码
            String encodedKeyword = URLEncoder.encode(keyword, StandardCharsets.UTF_8);
            url.append("kw=").append(encodedKeyword);

            // 城市参数 jl
            if (cityCode != null && !cityCode.trim().isEmpty()) {
                url.append("&jl=").append(cityCode);
            }

            // 学历要求 el (Education Level)
            // el=4 表示本科, 1=不限, 2=高中, 3=大专, 4=本科, 5=硕士, 6=博士
            if (config.getDegree() != null && !config.getDegree().trim().isEmpty()) {
                url.append("&el=").append(config.getDegree());
            }

            // 职位类型 et (Employment Type)
            // et=2 表示全职, 1=全职, 2=兼职, 3=实习
            if (config.getJobType() != null && !config.getJobType().trim().isEmpty()) {
                url.append("&et=").append(config.getJobType());
            }

            // 公司性质 ct (Company Type)
            if (config.getCompanyType() != null && !config.getCompanyType().trim().isEmpty()) {
                url.append("&ct=").append(config.getCompanyType());
            }

            // 公司规模 cs (Company Size)
            if (config.getScale() != null && !config.getScale().trim().isEmpty()) {
                url.append("&cs=").append(config.getScale());
            }

            // 薪资范围 sl (Salary Level)
            // 格式: sl=15001,25000
            if (config.getSalary() != null && !config.getSalary().trim().isEmpty()) {
                url.append("&sl=").append(config.getSalary());
            }

            // 工作经验 we (Work Experience)
            // we=0510 表示5-10年
            if (config.getExperience() != null && !config.getExperience().trim().isEmpty()) {
                url.append("&we=").append(config.getExperience());
            }

            // 行业类型 in
            if (config.getIndustry() != null && !config.getIndustry().trim().isEmpty()) {
                url.append("&in=").append(URLEncoder.encode(config.getIndustry(), StandardCharsets.UTF_8));
            }

        } catch (Exception e) {
            log.error("构建搜索URL失败", e);
            // 返回基础URL
            return SEARCH_JOB_URL + "kw=" + keyword;
        }

        String finalUrl = url.toString();
        log.debug("构建的搜索URL: {}", finalUrl);
        return finalUrl;
    }

    /**
     * 执行登录操作
     */
    private boolean performLogin() {
        try {
            // 直接首页登录即可，不需要单独使用登录页（带重试机制）
            PageHealthChecker.executeWithRetry(
                    page,
                    () -> {
                        page.navigate(HOME_URL);
                        return null;
                    },
                    "导航到智联招聘登录页面",
                    2 // 最多重试2次
            );

            TimeUnit.SECONDS.sleep(3);

            log.info("等待用户手动登录...");
            log.info("请在浏览器中完成登录操作");

            boolean loginSuccess = false;

            while (!loginSuccess) {
                try {
                    // 检查登录状态
                    if (ZhiLianElementLocators.isUserLoggedIn(page)) {
                        loginSuccess = true;
                        log.info("登录成功");
                    }
                } catch (Exception e) {
                    log.debug("登录状态检查异常: {}", e.getMessage());
                }

                TimeUnit.SECONDS.sleep(2);
            }

            return true;

        } catch (Exception e) {
            log.error("登录过程中发生错误", e);
            return false;
        }
    }

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
            log.info("智联招聘 Cookie已保存到配置实体");
        } catch (Exception e) {
            log.error("保存智联招聘 Cookie到配置失败", e);
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
            log.error("获取智联招聘当前Cookie失败", e);
            return "[]";
        }
    }

    /**
     * 校验是否是"投递成功"页
     * 通过URL或页面标题判断是否为投递成功页面
     *
     * @param popup   弹出的页面
     * @param jobName 岗位名称
     * @return 是否是投递成功页
     */
    private boolean verifyDeliverySuccessPage(Page popup, String jobName) {
        try {
            // 等待页面加载完成
            popup.waitForLoadState();

            String url = popup.url().toLowerCase();
            String title = "";

            try {
                title = popup.title().toLowerCase();
            } catch (Exception e) {
                log.debug("获取页面标题失败: {}", e.getMessage());
            }

            // 检查URL是否包含投递成功相关关键词
            boolean hasSuccessUrl = url.contains("success") ||
                    url.contains("delivery") ||
                    url.contains("apply") ||
                    url.contains("submit");

            // 检查页面标题是否包含投递成功相关关键词
            boolean hasSuccessTitle = title.contains("投递成功") ||
                    title.contains("申请成功") ||
                    title.contains("提交成功") ||
                    title.contains("success");

            // 检查页面内容是否包含投递成功相关文本
            boolean hasSuccessContent = false;
            try {
                String bodyText = popup.evaluate("document.body ? document.body.innerText : ''").toString();
                hasSuccessContent = bodyText.contains("投递成功") ||
                        bodyText.contains("申请已提交") ||
                        bodyText.contains("简历已投递") ||
                        bodyText.contains("您已成功投递");
            } catch (Exception e) {
                log.debug("获取页面内容失败: {}", e.getMessage());
            }

            boolean isSuccess = hasSuccessUrl || hasSuccessTitle || hasSuccessContent;
            log.debug("投递成功页校验: URL={}, title={}, hasSuccessUrl={}, hasSuccessTitle={}, hasSuccessContent={}, result={}",
                    url, title, hasSuccessUrl, hasSuccessTitle, hasSuccessContent, isSuccess);

            return isSuccess;
        } catch (Exception e) {
            log.warn("校验投递成功页异常: {}", e.getMessage());
            return false;
        }
    }
}
