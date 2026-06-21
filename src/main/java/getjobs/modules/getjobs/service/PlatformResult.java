package getjobs.modules.getjobs.service;

import lombok.Data;

@Data
public class PlatformResult {
    private String platformName;
    private int attempted;
    private int delivered;
    private int skipped;
    private boolean needsUserAction;
}
