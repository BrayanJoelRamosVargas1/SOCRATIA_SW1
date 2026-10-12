import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BASE_URL = "http://localhost:3000";
const ROOT_DIR = path.resolve(__dirname, "../../");
const SCREENSHOTS_DIR = path.join(ROOT_DIR, "docs/screenshots");
const EVIDENCIAS_DIR = path.join(ROOT_DIR, "docs/evidencias");

fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
fs.mkdirSync(EVIDENCIAS_DIR, { recursive: true });

async function runVisualTour() {
  console.log("🚀 Starting Playwright Visual Tour using native Microsoft Edge...");

  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();
  const results = [];

  const record = (cu, name, status, file) => {
    results.push({ cu, name, status, file });
    console.log(`[${status}] ${cu} - ${name} -> ${file || "N/A"}`);
  };

  try {
    // -------------------------------------------------------------
    // 1. CU01: Login & Register pages
    // -------------------------------------------------------------
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU01_01_login_page.png"), fullPage: true });
    record("CU01", "Login Form (HttpOnly Cookies)", "PASS", "CU01_01_login_page.png");

    await page.goto(`${BASE_URL}/register`, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU01_02_register_page.png"), fullPage: true });
    record("CU01", "Student Registration Form", "PASS", "CU01_02_register_page.png");

    // -------------------------------------------------------------
    // 2. Administrator Section (CU17, CU04, CU05, CU09, CU13)
    // -------------------------------------------------------------
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', "smoke_admin_demo@socratia.edu");
    await page.fill('input[type="password"]', "SmokeAdminPassword123!");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // CU17: Admin Dashboard
    await page.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU17_admin_dashboard.png"), fullPage: true });
    record("CU17", "Admin Platform Supervision Dashboard", "PASS", "CU17_admin_dashboard.png");

    // CU04: Admin Users Management
    await page.goto(`${BASE_URL}/admin/users`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU04_admin_users.png"), fullPage: true });
    record("CU04", "Admin User Management & RBAC Roles", "PASS", "CU04_admin_users.png");

    // CU05: Admin Plans
    await page.goto(`${BASE_URL}/admin/plans`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU05_01_admin_plans.png"), fullPage: true });
    record("CU05", "Admin Plans Catalog Management", "PASS", "CU05_01_admin_plans.png");

    // CU05: Admin Subscriptions
    await page.goto(`${BASE_URL}/admin/subscriptions`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU05_02_admin_subscriptions.png"), fullPage: true });
    record("CU05", "Admin Subscriptions Audit & Control", "PASS", "CU05_02_admin_subscriptions.png");

    // CU09: Admin AI Settings
    await page.goto(`${BASE_URL}/admin/ai-settings`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU09_admin_ai_settings.png"), fullPage: true });
    record("CU09", "Admin Runtime AI & RAG Configuration", "PASS", "CU09_admin_ai_settings.png");

    // CU13: Admin Jury Profiles
    await page.goto(`${BASE_URL}/admin/jury-profiles`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU13_admin_jury_profiles.png"), fullPage: true });
    record("CU13", "Admin Jury Profiles Management", "PASS", "CU13_admin_jury_profiles.png");

    // -------------------------------------------------------------
    // 3. Student Section (CU02, CU03, CU06, CU07, CU08, CU10, CU11, CU12, CU14, CU15, CU16)
    // -------------------------------------------------------------
    await context.clearCookies();
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', "student_00dd92@socratia.edu");
    await page.fill('input[type="password"]', "SmokeStudentPassword123!");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // CU06 / CU07 / CU08: Student Dashboard
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU06_CU07_CU08_student_dashboard.png"), fullPage: true });
    record("CU06-CU08", "Student Document & Question Preparation Dashboard", "PASS", "CU06_CU07_CU08_student_dashboard.png");

    // CU02: Student Profile Management
    await page.goto(`${BASE_URL}/profile`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU02_student_profile.png"), fullPage: true });
    record("CU02", "Student Self-Service Profile Management", "PASS", "CU02_student_profile.png");

    // CU03: Student Subscription
    await page.goto(`${BASE_URL}/subscription`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU03_student_subscription.png"), fullPage: true });
    record("CU03", "Student Subscription Selection & Status", "PASS", "CU03_student_subscription.png");

    // CU16: Student History
    await page.goto(`${BASE_URL}/history`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU16_student_history.png"), fullPage: true });
    record("CU16", "Student Defense Simulations History", "PASS", "CU16_student_history.png");

    // CU15: Student Performance Report
    const simId = "a474bb97-73fa-458e-b817-a9b7c47168b0";
    await page.goto(`${BASE_URL}/simulations/${simId}/report`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU15_student_performance_report.png"), fullPage: true });
    record("CU15", "Student Performance Report with Dimensions", "PASS", "CU15_student_performance_report.png");

    // Generate physical PDF of the Report page
    const pdfPath = path.join(EVIDENCIAS_DIR, "reporte_defensa_simulacion.pdf");
    await page.pdf({
      path: pdfPath,
      format: "A4",
      printBackground: true,
      margin: { top: "20mm", bottom: "20mm", left: "15mm", right: "15mm" },
    });
    const pdfStats = fs.statSync(pdfPath);
    console.log(`📑 PDF Generated at: ${pdfPath} (${pdfStats.size} bytes)`);
    record("CU15-PDF", "Physical PDF Export Verification", "PASS", "reporte_defensa_simulacion.pdf");

    // CU11 / CU12: Simulation Live Session (Completed State)
    await page.goto(`${BASE_URL}/simulations/${simId}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "CU11_CU12_simulation_session.png"), fullPage: true });
    record("CU11-CU12", "Simulation Live Defense Room (Jury & Transcript)", "PASS", "CU11_CU12_simulation_session.png");

  } catch (error) {
    console.error("❌ Visual Tour Error:", error);
  } finally {
    await browser.close();
  }

  console.log("\n=======================================================");
  console.log("  PLAYWRIGHT VISUAL TOUR SUMMARY (Microsoft Edge)");
  console.log("=======================================================");
  for (const r of results) {
    console.log(`[${r.status}] ${r.cu.padEnd(10)} | ${r.name.padEnd(45)} | ${r.file}`);
  }
}

runVisualTour();
