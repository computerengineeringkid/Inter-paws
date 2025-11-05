import { expect, test } from "@playwright/test";

const adminEmail = `admin-${Date.now()}@example.com`;
const adminPassword = "Password!123";
const clientEmail = `client-${Date.now()}@example.com`;
const clientPassword = "Password!123";
const clientName = "Taylor Petlover";
const petName = "Luna";
let clinicId: number;

function isoLocal(date: Date) {
  return date.toISOString().slice(0, 16);
}

test.beforeAll(async ({ request }) => {
  const registerAdmin = await request.post("/api/auth/register", {
    data: {
      email: adminEmail,
      password: adminPassword,
      name: "Clinic Admin",
      role: "admin",
    },
  });
  expect(registerAdmin.ok()).toBeTruthy();

  const loginAdmin = await request.post("/api/auth/login", {
    data: { email: adminEmail, password: adminPassword },
  });
  expect(loginAdmin.ok()).toBeTruthy();
  const { access_token: adminToken } = await loginAdmin.json();

  const onboardingResponse = await request.post("/api/clinic/onboarding", {
    data: {
      clinic: {
        name: "Playwright Animal Hospital",
        email: "clinic@example.com",
        phone_number: "123-456-7890",
        address: "123 Main St",
      },
      doctors: [
        {
          display_name: "Dr. Whiskers",
          specialty: "Feline care",
          license_number: `LIC-${Date.now()}`,
        },
      ],
      rooms: [
        {
          name: "Exam Room 1",
          room_type: "exam",
          capacity: 1,
          notes: "Standard feline exam room",
        },
      ],
      schedule_rules: {
        operating_hours: [
          { day: "Monday", start: "08:00", end: "18:00" },
          { day: "Tuesday", start: "08:00", end: "18:00" },
          { day: "Wednesday", start: "08:00", end: "18:00" },
          { day: "Thursday", start: "08:00", end: "18:00" },
          { day: "Friday", start: "08:00", end: "18:00" },
        ],
      },
    },
    headers: {
      Authorization: `Bearer ${adminToken}`,
    },
  });
  expect(onboardingResponse.ok()).toBeTruthy();
  const onboardingPayload = await onboardingResponse.json();
  clinicId = onboardingPayload.clinic_id;
  expect(clinicId).toBeTruthy();
});

test("client can register, discover slots, book, and review history", async ({ page }) => {
  await page.goto("/client/register");

  await page.getByLabel(/Full name/i).fill(clientName);
  await page.getByLabel(/Email/i).fill(clientEmail);
  await page.getByLabel(/Password/i).fill(clientPassword);
  await page.getByLabel(/Clinic ID/i).fill(String(clinicId));
  await page.getByRole("button", { name: /Create account/i }).click();

  await page.waitForURL("**/client/booking");
  await expect(page.getByRole("heading", { name: /Find the perfect time/i })).toBeVisible();

  const start = new Date();
  start.setDate(start.getDate() + 2);
  start.setHours(9, 0, 0, 0);
  const end = new Date(start.getTime());
  end.setDate(end.getDate() + 2);
  end.setHours(17, 0, 0, 0);

  await page.getByLabel(/Pet name/i).fill(petName);
  await page.getByLabel(/Reason for visit/i).fill("Annual wellness exam");
  await page.getByLabel(/Search start/i).fill(isoLocal(start));
  await page.getByLabel(/Search end/i).fill(isoLocal(end));
  await page.getByLabel(/Duration/i).fill("30");
  await page.getByRole("button", { name: /Search suggestions/i }).click();

  await expect(page.getByRole("heading", { name: /Recommended slots/i })).toBeVisible();
  const slotButton = page.locator(".schedule-card").first();
  await expect(slotButton).toBeVisible();
  await slotButton.click();

  await page.getByRole("button", { name: /Book selected slot/i }).click();
  await expect(page.getByRole("status").first()).toContainText(/Appointment booked successfully/i);

  await page.getByRole("link", { name: /Visit history/i }).click();
  await page.waitForURL("**/client/history");
  await expect(page.getByRole("heading", { name: /Visit history/i })).toBeVisible();
  await expect(page.getByRole("cell", { name: petName })).toBeVisible();
  await expect(page.getByText(/scheduled/i)).toBeVisible();
});

test("clinic team can manage resources and monitor the live schedule", async ({ page }) => {
  await page.goto("/clinic/login");
  await page.getByLabel(/Email/i).fill(adminEmail);
  await page.getByLabel(/Password/i).fill(adminPassword);
  await page.getByRole("button", { name: /Sign in/i }).click();

  await page.waitForURL("**/clinic/dashboard");
  await expect(page.getByRole("heading", { name: /Operational overview/i })).toBeVisible();

  const doctorName = `Dr. Flux ${Date.now()}`;
  await page.getByRole("form", { name: /Add doctor/i }).getByLabel(/Display name/i).fill(doctorName);
  await page.getByRole("form", { name: /Add doctor/i }).getByLabel(/Specialty/i).fill("Surgery");
  await page.getByRole("form", { name: /Add doctor/i }).getByRole("button", { name: /Add doctor/i }).click();
  await expect(page.getByRole("cell", { name: doctorName })).toBeVisible();

  await page.getByRole("cell", { name: doctorName }).locator("xpath=..//button[contains(., 'Remove')]").click();
  await expect(page.getByRole("cell", { name: doctorName })).toHaveCount(0);

  const equipmentName = `Pulse Oximeter ${Date.now()}`;
  await page.getByRole("form", { name: /Add equipment/i }).getByLabel(/Room/i).selectOption({ label: "Exam Room 1" });
  await page.getByRole("form", { name: /Add equipment/i }).getByLabel(/Equipment name/i).fill(equipmentName);
  await page.getByRole("form", { name: /Add equipment/i }).getByRole("button", { name: /Add equipment/i }).click();
  await expect(page.getByText(equipmentName)).toBeVisible();
  await page
    .getByText(equipmentName)
    .locator("xpath=../button[contains(., 'Remove')]")
    .click();
  await expect(page.getByText(equipmentName)).toHaveCount(0);

  await page.getByRole("link", { name: /Schedule/i }).click();
  await page.waitForURL("**/clinic/schedule");
  await expect(page.getByRole("heading", { name: /Live schedule board/i })).toBeVisible();
  await expect(page.getByText(petName)).toBeVisible();
  await expect(page.getByText(clientName)).toBeVisible();
});
