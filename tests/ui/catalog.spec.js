const { test, expect } = require("@playwright/test");

const manifest = {
  version: 1,
  device: { hostname: "studio", dns_name: "studio.tail1234.ts.net" },
  artifacts: [
    {
      slug: "world-clock",
      title: "World Clock",
      description: "Timezones at a glance",
      path: "/artifacts/world-clock/",
    },
  ],
  generated_at: "2026-08-10T01:02:03Z",
};

const peers = {
  version: 2,
  peers: [
    {
      hostname: "workshop",
      dns_name: "workshop.tail1234.ts.net",
      url: "https://workshop.example.com",
      source: "discovered",
      state: "online",
      artifacts: [
        {
          slug: "telemetry",
          title: "Telemetry",
          description: "Live vehicle traces",
          path: "/artifacts/telemetry/",
        },
      ],
    },
  ],
  generated_at: "2026-08-10T01:03:00Z",
};

async function mockCatalog(page, manifestBody = manifest, peersBody = peers) {
  await page.route("**/manifest.json", (route) => route.fulfill({ json: manifestBody }));
  await page.route("**/peers.json", (route) => route.fulfill({ json: peersBody }));
}

test("renders operational summary and artifact mesh", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await mockCatalog(page);
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Artifact mesh" })).toBeVisible();
  await expect(page.getByTestId("status-summary")).toContainText("2 artifacts");
  await expect(page.getByTestId("local-grid")).toContainText("World Clock");
  await expect(page.getByTestId("peer-grid")).toContainText("Telemetry");
  await expect(page.getByText("workshop.tail1234.ts.net")).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("keeps launch links keyboard reachable", async ({ page }) => {
  await mockCatalog(page);
  await page.goto("/");
  const launch = page.getByRole("link", { name: /Open World Clock/ });

  await launch.focus();

  await expect(launch).toBeFocused();
  await expect(launch).toHaveCSS("outline-style", "solid");
});

test("reports degraded discovery without exposing raw errors", async ({ page }) => {
  await page.route("**/manifest.json", (route) => route.abort());
  await page.route("**/peers.json", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByTestId("degraded-state")).toBeVisible();
  await expect(page.getByText("Mesh data is temporarily unavailable.")).toBeVisible();
});

test("does not overflow a phone viewport", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-specific assertion");
  await mockCatalog(page);
  await page.goto("/");

  const sizes = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(sizes.scrollWidth).toBeLessThanOrEqual(sizes.clientWidth);
});
