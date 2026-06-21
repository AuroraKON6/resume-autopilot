# 轮询投递策略设计

## 核心思路

给定目标岗位后，按平台轮询投递，每个平台投递5个岗位后切换到下一个平台：

```
Boss直聘(5个) → 51job(5个) → 智联招聘(5个) → 猎聘(5个) → Boss直聘(5个) → ...
```

## 为什么这样做

1. **反爬机制**：每个网站都有反爬机制，单平台频繁投递容易被检测
2. **降低风险**：轮询投递可以分散请求，降低被封号风险
3. **提高效率**：多平台并行投递，提高求职覆盖率

## 实现要点

### 1. 平台优先级
- Boss直聘（最主流）
- 51job（传统招聘）
- 智联招聘（传统招聘）
- 猎聘（中高端）

### 2. 投递数量
- 每个平台每次投递 **5个** 岗位
- 可根据实际情况调整数量

### 3. 循环逻辑
```java
// 伪代码
while (还有待投递岗位) {
    for (platform : platforms) {
        List<JobDTO> jobs = platform.getNextJobs(5);
        for (JobDTO job : jobs) {
            platform.deliverJob(job);
        }
    }
}
```

### 4. 状态管理
- 记录每个平台已投递数量
- 记录每个平台待投递队列
- 支持中断和恢复

## 已实现的代码

### 1. RoundRobinDeliveryService
- 位置：`src/main/java/getjobs/modules/getjobs/service/RoundRobinDeliveryService.java`
- 功能：轮询投递核心逻辑
- 方法：`executeRoundRobinDelivery()`

### 2. RoundRobinDeliveryController
- 位置：`src/main/java/getjobs/controller/RoundRobinDeliveryController.java`
- 功能：轮询投递API接口
- 接口：`POST /api/delivery/round-robin`

### 3. JobService
- 位置：`src/main/java/getjobs/modules/getjobs/service/JobService.java`
- 方法：`findPendingDelivery(platform)` - 获取待投递岗位

## 待解决问题

### 51job
- WAF拦截API请求，返回HTML响应
- 需要更长的等待时间或更好的绕过策略
- DOM选择器可能需要更新

### 智联招聘
- 待测试

### 猎聘
- 待测试

### Boss直聘
- 已基本可用

## 下一步

1. 修复51job的WAF拦截问题
2. 测试各平台投递功能
3. 添加投递状态持久化
4. 实现投递限制检查

## 测试结果

### 2026-06-20
- ✅ 轮询投递API接口已实现
- ✅ `POST /api/delivery/round-robin` 接口正常工作
- ✅ 返回投递结果（总投递数、轮数、各平台结果）
- ⚠️ 当前投递数量为0（没有待投递岗位）
- ⚠️ 各平台实际投递逻辑待实现
