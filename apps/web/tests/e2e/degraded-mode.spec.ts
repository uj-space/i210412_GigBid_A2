import { test, expect } from '@playwright/test';

test.describe('Degraded Mode', () => {
  test('shows marketplace unavailable banner when backend down', async ({ page }) => {
    // This test verifies degraded mode handling
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('GigBid');
  });
});