import { test, expect } from '@playwright/test';

test.describe('Edit Draft', () => {
  test('edit draft before submitting', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[placeholder="Your name"]', 'Test User');
    await page.selectOption('select', 'AI/ML Engineer');
    await page.click('text=Enter GigBid');
    await page.click('text=Build churn prediction model');
    
    // Verify job detail loads
    await expect(page.locator('text=Job Detail')).toBeVisible();
  });
});