const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests/ui",
  fullyParallel: true,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"] } },
  ],
  webServer: {
    command: "python3 -m http.server 4173 --directory platform/site",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: true,
  },
});
