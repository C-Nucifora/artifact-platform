const { test, expect } = require("@playwright/test");

const configResponse = {
  config: {
    version: 1,
    excluded_peers: [],
    peers: {
      "studio.tail1234.ts.net": {
        public_url: "https://studio.example.com",
      },
    },
  },
  revision: "revision-one",
  discovered_peers: [
    { hostname: "studio", dns_name: "studio.tail1234.ts.net", online: true },
    { hostname: "workshop", dns_name: "workshop.tail1234.ts.net", online: true },
  ],
};

test("edits exclusions, endpoints, and manual peers", async ({ page }) => {
  let saved;
  let ifMatch;
  await page.route("**/api/admin/config", async (route) => {
    if (route.request().method() === "PUT") {
      saved = route.request().postDataJSON();
      ifMatch = route.request().headers()["if-match"];
      await route.fulfill({ json: { ...configResponse, config: saved, revision: "revision-two" } });
    } else {
      await route.fulfill({ json: configResponse });
    }
  });
  await page.goto("/admin.html");

  await expect(page.getByRole("heading", { name: "Mesh configuration" })).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  const workshop = page.getByTestId("peer-workshop-tail1234-ts-net");
  await workshop.getByLabel("Exclude peer").check();
  await workshop.getByLabel("Public HTTPS endpoint").fill("https://workshop.example.com");
  await page.getByLabel("Manual peer identifier").fill("trackside");
  await page.getByRole("button", { name: "Add manual peer" }).click();
  const trackside = page.getByTestId("peer-trackside");
  await trackside.getByLabel("SSH target").fill("trackside.tail1234.ts.net");
  await trackside.getByLabel("Public HTTPS endpoint").fill("https://trackside.example.com");
  await trackside.getByLabel("Excluded artifact slugs").fill("private-demo, internal");
  await page.getByRole("button", { name: "Save configuration" }).click();

  await expect(page.getByText("Configuration saved")).toBeVisible();
  expect(ifMatch).toBe('"revision-one"');
  expect(saved.excluded_peers).toEqual(["workshop.tail1234.ts.net"]);
  expect(saved.peers.trackside).toEqual({
    manual: true,
    ssh_target: "trackside.tail1234.ts.net",
    public_url: "https://trackside.example.com",
    excluded_artifacts: ["private-demo", "internal"],
  });
});

test("validates endpoints and slugs before sending configuration", async ({ page }) => {
  let putCount = 0;
  await page.route("**/api/admin/config", async (route) => {
    if (route.request().method() === "PUT") putCount += 1;
    await route.fulfill({ json: configResponse });
  });
  await page.goto("/admin.html");
  const studio = page.getByTestId("peer-studio-tail1234-ts-net");
  await studio.getByLabel("Public HTTPS endpoint").fill("http://insecure.example.com");
  await studio.getByLabel("Excluded artifact slugs").fill("../private");

  await page.getByRole("button", { name: "Save configuration" }).click();

  await expect(page.getByText("Fix the highlighted fields before saving.")).toBeVisible();
  await expect(studio.getByLabel("Public HTTPS endpoint")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(putCount).toBe(0);
});

test("canceling peer exclusion leaves the peer included", async ({ page }) => {
  await page.route("**/api/admin/config", (route) => route.fulfill({ json: configResponse }));
  await page.goto("/admin.html");
  page.once("dialog", (dialog) => dialog.dismiss());
  const exclusion = page
    .getByTestId("peer-workshop-tail1234-ts-net")
    .getByLabel("Exclude peer");

  await exclusion.click();

  await expect(exclusion).not.toBeChecked();
});

test("keeps an unsaved state and explains revision conflicts", async ({ page }) => {
  await page.route("**/api/admin/config", async (route) => {
    if (route.request().method() === "PUT") {
      await route.fulfill({ status: 409, json: { error: "mesh configuration changed" } });
    } else {
      await route.fulfill({ json: configResponse });
    }
  });
  await page.goto("/admin.html");
  await page
    .getByTestId("peer-studio-tail1234-ts-net")
    .getByLabel("Public HTTPS endpoint")
    .fill("https://new.example.com");

  await expect(page.getByText("Unsaved changes")).toBeVisible();
  await page.getByRole("button", { name: "Save configuration" }).click();
  await expect(page.getByText("Configuration changed elsewhere. Reload before saving.")).toBeVisible();
});
