package getjobs.modules.integration.service.mediasaver;

import getjobs.modules.integration.dto.ApiResponse;
import getjobs.modules.integration.service.mediasaver.dto.MediaSaverResponse;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.List;

/**
 * 媒体保存服务控制器
 * 提供社交媒体内容下载的HTTP接口
 */
@Slf4j
@RestController
@RequestMapping("/api/media-saver")
@RequiredArgsConstructor
public class MediaSaverController {

    private final MediaSaverService mediaSaverService;

    /**
     * 智能下载 - 自动识别URL类型并下载
     * 
     * @param url 媒体URL（支持 TikTok、Instagram、Facebook、Twitter）
     * @return 下载结果
     */
    @PostMapping("/download")
    public Mono<ApiResponse<MediaSaverResponse>> smartDownload(@RequestParam String url) {
        return mediaSaverService.downloadByUrl(url);
    }

    /**
     * 下载 TikTok 视频
     * 
     * @param url TikTok视频URL
     * @return 视频信息
     */
    @PostMapping("/tiktok")
    public Mono<ApiResponse<MediaSaverResponse>> downloadTikTok(@RequestParam String url) {
        return mediaSaverService.downloadTikTok(url);
    }

    /**
     * 下载 Instagram 内容
     * 
     * @param url Instagram内容URL（照片或视频）
     * @return 内容信息
     */
    @PostMapping("/instagram")
    public Mono<ApiResponse<MediaSaverResponse>> downloadInstagram(@RequestParam String url) {
        return mediaSaverService.downloadInstagram(url);
    }

    /**
     * 下载 Facebook 视频
     * 
     * @param url Facebook视频URL
     * @return 视频信息
     */
    @PostMapping("/facebook")
    public Mono<ApiResponse<MediaSaverResponse>> downloadFacebook(@RequestParam String url) {
        return mediaSaverService.downloadFacebook(url);
    }

    /**
     * 下载 Twitter/X 视频
     * 
     * @param url Twitter视频URL
     * @return 视频信息
     */
    @PostMapping("/twitter")
    public Mono<ApiResponse<MediaSaverResponse>> downloadTwitter(@RequestParam String url) {
        return mediaSaverService.downloadTwitter(url);
    }

    /**
     * 批量下载
     * 
     * @param request 批量下载请求
     * @return 下载结果列表
     */
    @PostMapping("/batch")
    public Mono<ApiResponse<BatchDownloadResponse>> batchDownload(@RequestBody BatchDownloadRequest request) {
        if (request.getUrls() == null || request.getUrls().isEmpty()) {
            return Mono.just(ApiResponse.error("URL列表不能为空"));
        }

        log.info("开始批量下载，共{}个URL", request.getUrls().size());

        return reactor.core.publisher.Flux.fromIterable(request.getUrls())
                .parallel()
                .runOn(reactor.core.scheduler.Schedulers.boundedElastic())
                .flatMap(url -> {
                    DownloadResult result = new DownloadResult();
                    result.setUrl(url);

                    try {
                        // 调用单个下载服务
                        var response = mediaSaverService.downloadByUrl(url).block();
                        if (response != null && response.isSuccess()) {
                            result.setSuccess(true);
                            result.setData(response.getData());
                        } else {
                            result.setSuccess(false);
                            result.setError(response != null ? response.getMessage() : "下载失败");
                        }
                    } catch (Exception e) {
                        log.error("下载失败: {}", url, e);
                        result.setSuccess(false);
                        result.setError(e.getMessage());
                    }

                    return reactor.core.publisher.Mono.just(result);
                })
                .sequential()
                .collectList()
                .map(results -> {
                    BatchDownloadResponse response = new BatchDownloadResponse();
                    response.setResults(results);

                    long successCount = results.stream().filter(r -> Boolean.TRUE.equals(r.getSuccess())).count();
                    log.info("批量下载完成，成功: {}/{}", successCount, results.size());

                    return ApiResponse.success(response);
                })
                .onErrorResume(e -> {
                    log.error("批量下载异常", e);
                    return Mono.just(ApiResponse.error("批量下载失败: " + e.getMessage()));
                });
    }

    /**
     * 获取服务状态
     * 
     * @return 服务状态信息
     */
    @GetMapping("/status")
    public Mono<ApiResponse<ServiceStatus>> getStatus() {
        ServiceStatus status = new ServiceStatus();
        status.setAvailable(true);
        status.setSupportedPlatforms(new String[] { "TikTok", "Instagram", "Facebook", "Twitter/X" });
        status.setVersion("1.0.0");

        return Mono.just(ApiResponse.success(status));
    }

    /**
     * 批量下载请求
     */
    @Data
    public static class BatchDownloadRequest {
        private List<String> urls;
    }

    /**
     * 批量下载响应
     */
    @Data
    public static class BatchDownloadResponse {
        private List<DownloadResult> results;
    }

    /**
     * 单个下载结果
     */
    @Data
    public static class DownloadResult {
        private String url;
        private Boolean success;
        private MediaSaverResponse data;
        private String error;
    }

    /**
     * 服务状态
     */
    @Data
    public static class ServiceStatus {
        private Boolean available;
        private String[] supportedPlatforms;
        private String version;
    }
}
