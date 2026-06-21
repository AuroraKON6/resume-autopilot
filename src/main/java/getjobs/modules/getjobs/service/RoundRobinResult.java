package getjobs.modules.getjobs.service;

import lombok.Data;
import java.util.*;

@Data
public class RoundRobinResult {
    private Date startTime;
    private Date endTime;
    private int totalDelivered;
    private int totalRounds;
    private String keyword;
    private List<PlatformResult> platformResults = new ArrayList<>();
}
